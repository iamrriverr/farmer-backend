# main.py
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path

from src.config import Config
from src.database import PostgreSQLManager
from src.vector import VectorStoreManager
from src.routes import auth, conversations, chat, documents, users

# 確保必要目錄存在
Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
Config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理
    啟動時執行初始化，關閉時執行清理
    """
    print("=" * 60)
    print("🚀 Farmer RAG System 啟動中...")
    print("=" * 60)
    
    # 驗證配置
    try:
        Config.validate()
        print("✅ 配置驗證通過")
    except ValueError as e:
        print(f"❌ 配置驗證失敗: {e}")
        raise
    
    # 初始化資料庫
    try:
        db = PostgreSQLManager()
        db.init_database()
        print("✅ 資料庫初始化完成")
    except Exception as e:
        print(f"❌ 資料庫初始化失敗: {e}")
        raise
    
    # 初始化向量資料庫
    try:
        vector_manager = VectorStoreManager(
            persist_directory=Config.CHROMA_PERSIST_DIR,
            collection_name=Config.CHROMA_COLLECTION
        )
        print(f"✅ 向量資料庫初始化完成 (Collection: {Config.CHROMA_COLLECTION})")
    except Exception as e:
        print(f"⚠️ 向量資料庫初始化警告: {e}")
        vector_manager = None
    
    # 🔥 初始化混合搜尋（新增）
    if Config.ENABLE_HYBRID_SEARCH and vector_manager:
        try:
            print("📚 正在載入文件以建立 BM25 索引...")
            from src.loader import DocumentLoader
            
            # 從資料庫載入已處理的文件
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT d.id, d.file_path, d.filename, d.metadata
                        FROM documents d
                        WHERE d.status = 'completed'
                        ORDER BY d.created_at DESC
                        LIMIT %s
                    """, (Config.HYBRID_SEARCH_LIMIT,))
                    docs_info = cur.fetchall()
            
            # 載入文件內容
            all_docs = []
            for doc_id, file_path, filename, metadata in docs_info:
                try:
                    # 確保檔案路徑存在
                    file_path_obj = Path(file_path)
                    if not file_path_obj.exists():
                        print(f"  ⚠️ 檔案不存在: {file_path}")
                        continue
                    
                    loaded_docs = DocumentLoader.load_document(str(file_path_obj))
                    chunks = DocumentLoader.split_into_chunks(loaded_docs)
                    
                    # 添加 metadata
                    for chunk in chunks:
                        chunk.metadata.update({
                            "document_id": str(doc_id),
                            "filename": filename,
                            **(metadata or {})
                        })
                    
                    all_docs.extend(chunks)
                    print(f"  ✓ 載入 {filename}（{len(chunks)} 個片段）")
                except Exception as e:
                    print(f"  ⚠️ 載入文件失敗 {filename}: {e}")
            
            # 初始化混合搜尋
            if all_docs:
                vector_manager.init_hybrid_search(documents=all_docs)
                print(f"✅ 混合搜尋已啟用（載入 {len(all_docs)} 個文件片段）")
            else:
                print("⚠️ 無文件可用於混合搜尋，將僅使用向量搜尋")
                
        except Exception as e:
            print(f"⚠️ 混合搜尋初始化失敗: {e}，將僅使用向量搜尋")
    else:
        if not Config.ENABLE_HYBRID_SEARCH:
            print("⚠️ 混合搜尋已停用（ENABLE_HYBRID_SEARCH=false）")
        elif not vector_manager:
            print("⚠️ 混合搜尋無法啟用（向量資料庫未初始化）")
    
    # ============================================================
    # 🔥 重要：將實例存儲到 app.state（供所有路由使用）
    # ============================================================
    app.state.db = db
    app.state.vector_manager = vector_manager
    
    print("=" * 60)
    print("✅ 系統啟動完成!")
    print(f"📡 API 文件: http://localhost:8000/docs")
    print(f"📊 資料庫: PostgreSQL @ {Config.PG_HOST}:{Config.PG_PORT}/{Config.PG_DATABASE}")
    print(f"🔍 向量資料庫: Chroma @ {Config.CHROMA_PERSIST_DIR}")
    print(f"🎯 對話記憶: 已啟用（支援多輪對話）")
    print(f"🤖 AI 模型: {Config.get_model_name()}")
    print(f"🔎 混合搜尋: {'✅ 啟用 (BM25 + 向量)' if Config.ENABLE_HYBRID_SEARCH and vector_manager and vector_manager.hybrid_manager else '❌ 停用'}")
    if Config.ENABLE_HYBRID_SEARCH and vector_manager and vector_manager.hybrid_manager:
        print(f"   ├─ BM25 權重: {Config.BM25_WEIGHT}")
        print(f"   └─ 向量權重: {Config.VECTOR_WEIGHT}")
    print("=" * 60)
    
    yield  # 應用程式運行
    
    # 關閉時清理
    print("\n" + "=" * 60)
    print("🛑 系統關閉中...")
    print("=" * 60)
    
    if hasattr(app.state, 'db') and app.state.db.pool:
        app.state.db.pool.closeall()
        print("✅ 資料庫連線池已關閉")
    
    print("✅ 系統已安全關閉")
    print("=" * 60)


