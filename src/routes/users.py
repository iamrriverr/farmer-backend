# src/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Optional
from psycopg2.extras import RealDictCursor

from ..auth import get_current_user, get_db
from ..database import PostgreSQLManager

router = APIRouter(prefix="/users", tags=["用戶管理"])


@router.get("/me/profile", response_model=Dict)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得當前用戶的完整資料
    
    包含基本資訊、統計數據、偏好設定等
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # 統計資訊
                cur.execute(
                    """
                    SELECT 
                        (SELECT COUNT(*) FROM conversations WHERE user_id = %s AND is_archived = FALSE) as active_conversations,
                        (SELECT COUNT(*) FROM conversations WHERE user_id = %s) as total_conversations,
                        (SELECT COUNT(*) FROM documents WHERE user_id = %s) as total_documents,
                        (SELECT COALESCE(SUM(file_size), 0) FROM documents WHERE user_id = %s) as storage_used,
                        (SELECT COALESCE(SUM(message_count), 0) FROM conversations WHERE user_id = %s) as total_messages,
                        (SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = FALSE) as unread_notifications
                    """,
                    (current_user["id"],) * 6
                )
                stats = cur.fetchone()
                
                # 最近活動
                cur.execute(
                    """
                    SELECT title, last_message_at, message_count
                    FROM conversations
                    WHERE user_id = %s AND last_message_at IS NOT NULL
                    ORDER BY last_message_at DESC
                    LIMIT 5
                    """,
                    (current_user["id"],)
                )
                recent_conversations = cur.fetchall()
        
        return {
            "user": {
                "id": current_user["id"],
                "username": current_user["username"],
                "email": current_user["email"],
                "role": current_user["role"],
                "created_at": current_user["created_at"].isoformat()
            },
            "statistics": {
                "active_conversations": stats[0],
                "total_conversations": stats[1],
                "total_documents": stats[2],
                "storage_used_bytes": stats[3],
                "storage_used_mb": round(stats[3] / 1024 / 1024, 2),
                "total_messages": stats[4],
                "unread_notifications": stats[5]
            },
            "recent_activity": [
                {
                    "title": conv[0],
                    "last_message_at": conv[1].isoformat() if conv[1] else None,
                    "message_count": conv[2]
                }
                for conv in recent_conversations
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢失敗: {str(e)}"
        )


@router.patch("/me/profile", response_model=Dict)
async def update_my_profile(
    username: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    更新當前用戶的基本資料
    
    - **username**: 新的用戶名稱（可選）
    """
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要提供一個更新欄位"
        )
    
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 檢查用戶名是否已被使用
                cur.execute(
                    "SELECT id FROM users WHERE username = %s AND id != %s",
                    (username, current_user["id"])
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="用戶名稱已被使用"
                    )
                
                # 更新用戶資料
                cur.execute(
                    """
                    UPDATE users 
                    SET username = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, username, email, role, updated_at
                    """,
                    (username, current_user["id"])
                )
                result = cur.fetchone()
                conn.commit()
        
        return {
            "message": "資料已更新",
            "user": dict(result)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新失敗: {str(e)}"
        )


@router.get("/me/notifications", response_model=List[Dict])
async def get_my_notifications(
    unread_only: bool = Query(False, description="只顯示未讀通知"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得當前用戶的通知列表
    
    - **unread_only**: 是否只顯示未讀通知
    - **limit**: 返回數量限制
    - **offset**: 分頁偏移量
    """
    try:
        sql = """
        SELECT id, notification_type, title, message, 
               related_entity_type, related_entity_id, action_url,
               priority, is_read, read_at, created_at
        FROM notifications
        WHERE user_id = %s
        """
        params = [current_user["id"]]
        
        if unread_only:
            sql += " AND is_read = FALSE"
        
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                results = cur.fetchall()
        
        return [
            {
                "id": row["id"],
                "type": row["notification_type"],
                "title": row["title"],
                "message": row["message"],
                "related_entity": {
                    "type": row["related_entity_type"],
                    "id": row["related_entity_id"]
                } if row["related_entity_type"] else None,
                "action_url": row["action_url"],
                "priority": row["priority"],
                "is_read": row["is_read"],
                "read_at": row["read_at"].isoformat() if row["read_at"] else None,
                "created_at": row["created_at"].isoformat()
            }
            for row in results
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢通知失敗: {str(e)}"
        )


@router.patch("/me/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    標記通知為已讀
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notifications
                    SET is_read = TRUE, read_at = NOW()
                    WHERE id = %s AND user_id = %s
                    """,
                    (notification_id, current_user["id"])
                )
                
                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="通知不存在或無權限"
                    )
                
                conn.commit()
        
        return {"message": "通知已標記為已讀"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"標記失敗: {str(e)}"
        )


@router.post("/me/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    標記所有通知為已讀
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notifications
                    SET is_read = TRUE, read_at = NOW()
                    WHERE user_id = %s AND is_read = FALSE
                    """,
                    (current_user["id"],)
                )
                updated_count = cur.rowcount
                conn.commit()
        
        return {
            "message": "所有通知已標記為已讀",
            "updated_count": updated_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"標記失敗: {str(e)}"
        )


@router.delete("/me/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    刪除通知
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM notifications WHERE id = %s AND user_id = %s",
                    (notification_id, current_user["id"])
                )
                
                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="通知不存在或無權限"
                    )
                
                conn.commit()
        
        return {"message": "通知已刪除"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除失敗: {str(e)}"
        )


@router.get("/me/tags", response_model=List[Dict])
async def get_my_tags(
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得當前用戶的自訂標籤（包含系統標籤）
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, color, icon, usage_count, created_at
                    FROM tags
                    WHERE user_id = %s OR user_id IS NULL
                    ORDER BY usage_count DESC, created_at DESC
                    """,
                    (current_user["id"],)
                )
                results = cur.fetchall()
        
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "color": row["color"],
                "icon": row["icon"],
                "usage_count": row["usage_count"],
                "is_system": row.get("user_id") is None,
                "created_at": row["created_at"].isoformat()
            }
            for row in results
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢標籤失敗: {str(e)}"
        )


@router.post("/me/tags", response_model=Dict)
async def create_tag(
    name: str,
    color: str = "#3B82F6",
    icon: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    建立自訂標籤
    
    - **name**: 標籤名稱
    - **color**: 標籤顏色（Hex 格式，如 #FF0000）
    - **icon**: 圖示名稱（可選）
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO tags (user_id, name, color, icon, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    RETURNING id, name, color, icon, usage_count, created_at
                    """,
                    (current_user["id"], name, color, icon)
                )
                result = cur.fetchone()
                conn.commit()
        
        return {
            "message": "標籤已建立",
            "tag": dict(result)
        }
        
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="標籤名稱已存在"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"建立標籤失敗: {str(e)}"
        )


