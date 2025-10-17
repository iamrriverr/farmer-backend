# src/routes/documents.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from typing import List, Optional, Dict
from pathlib import Path
import hashlib
import shutil
from datetime import datetime
from psycopg2.extras import RealDictCursor

from ..models import DocumentUploadResponse, DocumentResponse
from ..auth import get_current_user, get_db
from ..database import PostgreSQLManager
from ..config import Config
from ..rag import RAGSystem
from ..vector import VectorStoreManager

router = APIRouter(prefix="/documents", tags=["文件管理"])

# 支援的文件類型
ALLOWED_EXTENSIONS = {
    '.pdf', '.txt', '.docx', '.doc', '.md', 
    '.csv', '.xlsx', '.xls', '.json', '.xml'
}

def get_file_hash(file_path: str) -> str:
    """計算文件的 SHA-256 hash"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """
    驗證上傳的文件
    
    Returns:
        (is_valid, error_message)
    """
    # 檢查文件名
    if not file.filename:
        return False, "文件名不能為空"
    
    # 檢查文件擴展名
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"不支援的文件類型: {file_ext}。支援的類型: {', '.join(ALLOWED_EXTENSIONS)}"
    
    return True, ""


async def process_document_background(
    doc_id: str,
    user_id: int,
    file_path: str
):
    """
    背景任務：處理文件向量化
    
    此函數會在背景執行，避免阻塞 API 回應
    """
    db = PostgreSQLManager()
    
    try:
        # 更新狀態為處理中
        db.update_document_status(doc_id, 'processing')
        
        # 建立通知
        db.create_notification(
            user_id=user_id,
            notification_type="file_processing",
            title="文件處理中",
            message=f"文件正在進行向量化處理...",
            related_entity_type="document",
            related_entity_id=doc_id,
            priority="low"
        )
        
        # 初始化 RAG 系統
        vector_manager = VectorStoreManager()
        rag = RAGSystem(vector_store_manager=vector_manager)
        
        # 取得文件資訊
        doc_info = None
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM documents WHERE id = %s",
                    (doc_id,)
                )
                doc_info = dict(cur.fetchone())
        
        if not doc_info:
            raise Exception("文件不存在")
        
        # 處理文件
        processed_count = rag.process_documents_to_vectors([doc_info])
        
        if processed_count > 0:
            # 更新為完成
            db.update_document_status(doc_id, 'completed')
            
            # 建立完成通知
            db.create_notification(
                user_id=user_id,
                notification_type="file_processed",
                title="文件處理完成",
                message=f"文件「{doc_info['filename']}」已完成向量化處理，可以開始使用",
                related_entity_type="document",
                related_entity_id=doc_id,
                action_url=f"/documents/{doc_id}",
                priority="normal"
            )
        else:
            raise Exception("文件處理失敗")
            
    except Exception as e:
        print(f"❌ 背景處理失敗: {e}")
        db.update_document_status(doc_id, 'failed', str(e))
        
        # 建立失敗通知
        db.create_notification(
            user_id=user_id,
            notification_type="file_processing_failed",
            title="文件處理失敗",
            message=f"文件處理過程中發生錯誤: {str(e)}",
            related_entity_type="document",
            related_entity_id=doc_id,
            priority="high"
        )
    finally:
        db.close()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    department: Optional[str] = None,
    jobtype: Optional[str] = None,
    year: Optional[int] = None,
    documenttype: str = "general",
    auto_process: bool = Query(True, description="是否自動處理文件向量化"),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    上傳文件
    
    - **file**: 文件（必填）
    - **department**: 部門（選填）
    - **jobtype**: 工作類型（選填）
    - **year**: 年份（選填）
    - **documenttype**: 文件類型（預設 general）
    - **auto_process**: 是否自動處理向量化（預設 True）
    
    支援的文件類型: PDF, TXT, DOCX, MD, CSV, XLSX, JSON, XML
    """
    # 驗證文件
    is_valid, error_msg = validate_file(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # 檢查文件大小
    file.file.seek(0, 2)  # 移到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置位置
    
    max_size = Config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超過限制 ({Config.MAX_UPLOAD_SIZE_MB}MB)"
        )
    
    try:
        # 確保上傳目錄存在
        upload_dir = Config.UPLOAD_DIR / str(current_user["id"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一文件名（加上時間戳避免衝突）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / safe_filename
        
        # 儲存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"✅ 文件已儲存: {file_path}")
        
        # 計算文件 hash
        content_hash = get_file_hash(str(file_path))
        
        # 檢查是否已存在相同文件
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, filename FROM documents WHERE user_id = %s AND content_hash = %s",
                    (current_user["id"], content_hash)
                )
                existing = cur.fetchone()
                
                if existing:
                    # 刪除剛上傳的重複文件
                    file_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"文件已存在: {existing[1]}"
                    )
        
        # 插入資料庫
        doc_id = db.insert_document_metadata(
            user_id=current_user["id"],
            filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            file_type=file.content_type or "application/octet-stream",
            content_hash=content_hash,
            department=department,
            jobtype=jobtype,
            year=year,
            documenttype=documenttype
        )
        
        print(f"✅ 文件 metadata 已儲存，ID: {doc_id}")
        
        # 如果啟用自動處理，加入背景任務
        if auto_process:
            background_tasks.add_task(
                process_document_background,
                doc_id,
                current_user["id"],
                str(file_path)
            )
        
        return DocumentUploadResponse(
            id=doc_id,
            filename=file.filename,
            file_path=str(file_path),
            status="processing" if auto_process else "pending",
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 上傳失敗: {e}")
        # 清理已上傳的文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上傳失敗: {str(e)}"
        )


