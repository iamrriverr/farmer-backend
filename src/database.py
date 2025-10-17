# src/database.py
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import SimpleConnectionPool
from typing import List, Dict, Optional, Any
import json
from pathlib import Path
from contextlib import contextmanager

from .config import Config


class PostgreSQLManager:
    """PostgreSQL 資料庫管理器"""
    
    def __init__(self):
        self.pool = None
        self.init_pool()
    
    def init_pool(self):
        """初始化連線池"""
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=Config.PG_HOST,
                port=Config.PG_PORT,
                database=Config.PG_DATABASE,
                user=Config.PG_USER,
                password=Config.PG_PASSWORD
            )
            print("✅ PostgreSQL 連線池已建立")
        except Exception as e:
            print(f"❌ PostgreSQL 連線失敗: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """取得資料庫連線的上下文管理器"""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)
    
    def init_database(self):
        """初始化資料庫結構"""
        sql_file = Path(__file__).parent / "schema.sql"
        
        if sql_file.exists():
            print(f"📄 執行 SQL 檔案: {sql_file}")
            with open(sql_file, "r", encoding="utf-8") as f:
                create_sql = f.read()
        else:
            print("⚠️  未找到 schema.sql，使用預設 SQL")
            create_sql = self._get_default_schema()
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(create_sql)
                    conn.commit()
            print("✅ 資料庫結構初始化完成")
        except Exception as e:
            print(f"❌ 資料庫初始化失敗: {e}")
            raise
    
    def _get_default_schema(self) -> str:
        """取得預設資料庫結構"""
        return """
        -- 啟用擴展
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        
        -- 更新時間觸發器函數
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        -- 用戶表
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'user', 'guest')),
            is_active BOOLEAN DEFAULT TRUE,
            last_login_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        
        -- 對話表
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(200),
            model_config JSONB DEFAULT '{"model": "gemini-pro", "temperature": 0.7}'::jsonb,
            is_pinned BOOLEAN DEFAULT FALSE,
            is_archived BOOLEAN DEFAULT FALSE,
            message_count INTEGER DEFAULT 0,
            last_message_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id, updated_at DESC);
        
        DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
        CREATE TRIGGER update_conversations_updated_at
            BEFORE UPDATE ON conversations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        
        -- 聊天記錄表
        CREATE TABLE IF NOT EXISTS chat_history (
            id BIGSERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            message JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_chat_history_message_gin ON chat_history USING GIN (message);
        
        -- 自動更新對話統計
        CREATE OR REPLACE FUNCTION update_conversation_stats()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE conversations 
            SET message_count = message_count + 1,
                last_message_at = NEW.created_at,
                updated_at = NOW()
            WHERE id::text = NEW.session_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        DROP TRIGGER IF EXISTS update_conversation_stats_trigger ON chat_history;
        CREATE TRIGGER update_conversation_stats_trigger
            AFTER INSERT ON chat_history
            FOR EACH ROW
            EXECUTE FUNCTION update_conversation_stats();
        
        -- 文件管理表（新版本）
        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            file_path TEXT NOT NULL,
            file_size BIGINT NOT NULL,
            file_type VARCHAR(50),
            content_hash VARCHAR(64),
            chunk_count INTEGER DEFAULT 0,
            embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
            error_message TEXT,
            metadata JSONB DEFAULT '{}'::jsonb,
            processed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status, created_at);
        CREATE INDEX IF NOT EXISTS idx_documents_metadata_gin ON documents USING GIN (metadata);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash) WHERE content_hash IS NOT NULL;
        
        -- 為 RAG 過濾建立專用索引
        CREATE INDEX IF NOT EXISTS idx_documents_dept ON documents((metadata->>'department'));
        CREATE INDEX IF NOT EXISTS idx_documents_job_type ON documents((metadata->>'job_type'));
        CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(((metadata->>'year')::int));
        CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents((metadata->>'document_type'));
        
        DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
        CREATE TRIGGER update_documents_updated_at
            BEFORE UPDATE ON documents
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        
        -- 用戶偏好設定表
        CREATE TABLE IF NOT EXISTS user_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            preference_key VARCHAR(100) NOT NULL,
            preference_value TEXT NOT NULL,
            value_type VARCHAR(20) DEFAULT 'string' CHECK (value_type IN ('string', 'integer', 'boolean', 'json')),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, preference_key)
        );
        
        CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
        
        -- 標籤表
        CREATE TABLE IF NOT EXISTS tags (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(50) NOT NULL,
            color VARCHAR(7) DEFAULT '#3B82F6',
            icon VARCHAR(50),
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, name)
        );
        
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_system_name ON tags(name) WHERE user_id IS NULL;
        
        -- 對話標籤關聯表
        CREATE TABLE IF NOT EXISTS conversation_tags (
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (conversation_id, tag_id)
        );
        
        -- 通知表
        CREATE TABLE IF NOT EXISTS notifications (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            notification_type VARCHAR(50) NOT NULL,
            title VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            related_entity_type VARCHAR(50),
            related_entity_id VARCHAR(100),
            action_url VARCHAR(500),
            priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
            is_read BOOLEAN DEFAULT FALSE,
            read_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);
        
        -- 插入預設系統標籤
        INSERT INTO tags (user_id, name, color, icon) VALUES
        (NULL, '水稻', '#10B981', 'plant'),
        (NULL, '病蟲害', '#EF4444', 'bug'),
        (NULL, '補助申請', '#F59E0B', 'money'),
        (NULL, '技術諮詢', '#3B82F6', 'question')
        ON CONFLICT DO NOTHING;
        """
    
    # ========================================
    # 文件管理方法（使用新的 documents 表）
    # ========================================
    
    def insert_document_metadata(self, user_id: int, filename: str, file_path: str, 
                                 file_size: int, file_type: str, content_hash: str = None,
                                 **metadata) -> str:
        """
        插入文件 metadata（新版本）
        
        Args:
            user_id: 用戶 ID
            filename: 文件名稱
            file_path: 文件路徑
            file_size: 文件大小（bytes）
            file_type: 文件類型
            content_hash: 文件 hash（用於去重）
            **metadata: 額外的 metadata（department, job_type, year, document_type 等）
        
        Returns:
            document_id (UUID string)
        """
        sql = """
        INSERT INTO documents (user_id, filename, file_path, file_size, file_type, 
                              content_hash, metadata, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING id
        """
        try:
            metadata_json = Json(metadata) if metadata else Json({})
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (user_id, filename, file_path, file_size, 
                                     file_type, content_hash, metadata_json))
                    doc_id = cur.fetchone()[0]
                    conn.commit()
            print(f"✅ 文件 metadata 已插入: {doc_id}")
            return str(doc_id)
        except Exception as e:
            print(f"❌ 插入文件 metadata 失敗: {e}")
            raise
    
    def filter_documents(self, filters: Dict, user_id: int = None) -> List[Dict]:
        """
        過濾文件（使用 JSONB metadata）
        
        Args:
            filters: 過濾條件字典
                - department: 部門
                - job_type: 業務類別
                - year: 年份
                - document_type: 文件類型
                - status: 狀態
            user_id: 用戶 ID（可選，不提供則查詢所有）
        
        Returns:
            符合條件的文件列表
        """
        base_sql = "SELECT * FROM documents WHERE 1=1"
        params = []
        
        # 用戶過濾
        if user_id:
            base_sql += " AND user_id = %s"
            params.append(user_id)
        
        # 狀態過濾（預設只查詢已完成的）
        if 'status' in filters and filters['status']:
            base_sql += " AND status = %s"
            params.append(filters['status'])
        else:
            base_sql += " AND status = 'completed'"
        
        # metadata 過濾
        if 'department' in filters and filters['department']:
            base_sql += " AND metadata->>'department' = %s"
            params.append(filters['department'])
        
        if 'job_type' in filters and filters['job_type']:
            base_sql += " AND metadata->>'job_type' = %s"
            params.append(filters['job_type'])
        
        if 'year' in filters and filters['year']:
            base_sql += " AND (metadata->>'year')::int = %s"
            params.append(filters['year'])
        
        if 'min_year' in filters and filters['min_year']:
            base_sql += " AND (metadata->>'year')::int >= %s"
            params.append(filters['min_year'])
        
        if 'document_type' in filters and filters['document_type']:
            base_sql += " AND metadata->>'document_type' = %s"
            params.append(filters['document_type'])
        
        base_sql += " ORDER BY created_at DESC"
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(base_sql, params)
                    results = cur.fetchall()
            
            # 轉換為相容格式（添加 document_id 和 source_url 欄位）
            documents = []
            for row in results:
                doc = dict(row)
                doc['document_id'] = str(doc['id'])  # 相容舊欄位名稱
                doc['source_url'] = doc['file_path']  # 相容舊欄位名稱
                
                # 將 metadata 中的欄位提升到頂層
                if doc.get('metadata'):
                    meta = doc['metadata']
                    doc['department'] = meta.get('department', '')
                    doc['job_type'] = meta.get('job_type')
                    doc['year'] = meta.get('year')
                    doc['document_type'] = meta.get('document_type', 'general')
                
                documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"❌ 查詢失敗: {e}")
            return []
    
    def get_user_documents(self, user_id: int, status: str = None) -> List[Dict]:
        """取得用戶的文件列表"""
        sql = "SELECT * FROM documents WHERE user_id = %s"
        params = [user_id]
        
        if status:
            sql += " AND status = %s"
            params.append(status)
        
        sql += " ORDER BY created_at DESC"
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, params)
                    results = cur.fetchall()
            
            # 轉換格式（同 filter_documents）
            documents = []
            for row in results:
                doc = dict(row)
                doc['document_id'] = str(doc['id'])
                doc['source_url'] = doc['file_path']
                
                if doc.get('metadata'):
                    meta = doc['metadata']
                    doc['department'] = meta.get('department', '')
                    doc['job_type'] = meta.get('job_type')
                    doc['year'] = meta.get('year')
                    doc['document_type'] = meta.get('document_type', 'general')
                
                documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"❌ 查詢文件失敗: {e}")
            return []
    
    def update_document_status(self, doc_id: str, status: str, error_message: str = None):
        """更新文件處理狀態"""
        sql = """
        UPDATE documents 
        SET status = %s, error_message = %s, 
            processed_at = CASE WHEN %s = 'completed' THEN NOW() ELSE processed_at END,
            updated_at = NOW()
        WHERE id = %s
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (status, error_message, status, doc_id))
                    conn.commit()
        except Exception as e:
            print(f"❌ 更新文件狀態失敗: {e}")
            raise
    
    # ========================================
    # 用戶管理方法
    # ========================================
    
    def create_user(self, username: str, email: str, hashed_password: str, role: str = "user") -> Dict:
        """建立新用戶"""
        sql = """
        INSERT INTO users (username, email, hashed_password, role, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING id, username, email, role, created_at
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (username, email, hashed_password, role))
                    result = cur.fetchone()
                    conn.commit()
            return dict(result)
        except Exception as e:
            print(f"❌ 建立用戶失敗: {e}")
            raise
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """根據 email 取得用戶"""
        sql = "SELECT * FROM users WHERE email = %s"
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (email,))
                    result = cur.fetchone()
            return dict(result) if result else None
        except Exception as e:
            print(f"❌ 查詢用戶失敗: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """根據 ID 取得用戶"""
        sql = "SELECT id, username, email, role, is_active, created_at FROM users WHERE id = %s"
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (user_id,))
                    result = cur.fetchone()
            return dict(result) if result else None
        except Exception as e:
            print(f"❌ 查詢用戶失敗: {e}")
            return None
    
    def update_last_login(self, user_id: int):
        """更新用戶最後登入時間"""
        sql = "UPDATE users SET last_login_at = NOW() WHERE id = %s"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (user_id,))
                    conn.commit()
        except Exception as e:
            print(f"❌ 更新登入時間失敗: {e}")
    
    # ========================================
    # 對話管理方法
    # ========================================
    
    def create_conversation(self, user_id: int, title: str = None) -> Dict:
        """建立新對話"""
        sql = """
        INSERT INTO conversations (user_id, title, created_at, updated_at)
        VALUES (%s, %s, NOW(), NOW())
        RETURNING id, user_id, title, created_at
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (user_id, title))
                    result = cur.fetchone()
                    conn.commit()
            return dict(result)
        except Exception as e:
            print(f"❌ 建立對話失敗: {e}")
            raise
    
    def get_user_conversations(self, user_id: int, include_archived: bool = False) -> List[Dict]:
        """取得用戶的所有對話"""
        sql = """
        SELECT id, title, message_count, is_pinned, is_archived, 
               last_message_at, created_at, updated_at
        FROM conversations
        WHERE user_id = %s
        """
        if not include_archived:
            sql += " AND is_archived = FALSE"
        sql += " ORDER BY is_pinned DESC, updated_at DESC"
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (user_id,))
                    results = cur.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            print(f"❌ 查詢對話失敗: {e}")
            return []
    
    def get_conversation_by_id(self, conversation_id: str, user_id: int = None) -> Optional[Dict]:
        """取得特定對話"""
        sql = "SELECT * FROM conversations WHERE id = %s"
        params = [conversation_id]
        
        if user_id:
            sql += " AND user_id = %s"
            params.append(user_id)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, params)
                    result = cur.fetchone()
            return dict(result) if result else None
        except Exception as e:
            print(f"❌ 查詢對話失敗: {e}")
            return None
    
    def update_conversation(self, conversation_id: str, **kwargs):
        """更新對話資訊"""
        allowed_fields = ['title', 'is_pinned', 'is_archived', 'model_config']
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            return
        
        set_clause = ", ".join([f"{k} = %s" for k in update_fields.keys()])
        sql = f"UPDATE conversations SET {set_clause}, updated_at = NOW() WHERE id = %s"
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, list(update_fields.values()) + [conversation_id])
                    conn.commit()
        except Exception as e:
            print(f"❌ 更新對話失敗: {e}")
            raise
    
    def delete_conversation(self, conversation_id: str):
        """刪除對話"""
        sql = "DELETE FROM conversations WHERE id = %s"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (conversation_id,))
                    conn.commit()
        except Exception as e:
            print(f"❌ 刪除對話失敗: {e}")
            raise
    
    # ========================================
    # 通知方法
    # ========================================
    
    def create_notification(self, user_id: int, notification_type: str, 
                          title: str, message: str, **kwargs) -> int:
        """建立通知"""
        sql = """
        INSERT INTO notifications (user_id, notification_type, title, message,
                                  related_entity_type, related_entity_id, 
                                  action_url, priority, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING id
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        user_id, notification_type, title, message,
                        kwargs.get('related_entity_type'),
                        kwargs.get('related_entity_id'),
                        kwargs.get('action_url'),
                        kwargs.get('priority', 'normal')
                    ))
                    notif_id = cur.fetchone()[0]
                    conn.commit()
            return notif_id
        except Exception as e:
            print(f"❌ 建立通知失敗: {e}")
            raise
    
    def close(self):
        """關閉連線池"""
        if self.pool:
            self.pool.closeall()
            print("✅ PostgreSQL 連線池已關閉")