@router.patch("/me/tags/{tag_id}")
async def update_tag(
    tag_id: int,
    name: Optional[str] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    更新自訂標籤
    
    只能更新自己建立的標籤
    """
    try:
        updates = []
        params = []
        
        if name:
            updates.append("name = %s")
            params.append(name)
        
        if color:
            updates.append("color = %s")
            params.append(color)
        
        if icon is not None:
            updates.append("icon = %s")
            params.append(icon)
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要提供一個更新欄位"
            )
        
        params.extend([tag_id, current_user["id"]])
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                sql = f"""
                UPDATE tags
                SET {', '.join(updates)}
                WHERE id = %s AND user_id = %s
                """
                cur.execute(sql, params)
                
                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="標籤不存在或無權限更新（系統標籤無法修改）"
                    )
                
                conn.commit()
        
        return {"message": "標籤已更新"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新失敗: {str(e)}"
        )


@router.delete("/me/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    刪除自訂標籤
    
    只能刪除自己建立的標籤
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM tags WHERE id = %s AND user_id = %s",
                    (tag_id, current_user["id"])
                )
                
                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="標籤不存在或無權限刪除（系統標籤無法刪除）"
                    )
                
                conn.commit()
        
        return {"message": "標籤已刪除"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除失敗: {str(e)}"
        )


@router.get("/me/activity", response_model=Dict)
async def get_my_activity(
    days: int = Query(7, ge=1, le=90, description="查詢天數"),
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得當前用戶的活動統計
    
    - **days**: 查詢最近幾天的活動（預設 7 天）
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # 每日訊息數量
                cur.execute(
                    """
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM chat_history ch
                    JOIN conversations c ON ch.session_id::uuid = c.id
                    WHERE c.user_id = %s
                      AND ch.created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                    """,
                    (current_user["id"], days)
                )
                daily_messages = [
                    {"date": row[0].isoformat(), "count": row[1]}
                    for row in cur.fetchall()
                ]
                
                # 最活躍的對話
                cur.execute(
                    """
                    SELECT title, message_count, last_message_at
                    FROM conversations
                    WHERE user_id = %s
                      AND updated_at >= NOW() - INTERVAL '%s days'
                    ORDER BY message_count DESC
                    LIMIT 5
                    """,
                    (current_user["id"], days)
                )
                active_conversations = [
                    {
                        "title": row[0],
                        "message_count": row[1],
                        "last_message_at": row[2].isoformat() if row[2] else None
                    }
                    for row in cur.fetchall()
                ]
                
                # 文件上傳統計
                cur.execute(
                    """
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM documents
                    WHERE user_id = %s
                      AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                    """,
                    (current_user["id"], days)
                )
                daily_uploads = [
                    {"date": row[0].isoformat(), "count": row[1]}
                    for row in cur.fetchall()
                ]
        
        return {
            "period": f"最近 {days} 天",
            "daily_messages": daily_messages,
            "active_conversations": active_conversations,
            "daily_uploads": daily_uploads
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢活動失敗: {str(e)}"
        )


# ========================================
# 管理員功能（需要 admin 權限）
# ========================================

async def require_admin(current_user: dict = Depends(get_current_user)):
    """驗證管理員權限"""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )
    return current_user


@router.get("/admin/all", response_model=List[Dict], dependencies=[Depends(require_admin)])
async def get_all_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    取得所有用戶列表（僅管理員）
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, username, email, role, is_active, 
                           last_login_at, created_at
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset)
                )
                results = cur.fetchall()
        
        return [dict(row) for row in results]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢失敗: {str(e)}"
        )


@router.patch("/admin/{user_id}/toggle-active", dependencies=[Depends(require_admin)])
async def toggle_user_active(
    user_id: int,
    db: PostgreSQLManager = Depends(get_db)
):
    """
    啟用/停用用戶（僅管理員）
    """
    try:
        with db.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET is_active = NOT is_active, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, username, is_active
                    """,
                    (user_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="用戶不存在"
                    )
                
                conn.commit()
        
        return {
            "message": f"用戶已{'啟用' if result['is_active'] else '停用'}",
            "user": dict(result)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"操作失敗: {str(e)}"
        )