@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    status_filter: Optional[str] = Query(None, description="過濾狀態 (pending/processing/completed/failed)"),
    department: Optional[str] = Query(None, description="過濾部門"),
    year: Optional[int] = Query(None, description="過濾年份"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得當前用戶的文件列表
    
    支援多種過濾條件和分頁
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 建立查詢
                query = "SELECT * FROM documents WHERE user_id = %s"
                params = [current_user["id"]]
                
                # 添加過濾條件
                if status_filter:
                    query += " AND status = %s"
                    params.append(status_filter)
                
                if department:
                    query += " AND metadata->>'department' = %s"
                    params.append(department)
                
                if year:
                    query += " AND metadata->>'year' = %s"
                    params.append(str(year))
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                results = [dict(row) for row in cur.fetchall()]
        
        # 格式化回應
        documents = []
        for row in results:
            documents.append(
                DocumentResponse(
                    id=str(row["id"]),
                    filename=row["filename"],
                    file_size=row["file_size"],
                    file_type=row["file_type"],
                    status=row["status"],
                    chunk_count=row["chunk_count"] or 0,
                    metadata=row["metadata"] or {},
                    created_at=row["created_at"]
                )
            )
        
        return documents
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢文件失敗: {str(e)}"
        )


@router.get("/{document_id}", response_model=Dict)
async def get_document_detail(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得文件詳細資訊
    
    包含文件內容預覽和向量化統計
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 查詢文件
                cur.execute(
                    "SELECT * FROM documents WHERE id = %s AND user_id = %s",
                    (document_id, current_user["id"])
                )
                doc = cur.fetchone()
                
                if not doc:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="文件不存在或無權限存取"
                    )
                
                doc = dict(doc)
                
                # 查詢向量統計
                vector_manager = VectorStoreManager()
                vector_count = 0
                try:
                    results = vector_manager.vector_store._collection.get(
                        where={"document_id": document_id}
                    )
                    vector_count = len(results['ids'])
                except:
                    pass
        
        # 讀取文件內容預覽
        preview = ""
        try:
            file_path = Path(doc["file_path"])
            if file_path.exists() and file_path.suffix in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    preview = f.read(500)  # 前 500 字元
                    if len(preview) == 500:
                        preview += "..."
        except:
            preview = "無法預覽此文件類型"
        
        return {
            "id": str(doc["id"]),
            "filename": doc["filename"],
            "file_path": doc["file_path"],
            "file_size": doc["file_size"],
            "file_type": doc["file_type"],
            "content_hash": doc["content_hash"],
            "status": doc["status"],
            "error_message": doc["error_message"],
            "chunk_count": doc["chunk_count"],
            "vector_count": vector_count,
            "embedding_model": doc["embedding_model"],
            "metadata": doc["metadata"],
            "preview": preview,
            "processed_at": doc["processed_at"].isoformat() if doc["processed_at"] else None,
            "created_at": doc["created_at"].isoformat(),
            "updated_at": doc["updated_at"].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢文件失敗: {str(e)}"
        )


