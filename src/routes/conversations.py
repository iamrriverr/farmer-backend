# src/routes/conversations.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict
import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor, Json

from ..models import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ChatMessageResponse
)
from ..auth import get_current_user, get_db
from ..database import PostgreSQLManager
from ..config import Config  # ✅ 添加這行
router = APIRouter(prefix="/conversations", tags=["對話管理"])


from ..models import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ChatMessageResponse
)
from ..auth import get_current_user, get_db
from ..database import PostgreSQLManager

router = APIRouter(prefix="/conversations", tags=["對話管理"])


@router.post("/", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    建立新對話
    
    - **title**: 對話標題（選填，預設為「新對話」）
    """
    try:
        conversation = db.create_conversation(
            user_id=current_user["id"],
            title=conversation_data.title or "新對話"
        )
        
        # 建立通知
        db.create_notification(
            user_id=current_user["id"],
            notification_type="conversation_created",
            title="新對話已建立",
            message=f"對話「{conversation['title']}」已成功建立",
            related_entity_type="conversation",
            related_entity_id=str(conversation["id"]),
            priority="low"
        )
        
        return {
            "message": "對話建立成功",
            "conversation": {
                "id": str(conversation["id"]),
                "title": conversation["title"],
                "created_at": conversation["created_at"].isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"建立對話失敗: {str(e)}"
        )


@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    include_archived: bool = Query(False, description="是否包含已封存的對話"),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得當前用戶的所有對話列表
    
    - **include_archived**: 是否包含已封存的對話（預設 False）
    
    對話按置頂優先，然後依更新時間倒序排列
    """
    try:
        conversations = db.get_user_conversations(
            user_id=current_user["id"],
            include_archived=include_archived
        )
        
        # 轉換為 response model 格式
        return [
            ConversationResponse(
                id=str(conv["id"]),
                title=conv["title"],
                message_count=conv["message_count"],
                is_pinned=conv["is_pinned"],
                is_archived=conv["is_archived"],
                last_message_at=conv["last_message_at"],
                created_at=conv["created_at"],
                updated_at=conv["updated_at"]
            )
            for conv in conversations
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢對話失敗: {str(e)}"
        )


@router.get("/{conversation_id}", response_model=Dict)
async def get_conversation_detail(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得特定對話的詳細資訊
    
    包含對話基本資訊、標籤、分享狀態等
    """
    # 查詢對話
    conversation = db.get_conversation_by_id(conversation_id, current_user["id"])
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在或無權限存取"
        )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 查詢標籤
                cur.execute(
                    """
                    SELECT t.id, t.name, t.color, t.icon
                    FROM tags t
                    JOIN conversation_tags ct ON t.id = ct.tag_id
                    WHERE ct.conversation_id = %s
                    """,
                    (conversation_id,)
                )
                tags = [dict(row) for row in cur.fetchall()]
                
                # 查詢分享狀態
                cur.execute(
                    """
                    SELECT cs.id, cs.shared_with, u.username, cs.permission_level, 
                           cs.is_active, cs.expires_at, cs.created_at
                    FROM conversation_shares cs
                    JOIN users u ON cs.shared_with = u.id
                    WHERE cs.conversation_id = %s AND cs.is_active = TRUE
                    """,
                    (conversation_id,)
                )
                shares = [dict(row) for row in cur.fetchall()]
        
        return {
            "id": str(conversation["id"]),
            "title": conversation["title"],
            "message_count": conversation["message_count"],
            "is_pinned": conversation["is_pinned"],
            "is_archived": conversation["is_archived"],
            "model_config": conversation["model_config"],
            "last_message_at": conversation["last_message_at"].isoformat() if conversation["last_message_at"] else None,
            "created_at": conversation["created_at"].isoformat(),
            "updated_at": conversation["updated_at"].isoformat(),
            "tags": tags,
            "shares": [
                {
                    "share_id": share["id"],
                    "shared_with_user_id": share["shared_with"],
                    "shared_with_username": share["username"],
                    "permission_level": share["permission_level"],
                    "expires_at": share["expires_at"].isoformat() if share["expires_at"] else None,
                    "created_at": share["created_at"].isoformat()
                }
                for share in shares
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢對話詳情失敗: {str(e)}"
        )


@router.get("/{conversation_id}/messages", response_model=List[ChatMessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=500, description="返回訊息數量上限"),
    offset: int = Query(0, ge=0, description="跳過的訊息數量"),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得對話的聊天記錄
    
    - **conversation_id**: 對話 ID
    - **limit**: 返回訊息數量上限（預設 100，最多 500）
    - **offset**: 分頁偏移量
    
    訊息按時間順序返回（最舊的在前）
    """
    # 驗證對話所有權
    conversation = db.get_conversation_by_id(conversation_id, current_user["id"])
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在或無權限存取"
        )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT message, created_at
                    FROM chat_history
                    WHERE session_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s OFFSET %s
                    """,
                    (conversation_id, limit, offset)
                )
                results = cur.fetchall()
        
        # 解析 JSONB message 欄位
        messages = []
        for row in results:
            msg_data = row["message"]
            messages.append(
                ChatMessageResponse(
                    role=msg_data.get("type", "human"),  # "human" or "ai"
                    content=msg_data.get("content", ""),
                    timestamp=row["created_at"]
                )
            )
        
        return messages
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢聊天記錄失敗: {str(e)}"
        )


@router.patch("/{conversation_id}", response_model=Dict)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    更新對話資訊
    
    - **title**: 對話標題
    - **is_pinned**: 是否置頂
    - **is_archived**: 是否封存
    """
    # 驗證對話所有權
    conversation = db.get_conversation_by_id(conversation_id, current_user["id"])
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在或無權限存取"
        )
    
    try:
        # 準備更新資料
        update_fields = update_data.model_dump(exclude_none=True)
        
        if update_fields:
            db.update_conversation(conversation_id, **update_fields)
        
        return {
            "message": "對話已更新",
            "conversation_id": conversation_id,
            "updated_fields": list(update_fields.keys())
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新對話失敗: {str(e)}"
        )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    create_snapshot: bool = Query(True, description="刪除前是否建立快照"),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    刪除對話
    
    - **conversation_id**: 對話 ID
    - **create_snapshot**: 刪除前是否建立快照備份（預設 True）
    
    刪除對話會同時刪除所有相關的聊天記錄、標籤關聯等
    """
    # 驗證對話所有權
    conversation = db.get_conversation_by_id(conversation_id, current_user["id"])
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在或無權限存取"
        )
    
    try:
        # 建立快照（如果需要）
        if create_snapshot:
            with db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 查詢所有訊息
                    cur.execute(
                        "SELECT message, created_at FROM chat_history WHERE session_id = %s ORDER BY created_at",
                        (conversation_id,)
                    )
                    messages = [dict(row) for row in cur.fetchall()]
                    
                    # 查詢標籤
                    cur.execute(
                        """
                        SELECT t.name FROM tags t
                        JOIN conversation_tags ct ON t.id = ct.tag_id
                        WHERE ct.conversation_id = %s
                        """,
                        (conversation_id,)
                    )
                    tags = [row[0] for row in cur.fetchall()]
                    
                    # 建立快照資料
                    snapshot_data = {
                        "conversation_id": conversation_id,
                        "title": conversation["title"],
                        "messages": [
                            {
                                "role": msg["message"].get("type"),
                                "content": msg["message"].get("content"),
                                "timestamp": msg["created_at"].isoformat()
                            }
                            for msg in messages
                        ],
                        "tags": tags,
                        "model_config": conversation["model_config"],
                        "created_at": conversation["created_at"].isoformat()
                    }
                    
                    # 插入快照
                    cur.execute(
                        """
                        INSERT INTO conversation_snapshots 
                        (conversation_id, snapshot_data, snapshot_version, message_count, 
                         snapshot_type, created_by, retention_days)
                        VALUES (%s, %s, 1, %s, 'pre_delete', %s, 365)
                        """,
                        (
                            conversation_id,
                            psycopg2.extras.Json(snapshot_data),
                            len(messages),
                            current_user["id"]
                        )
                    )
                    conn.commit()
        
        # 刪除對話（CASCADE 會自動刪除相關記錄）
        db.delete_conversation(conversation_id)
        
        # 建立通知
        db.create_notification(
            user_id=current_user["id"],
            notification_type="conversation_deleted",
            title="對話已刪除",
            message=f"對話「{conversation['title']}」已刪除" + ("（已建立備份快照）" if create_snapshot else ""),
            priority="low"
        )
        
        return None  # 204 No Content
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除對話失敗: {str(e)}"
        )


# === 標籤管理 ===

@router.get("/{conversation_id}/tags", response_model=List[Dict])
async def get_conversation_tags(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得對話的標籤列表
    """
    # 驗證對話所有權
    conversation = db.get_conversation_by_id(conversation_id, current_user["id"])
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在或無權限存取"
        )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT t.id, t.name, t.color, t.icon
                    FROM tags t
                    JOIN conversation_tags ct ON t.id = ct.tag_id
                    WHERE ct.conversation_id = %s
                    """,
                    (conversation_id,)
                )
                tags = [dict(row) for row in cur.fetchall()]
        
        return tags
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢標籤失敗: {str(e)}"
        )


@router.post("/{conversation_id}/tags/{tag_id}", status_code=status.HTTP_201_CREATED)
async def add_tag_to_conversation(
    conversation_id: str,
    tag_id: int,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    為對話新增標籤
    
    - **conversation_id**: 對話 ID
    - **tag_id**: 標籤 ID
    """
    # 驗證對話所有權
    conversation = db.get_conversation_by_id(conversation_id, current_user["id"])
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在或無權限存取"
        )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # 檢查標籤是否存在且屬於該用戶或系統標籤
                cur.execute(
                    "SELECT name FROM tags WHERE id = %s AND (user_id = %s OR user_id IS NULL)",
                    (tag_id, current_user["id"])
                )
                tag = cur.fetchone()
                
                if not tag:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="標籤不存在或無權限使用"
                    )
                
                # 新增標籤關聯（如果已存在會觸發 UNIQUE 約束）
                cur.execute(
                    """
                    INSERT INTO conversation_tags (conversation_id, tag_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (conversation_id, tag_id)
                )
                conn.commit()
        
        return {
            "message": "標籤已新增",
            "conversation_id": conversation_id,
            "tag_id": tag_id,
            "tag_name": tag[0]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"新增標籤失敗: {str(e)}"
        )


@router.delete("/{conversation_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tag_from_conversation(
    conversation_id: str,
    tag_id: int,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    從對話移除標籤
    """
    # 驗證對話所有權
    conversation = db.get_conversation_by_id(conversation_id, current_user["id"])
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在或無權限存取"
        )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM conversation_tags WHERE conversation_id = %s AND tag_id = %s",
                    (conversation_id, tag_id)
                )
                conn.commit()
        
        return None  # 204 No Content
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除標籤失敗: {str(e)}"
        )