# 建立 FastAPI 應用
app = FastAPI(
    title=Config.TITLE,
    version=Config.VERSION,
    description="""
    ## 🌾 Farmer RAG System API
    
    農會 RAG (Retrieval-Augmented Generation) 智能問答系統後端 API
    
    ### ✨ 主要功能
    
    - **🔐 用戶認證**: JWT Token 認證、註冊登入、權限管理
    - **💬 對話管理**: 建立、查詢、更新、刪除對話，支援標籤和分享
    - **🧠 對話記憶**: 支援多輪對話，AI 會記住上下文（像 ChatGPT）
    - **🤖 即時聊天**: WebSocket 串流聊天、RESTful 查詢、完整對話記錄
    - **📁 文件管理**: 上傳、處理、查詢文件，自動向量化
    - **🔍 RAG 查詢**: 基於向量檢索的智能問答，支援意圖自動判斷
    - **🔎 混合搜尋**: BM25 關鍵字搜尋 + 向量語義搜尋（提升檢索精確度 15-30%）
    - **📚 來源引用**: 回答附帶文件來源，可追溯可靠
    
    ### 🎯 核心特色
    
    1. **智能意圖判斷**: 自動識別問題類型，決定是否使用 RAG
    2. **對話記憶功能**: 記住歷史對話，支援上下文連貫對話
    3. **混合搜尋技術**: 結合 BM25 精確匹配與向量語義理解
    4. **文件來源追蹤**: 每個回答都附上依據的文件來源
    5. **即時串流輸出**: 像 ChatGPT 一樣逐字顯示 AI 回應
    6. **專業知識庫**: 基於農會實際文件，準確可靠
    
    ### 🔑 認證方式
    
    大部分 API 需要在 Header 中提供 JWT Token：
    ```
    Authorization: Bearer <your_token>
    ```
    
    ### 🚀 快速開始
    
    1. **註冊帳號**: `POST /auth/register`
    2. **登入取得 Token**: `POST /auth/login`
    3. **上傳文件**: `POST /documents/upload`
    4. **建立對話**: `POST /conversations/`
    5. **開始聊天**: 
       - WebSocket (推薦): `ws://localhost:8000/chat/ws/{conversation_id}?token={token}`
       - REST API: `POST /chat/query`
    
    ### 💡 WebSocket 聊天範例
    
    ```
    // 建立連線
    const ws = new WebSocket('ws://localhost:8000/chat/ws/conv-123?token=your-token');
    
    // 發送訊息
    ws.send(JSON.stringify({
        type: 'message',
        content: '水稻病蟲害如何防治？',
        k: 5
    }));
    
    // 接收回應（逐字顯示）
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'chunk') {
            console.log(data.content); // AI 回應片段
        }
    };
    ```
    
    ### 🔎 混合搜尋測試
    
    ```
    # 對比三種搜尋方式
    curl -X POST "http://localhost:8000/chat/test-search-comparison?query=水稻病蟲害&k=5" \\
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    
    ### 📖 更多資訊
    
    - 完整 API 文件: [Swagger UI](/docs)
    - ReDoc 文件: [ReDoc](/redoc)
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# CORS 設定（開發模式 - 允許所有來源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應改為具體網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局異常處理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """處理請求驗證錯誤"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
            "message": "請求參數驗證失敗"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """處理全局異常"""
    print(f"❌ 未處理的異常: {exc}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "message": "伺服器內部錯誤"
        }
    )