@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    手動觸發文件處理
    
    適用於上傳時未自動處理或處理失敗後重試
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM documents WHERE id = %s AND user_id = %s",
                    (document_id, current_user["id"])
                )
                doc = cur.fetchone()
                
                if not doc:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="文件不存在或無權限存取"
                    )
                
                doc = dict(doc)
                
                if doc["status"] == "processing":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="文件正在處理中"
                    )
                
                if doc["status"] == "completed":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="文件已處理完成"
                    )
        
        # 加入背景任務
        background_tasks.add_task(
            process_document_background,
            document_id,
            current_user["id"],
            doc["file_path"]
        )
        
        return {
            "message": "文件處理已啟動",
            "document_id": document_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"啟動處理失敗: {str(e)}"
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    delete_vectors: bool = Query(True, description="是否同時刪除向量資料"),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    刪除文件
    
    - **document_id**: 文件 ID
    - **delete_vectors**: 是否同時刪除向量資料（預設 True）
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 查詢文件
                cur.execute(
                    "SELECT * FROM documents WHERE id = %s AND user_id = %s",
                    (document_id, current_user["id"])
                )
                doc = cur.fetchone()
                
                if not doc:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="文件不存在或無權限存取"
                    )
                
                doc = dict(doc)
                
                # 刪除實體文件
                file_path = Path(doc["file_path"])
                if file_path.exists():
                    file_path.unlink()
                    print(f"✅ 已刪除實體文件: {file_path}")
                
                # 刪除向量資料
                if delete_vectors:
                    try:
                        vector_manager = VectorStoreManager()
                        vector_manager.vector_store._collection.delete(
                            where={"document_id": document_id}
                        )
                        print(f"✅ 已刪除向量資料")
                    except Exception as e:
                        print(f"⚠️ 刪除向量資料失敗: {e}")
                
                # 刪除資料庫記錄
                cur.execute(
                    "DELETE FROM documents WHERE id = %s",
                    (document_id,)
                )
                conn.commit()
        
        # 建立通知
        db.create_notification(
            user_id=current_user["id"],
            notification_type="file_deleted",
            title="文件已刪除",
            message=f"文件「{doc['filename']}」已刪除",
            priority="low"
        )
        
        return None  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除文件失敗: {str(e)}"
        )


@router.get("/stats/overview")
async def get_documents_stats(
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得文件統計概覽
    
    包含文件數量、儲存空間、狀態分布等
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # 總文件數和總大小
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) as total_files,
                        COALESCE(SUM(file_size), 0) as total_size,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                    FROM documents
                    WHERE user_id = %s
                    """,
                    (current_user["id"],)
                )
                stats = cur.fetchone()
                
                # 文件類型分布
                cur.execute(
                    """
                    SELECT 
                        SUBSTRING(filename FROM '\\.([^.]+)$') as extension,
                        COUNT(*) as count
                    FROM documents
                    WHERE user_id = %s
                    GROUP BY extension
                    ORDER BY count DESC
                    """,
                    (current_user["id"],)
                )
                file_types = [{"extension": row[0], "count": row[1]} for row in cur.fetchall()]
        
        return {
            "total_files": stats[0],
            "total_size_bytes": stats[1],
            "total_size_mb": round(stats[1] / 1024 / 1024, 2),
            "status_distribution": {
                "completed": stats[2],
                "processing": stats[3],
                "pending": stats[4],
                "failed": stats[5]
            },
            "file_types": file_types
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢統計失敗: {str(e)}"
        )


@router.patch("/{document_id}/metadata")
async def update_document_metadata(
    document_id: str,
    department: Optional[str] = None,
    jobtype: Optional[str] = None,
    year: Optional[int] = None,
    documenttype: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    更新文件 metadata
    
    僅更新提供的欄位
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 驗證文件所有權
                cur.execute(
                    "SELECT metadata FROM documents WHERE id = %s AND user_id = %s",
                    (document_id, current_user["id"])
                )
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="文件不存在或無權限存取"
                    )
                
                # 更新 metadata
                metadata = result["metadata"] or {}
                if department is not None:
                    metadata["department"] = department
                if jobtype is not None:
                    metadata["jobtype"] = jobtype
                if year is not None:
                    metadata["year"] = year
                if documenttype is not None:
                    metadata["documenttype"] = documenttype
                
                cur.execute(
                    "UPDATE documents SET metadata = %s, updated_at = NOW() WHERE id = %s",
                    (psycopg2.extras.Json(metadata), document_id)
                )
                conn.commit()
        
        return {
            "message": "Metadata 已更新",
            "document_id": document_id,
            "metadata": metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新失敗: {str(e)}"
        )