# === 分享管理 ===

@router.post("/{conversation_id}/share", response_model=Dict)
async def share_conversation(
    conversation_id: str,
    shared_with_email: str,
    permission_level: str = Query(..., regex="^(view|comment|edit)$"),
    expires_days: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    分享對話給其他用戶
    
    - **shared_with_email**: 分享對象的 email
    - **permission_level**: 權限等級（view/comment/edit）
    - **expires_days**: 過期天數（選填，NULL 表示永久有效）
    """
    # 驗證對話所有權
    conversation = db.get_conversation_by_id(conversation_id, current_user["id"])
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在或無權限存取"
        )
    
    # 查詢分享對象
    shared_with_user = db.get_user_by_email(shared_with_email)
    
    if not shared_with_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分享對象不存在"
        )
    
    if shared_with_user["id"] == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能分享給自己"
        )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 計算過期時間
                expires_at_sql = f"NOW() + INTERVAL '{expires_days} days'" if expires_days else "NULL"
                
                cur.execute(
                    f"""
                    INSERT INTO conversation_shares 
                    (conversation_id, shared_by, shared_with, permission_level, expires_at)
                    VALUES (%s, %s, %s, %s, {expires_at_sql})
                    ON CONFLICT (conversation_id, shared_with)
                    DO UPDATE SET 
                        permission_level = EXCLUDED.permission_level,
                        is_active = TRUE,
                        expires_at = EXCLUDED.expires_at,
                        updated_at = NOW()
                    RETURNING id, expires_at
                    """,
                    (conversation_id, current_user["id"], shared_with_user["id"], permission_level)
                )
                result = cur.fetchone()
                conn.commit()
        
        # 建立通知給接收者
        db.create_notification(
            user_id=shared_with_user["id"],
            notification_type="share_received",
            title="收到對話分享",
            message=f"{current_user['username']} 分享了對話「{conversation['title']}」給您",
            related_entity_type="conversation",
            related_entity_id=conversation_id,
            action_url=f"/conversations/{conversation_id}",
            priority="normal"
        )
        
        return {
            "message": "對話已分享",
            "share_id": result["id"],
            "shared_with": {
                "user_id": shared_with_user["id"],
                "username": shared_with_user["username"],
                "email": shared_with_user["email"]
            },
            "permission_level": permission_level,
            "expires_at": result["expires_at"].isoformat() if result["expires_at"] else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分享對話失敗: {str(e)}"
        )


@router.delete("/{conversation_id}/share/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_conversation_share(
    conversation_id: str,
    share_id: int,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    撤銷對話分享
    
    只有對話擁有者可以撤銷分享
    """
    # 驗證對話所有權
    conversation = db.get_conversation_by_id(conversation_id, current_user["id"])
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="對話不存在或無權限存取"
        )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conversation_shares
                    SET is_active = FALSE, updated_at = NOW()
                    WHERE id = %s AND conversation_id = %s AND shared_by = %s
                    """,
                    (share_id, conversation_id, current_user["id"])
                )
                
                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="分享記錄不存在或無權限撤銷"
                    )
                
                conn.commit()
        
        return None  # 204 No Content
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"撤銷分享失敗: {str(e)}"
        )


@router.get("/shared-with-me", response_model=List[Dict])
async def get_shared_conversations(
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得其他人分享給我的對話列表
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        c.id, c.title, c.message_count, c.updated_at,
                        cs.permission_level, cs.expires_at,
                        u.username as owner_username
                    FROM conversations c
                    JOIN conversation_shares cs ON c.id = cs.conversation_id
                    JOIN users u ON c.user_id = u.id
                    WHERE cs.shared_with = %s 
                      AND cs.is_active = TRUE
                      AND (cs.expires_at IS NULL OR cs.expires_at > NOW())
                    ORDER BY c.updated_at DESC
                    """,
                    (current_user["id"],)
                )
                results = [dict(row) for row in cur.fetchall()]
        
        return [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "message_count": row["message_count"],
                "updated_at": row["updated_at"].isoformat(),
                "owner_username": row["owner_username"],
                "permission_level": row["permission_level"],
                "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None
            }
            for row in results
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢分享對話失敗: {str(e)}"
        )

