# src/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any  # ✅ 添加 Any
from datetime import timedelta

from ..models import (
    UserRegister, 
    UserLogin, 
    Token, 
    UserResponse
)
from ..auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    get_db
)
from ..database import PostgreSQLManager
from ..config import Config

router = APIRouter(prefix="/auth", tags=["認證"])


@router.post("/register", response_model=Dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: PostgreSQLManager = Depends(get_db)):
    """
    用戶註冊
    
    - **username**: 用戶名稱（3-50 字元）
    - **email**: 電子郵件
    - **password**: 密碼（至少 6 字元）
    """
    # 檢查 email 是否已存在
    existing_user = db.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此 Email 已被註冊"
        )
    
    # 檢查 username 是否已存在
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (user_data.username,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="此用戶名稱已被使用"
                )
    
    # 加密密碼
    hashed_password = get_password_hash(user_data.password)
    
    try:
        # 建立用戶
        user = db.create_user(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role="user"
        )
        
        # 建立預設偏好設定
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                default_preferences = [
                    (user["id"], "theme", "light", "string"),
                    (user["id"], "language", "zh-TW", "string"),
                    (user["id"], "rag_top_k", "5", "integer"),
                    (user["id"], "auto_save", "true", "boolean"),
                ]
                cur.executemany(
                    """
                    INSERT INTO user_preferences (user_id, preference_key, preference_value, value_type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, preference_key) DO NOTHING
                    """,
                    default_preferences
                )
                conn.commit()
        
        # 建立歡迎通知
        db.create_notification(
            user_id=user["id"],
            notification_type="system_announcement",
            title="歡迎使用 Farmer RAG 系統",
            message="感謝您的註冊！您可以開始上傳文件並進行智能問答。",
            priority="normal"
        )
        
        # 生成 JWT token
        access_token = create_access_token(
            data={"sub": user["id"]},
            expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "message": "註冊成功",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"註冊失敗: {str(e)}"
        )


@router.post("/login", response_model=Dict)
async def login(user_data: UserLogin, db: PostgreSQLManager = Depends(get_db)):
    """
    用戶登入
    
    - **email**: 電子郵件
    - **password**: 密碼
    
    返回 JWT token 用於後續 API 認證
    """
    # 查詢用戶
    user = db.get_user_by_email(user_data.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email 或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 驗證密碼
    if not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email 或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 檢查帳號是否啟用
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號已被停用，請聯繫管理員"
        )
    
    # 更新最後登入時間
    db.update_last_login(user["id"])
    
    # 生成 JWT token
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "message": "登入成功",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        },
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/login/form", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: PostgreSQLManager = Depends(get_db)
):
    """
    OAuth2 標準登入端點（用於 Swagger UI 測試）
    
    - **username**: 此處使用 email
    - **password**: 密碼
    """
    user = db.get_user_by_email(form_data.username)
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email 或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="帳號已被停用"
        )
    
    db.update_last_login(user["id"])
    
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """取得當前登入用戶資訊"""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"],
        created_at=current_user["created_at"]
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """用戶登出"""
    return {
        "message": "登出成功",
        "user_id": current_user["id"]
    }


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """驗證 JWT token 是否有效"""
    return {
        "valid": True,
        "user_id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"]
    }


@router.put("/password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """修改密碼"""
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密碼至少需要 6 個字元"
        )
    
    user = db.get_user_by_id(current_user["id"])
    
    if not verify_password(old_password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="舊密碼錯誤"
        )
    
    new_hashed_password = get_password_hash(new_password)
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET hashed_password = %s, updated_at = NOW() WHERE id = %s",
                    (new_hashed_password, current_user["id"])
                )
                conn.commit()
        
        db.create_notification(
            user_id=current_user["id"],
            notification_type="security",
            title="密碼已更新",
            message="您的密碼已成功更新",
            priority="normal"
        )
        
        return {"message": "密碼修改成功"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密碼修改失敗: {str(e)}"
        )


@router.get("/preferences")
async def get_user_preferences(
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """取得用戶偏好設定"""
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT preference_key, preference_value, value_type
                    FROM user_preferences
                    WHERE user_id = %s
                    """,
                    (current_user["id"],)
                )
                results = cur.fetchall()
        
        preferences = {}
        for row in results:
            key, value, value_type = row
            if value_type == "integer":
                preferences[key] = int(value)
            elif value_type == "boolean":
                preferences[key] = value.lower() == "true"
            elif value_type == "json":
                import json
                preferences[key] = json.loads(value)
            else:
                preferences[key] = value
        
        return {
            "user_id": current_user["id"],
            "preferences": preferences
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢偏好設定失敗: {str(e)}"
        )


@router.put("/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any],  # ✅ 修改：any → Any
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """更新用戶偏好設定"""
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                for key, value in preferences.items():
                    if isinstance(value, bool):
                        value_type = "boolean"
                        value_str = "true" if value else "false"
                    elif isinstance(value, int):
                        value_type = "integer"
                        value_str = str(value)
                    elif isinstance(value, dict) or isinstance(value, list):
                        value_type = "json"
                        import json
                        value_str = json.dumps(value)
                    else:
                        value_type = "string"
                        value_str = str(value)
                    
                    cur.execute(
                        """
                        INSERT INTO user_preferences (user_id, preference_key, preference_value, value_type)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, preference_key)
                        DO UPDATE SET preference_value = EXCLUDED.preference_value,
                                     value_type = EXCLUDED.value_type,
                                     updated_at = NOW()
                        """,
                        (current_user["id"], key, value_str, value_type)
                    )
                conn.commit()
        
        return {
            "message": "偏好設定已更新",
            "updated_count": len(preferences)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新偏好設定失敗: {str(e)}"
        )


@router.get("/stats")
async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    db: PostgreSQLManager = Depends(get_db)
):
    """取得用戶統計資訊"""
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = %s AND is_archived = FALSE",
                    (current_user["id"],)
                )
                active_conversations = cur.fetchone()[0]
                
                cur.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = %s",
                    (current_user["id"],)
                )
                total_conversations = cur.fetchone()[0]
                
                cur.execute(
                    "SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM documents WHERE user_id = %s",
                    (current_user["id"],)
                )
                doc_stats = cur.fetchone()
                total_documents = doc_stats[0]
                total_storage = doc_stats[1]
                
                cur.execute(
                    "SELECT COALESCE(SUM(message_count), 0) FROM conversations WHERE user_id = %s",
                    (current_user["id"],)
                )
                total_messages = cur.fetchone()[0]
                
                cur.execute(
                    "SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = FALSE",
                    (current_user["id"],)
                )
                unread_notifications = cur.fetchone()[0]
        
        return {
            "user_id": current_user["id"],
            "stats": {
                "conversations": {
                    "active": active_conversations,
                    "total": total_conversations,
                    "archived": total_conversations - active_conversations
                },
                "documents": {
                    "total": total_documents,
                    "storage_bytes": total_storage,
                    "storage_mb": round(total_storage / 1024 / 1024, 2)
                },
                "messages": {
                    "total": total_messages
                },
                "notifications": {
                    "unread": unread_notifications
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢統計資訊失敗: {str(e)}"
        )