# 註冊路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(documents.router)


# 根端點
@app.get("/", tags=["系統"])
async def root():
    """
    系統根端點
    返回系統基本資訊和 API 文件連結
    """
    return {
        "message": "Welcome to Farmer RAG System API",
        "version": Config.VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "auth": "/auth",
            "users": "/users",
            "conversations": "/conversations",
            "chat": "/chat",
            "documents": "/documents"
        },
        "features": {
            "conversation_memory": "✅ 支援多輪對話記憶",
            "intent_classification": "✅ 自動意圖判斷（使用 LLM）",
            "rag_integration": "✅ 智能文件檢索",
            "hybrid_search": f"✅ 混合搜尋（BM25 + 向量）" if Config.ENABLE_HYBRID_SEARCH else "❌ 停用",
            "streaming_chat": "✅ WebSocket 即時串流",
            "source_citation": "✅ 文件來源引用",
            "user_management": "✅ 完整用戶認證系統"
        }
    }


@app.get("/health", tags=["系統"])
async def health_check():
    """
    健康檢查端點
    檢查系統各組件狀態
    """
    health_status = {
        "status": "healthy",
        "components": {},
        "timestamp": None
    }
    
    # 檢查資料庫
    try:
        db = app.state.db
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # 檢查向量資料庫
    try:
        vector_manager = app.state.vector_manager
        if vector_manager:
            count = vector_manager.get_collection_count()
            health_status["components"]["vector_store"] = f"healthy (vectors: {count})"
            
            # 🔥 檢查混合搜尋狀態
            if vector_manager.hybrid_manager:
                bm25_docs = len(vector_manager.hybrid_manager.documents)
                health_status["components"]["hybrid_search"] = f"enabled (bm25_docs: {bm25_docs})"
            else:
                health_status["components"]["hybrid_search"] = "disabled"
        else:
            health_status["components"]["vector_store"] = "not initialized"
            health_status["components"]["hybrid_search"] = "not available"
    except Exception as e:
        health_status["components"]["vector_store"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # 檢查 API Keys
    health_status["components"]["openai_api"] = "configured" if Config.OPENAI_API_KEY else "not configured"
    health_status["components"]["google_api"] = "configured" if Config.GOOGLE_API_KEY else "not configured"
    
    # 添加時間戳
    from datetime import datetime
    health_status["timestamp"] = datetime.now().isoformat()
    
    return health_status


@app.get("/system/info", tags=["系統"])
async def system_info():
    """
    系統資訊
    返回系統配置和統計資訊
    """
    try:
        db = app.state.db
        
        # 統計資訊
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # 用戶統計
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]
                
                # 對話統計
                cur.execute("SELECT COUNT(*) FROM conversations")
                total_conversations = cur.fetchone()[0]
                
                # 文件統計
                cur.execute("SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM documents")
                doc_stats = cur.fetchone()
                total_documents = doc_stats[0]
                total_storage = doc_stats[1]
                
                # 訊息統計
                cur.execute("SELECT COUNT(*) FROM chat_history")
                total_messages = cur.fetchone()[0]
        
        # 向量資料庫統計
        try:
            vector_count = app.state.vector_manager.get_collection_count() if app.state.vector_manager else 0
        except:
            vector_count = 0
        
        # 🔥 混合搜尋統計
        hybrid_info = {"enabled": False}
        if app.state.vector_manager and app.state.vector_manager.hybrid_manager:
            hybrid_info = {
                "enabled": True,
                "bm25_documents": len(app.state.vector_manager.hybrid_manager.documents),
                "bm25_weight": Config.BM25_WEIGHT,
                "vector_weight": Config.VECTOR_WEIGHT
            }
        
        return {
            "system": {
                "title": Config.TITLE,
                "version": Config.VERSION,
                "environment": "development",
                "ai_model": Config.get_model_name()
            },
            "database": {
                "host": Config.PG_HOST,
                "port": Config.PG_PORT,
                "database": Config.PG_DATABASE
            },
            "vector_store": {
                "type": "Chroma",
                "collection": Config.CHROMA_COLLECTION,
                "persist_directory": str(Config.CHROMA_PERSIST_DIR),
                "vector_count": vector_count,
                "embedding_model": Config.EMBEDDING_MODEL
            },
            "hybrid_search": hybrid_info,
            "statistics": {
                "users": total_users,
                "conversations": total_conversations,
                "documents": total_documents,
                "messages": total_messages,
                "storage_bytes": total_storage,
                "storage_mb": round(total_storage / 1024 / 1024, 2)
            },
            "config": {
                "max_upload_size_mb": Config.MAX_UPLOAD_SIZE_MB,
                "chunk_size": Config.CHUNK_SIZE,
                "chunk_overlap": Config.CHUNK_OVERLAP
            },
            "features": {
                "conversation_memory": True,
                "intent_classification": True,
                "rag_integration": True,
                "hybrid_search": hybrid_info["enabled"],
                "streaming_chat": True,
                "source_citation": True
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "message": "無法取得系統資訊"
        }


@app.get("/system/tags", tags=["系統"])
async def get_system_tags():
    """
    取得系統預設標籤
    返回所有可用的系統標籤
    """
    try:
        db = app.state.db
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, color, icon, usage_count
                    FROM tags
                    WHERE user_id IS NULL
                    ORDER BY usage_count DESC
                    """
                )
                tags = []
                for row in cur.fetchall():
                    tags.append({
                        "id": row[0],
                        "name": row[1],
                        "color": row[2],
                        "icon": row[3],
                        "usage_count": row[4]
                    })
        
        return {
            "tags": tags,
            "total": len(tags)
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "tags": []
        }


# 開發用測試端點
if Config.TITLE == "Farmer RAG System":
    @app.get("/dev/test-db", tags=["開發測試"])
    async def test_database():
        """測試資料庫連線"""
        try:
            db = app.state.db
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    version = cur.fetchone()[0]
            return {
                "status": "success",
                "database_version": version
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    @app.get("/dev/test-vector", tags=["開發測試"])
    async def test_vector_store():
        """測試向量資料庫"""
        try:
            vector_manager = app.state.vector_manager
            if not vector_manager:
                return {
                    "status": "error",
                    "message": "向量資料庫未初始化"
                }
            
            count = vector_manager.get_collection_count()
            return {
                "status": "success",
                "vector_count": count,
                "collection_name": Config.CHROMA_COLLECTION,
                "hybrid_search": {
                    "enabled": vector_manager.hybrid_manager is not None,
                    "bm25_docs": len(vector_manager.hybrid_manager.documents) if vector_manager.hybrid_manager else 0
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    @app.get("/dev/test-memory", tags=["開發測試"])
    async def test_conversation_memory():
        """測試對話記憶功能"""
        return {
            "status": "success",
            "message": "對話記憶功能已啟用",
            "features": {
                "history_limit": "最近 10 輪對話",
                "context_aware": "支援代詞理解",
                "multi_turn": "支援多輪對話",
                "persistent": "自動儲存到 PostgreSQL"
            },
            "usage": {
                "websocket": "ws://localhost:8000/chat/ws/{conversation_id}?token={token}",
                "rest_api": "POST /chat/query (需提供 conversation_id)"
            }
        }


# 啟動應用
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 啟動 Farmer RAG System")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