# src/routes/conversations.py
# 在現有檔案末尾添加以下函數

@router.post("/conversations/{conversation_id}/generate-title")
async def generate_conversation_title(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    自動生成對話標題
    
    根據對話的前幾條訊息，使用 AI 自動生成簡潔的標題
    """
    try:
        # 取得前 3 條用戶訊息
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT content FROM chat_history 
                    WHERE conversation_id = %s AND role = 'user'
                    ORDER BY created_at 
                    LIMIT 3
                    """,
                    (conversation_id,)
                )
                messages = [row[0] for row in cur.fetchall()]
        
        if not messages:
            return {
                "title": "新對話",
                "conversation_id": conversation_id
            }
        
        # 使用 AI 生成標題
        from langchain_google_genai import ChatGoogleGenerativeAI
        from ..config import Config
        
        llm = ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.3
        )
        
        prompt = f"""
根據以下對話內容，生成一個簡短精確的標題（4-10個字）：

{chr(10).join(messages)}

要求：
1. 只返回標題文字，不要其他說明
2. 標題要能概括對話主題
3. 使用繁體中文
4. 不要使用標點符號
"""
        
        title = llm.invoke(prompt).content.strip()
        
        # 更新標題到資料庫
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conversations 
                    SET title = %s, updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                    """,
                    (title, conversation_id, current_user["id"])
                )
                conn.commit()
        
        return {
            "message": "標題已自動生成",
            "title": title,
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成標題失敗: {str(e)}"
        )


@router.get("/conversations/search")
async def search_conversations(
    q: str = Query(..., min_length=1, description="搜尋關鍵字"),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    搜尋對話
    
    在對話標題和內容中搜尋關鍵字
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT 
                        c.id, 
                        c.title, 
                        c.message_count,
                        c.last_message_at,
                        c.created_at
                    FROM conversations c
                    LEFT JOIN chat_history ch ON c.id = ch.conversation_id
                    WHERE c.user_id = %s 
                    AND (
                        c.title ILIKE %s 
                        OR ch.content ILIKE %s
                    )
                    ORDER BY c.last_message_at DESC
                    LIMIT 20
                    """,
                    (current_user["id"], f"%{q}%", f"%{q}%")
                )
                results = cur.fetchall()
        
        return {
            "query": q,
            "results": [
                {
                    "id": row[0],
                    "title": row[1],
                    "message_count": row[2],
                    "last_message_at": row[3],
                    "created_at": row[4]
                }
                for row in results
            ],
            "total": len(results)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜尋失敗: {str(e)}"
        )

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

@router.post("/conversations/{conversation_id}/generate-title")
async def generate_conversation_title(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    自動生成對話標題
    
    根據對話的前幾條訊息，使用 AI 自動生成簡潔的標題
    """
    try:
        # 取得前 3 條用戶訊息
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT content FROM chat_history 
                    WHERE conversation_id = %s AND role = 'user'
                    ORDER BY created_at 
                    LIMIT 3
                    """,
                    (conversation_id,)
                )
                messages = [row[0] for row in cur.fetchall()]
        
        if not messages:
            return {
                "title": "新對話",
                "conversation_id": conversation_id
            }
        
        # 使用 LLM 生成標題
        if Config.PRIMARY_LLM == "gpt":
            llm = ChatOpenAI(
                model=Config.GPT_MODEL,
                openai_api_key=Config.OPENAI_API_KEY,
                temperature=0.3,
                max_tokens=50
            )
        else:
            llm = ChatGoogleGenerativeAI(
                model=Config.GEMINI_MODEL,
                google_api_key=Config.GOOGLE_API_KEY,
                temperature=0.3
            )
        
        prompt = f"""
根據以下對話內容，生成一個簡短精確的標題（4-10個字）：

{chr(10).join(messages)}

要求：
1. 只返回標題文字，不要其他說明
2. 標題要能概括對話主題
3. 使用繁體中文
4. 不要使用標點符號
"""
        
        title = llm.invoke(prompt).content.strip()
        
        # 更新標題到資料庫
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conversations 
                    SET title = %s, updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                    """,
                    (title, conversation_id, current_user["id"])
                )
                conn.commit()
        
        return {
            "message": "標題已自動生成",
            "title": title,
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成標題失敗: {str(e)}"
        )


@router.get("/conversations/search")
async def search_conversations(
    q: str = Query(..., min_length=1, description="搜尋關鍵字"),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    搜尋對話
    
    在對話標題和內容中搜尋關鍵字
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT 
                        c.id, 
                        c.title, 
                        c.message_count,
                        c.last_message_at,
                        c.created_at
                    FROM conversations c
                    LEFT JOIN chat_history ch ON c.id = ch.conversation_id
                    WHERE c.user_id = %s 
                    AND (
                        c.title ILIKE %s 
                        OR ch.content ILIKE %s
                    )
                    ORDER BY c.last_message_at DESC
                    LIMIT 20
                    """,
                    (current_user["id"], f"%{q}%", f"%{q}%")
                )
                results = cur.fetchall()
        
        return {
            "query": q,
            "results": [
                {
                    "id": row[0],
                    "title": row[1],
                    "message_count": row[2],
                    "last_message_at": row[3],
                    "created_at": row[4]
                }
                for row in results
            ],
            "total": len(results)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜尋失敗: {str(e)}"
        )