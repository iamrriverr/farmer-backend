# src/auth.py
"""
JWT 認證和密碼處理工具模組（使用 Argon2）
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .config import Config
from .database import PostgreSQLManager

# 使用 Argon2 密碼加密（比 bcrypt 更安全且無長度限制）
pwd_hasher = PasswordHasher()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證密碼
    
    Args:
        plain_password: 明文密碼
        hashed_password: 加密後的密碼
        
    Returns:
        是否匹配
    """
    try:
        pwd_hasher.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False
    except Exception as e:
        print(f"密碼驗證錯誤: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    加密密碼
    
    Args:
        password: 明文密碼
        
    Returns:
        加密後的密碼
    """
    return pwd_hasher.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    建立 JWT access token
    
    Args:
        data: 要編碼的數據（通常包含 sub: user_id）
        expires_delta: 過期時間增量
        
    Returns:
        JWT token 字串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解碼 JWT token
    
    Args:
        token: JWT token
        
    Returns:
        解碼後的 payload，失敗返回 None
    """
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: PostgreSQLManager = Depends()
):
    """
    取得當前登入用戶（Dependency）
    
    從 JWT token 中提取用戶 ID 並查詢用戶資訊
    
    Args:
        token: JWT token（自動從 Authorization header 提取）
        db: 資料庫管理器實例
        
    Returns:
        用戶資訊字典
        
    Raises:
        HTTPException: 認證失敗
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑證",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 解碼 token
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        user_id: int = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # 從資料庫查詢用戶
    user = db.get_user_by_id(user_id)
    
    if user is None:
        raise credentials_exception
    
    # 檢查帳號是否啟用
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用戶帳號已停用"
        )
    
    return user


async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """
    取得當前活躍用戶（Dependency）
    
    確保用戶帳號是啟用狀態
    """
    if not current_user.get("is_active", True):
        raise HTTPException(status_code=400, detail="用戶帳號已停用")
    return current_user


async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """
    取得當前管理員用戶（Dependency）
    
    確保用戶是管理員角色
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理員權限"
        )
    return current_user


def get_db():
    """
    Dependency 注入：取得資料庫管理器實例
    
    Returns:
        PostgreSQLManager 實例
    """
    return PostgreSQLManager()


# WebSocket 認證相關
def verify_websocket_token(token: str) -> Optional[dict]:
    """
    驗證 WebSocket 連線的 JWT token
    
    Args:
        token: JWT token
        
    Returns:
        用戶資訊字典，失敗返回 None
    """
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        user_id: int = payload.get("sub")
        
        if user_id is None:
            return None
        
        # 從資料庫取得用戶資訊
        db = PostgreSQLManager()
        user = db.get_user_by_id(user_id)
        db.close()
        
        return user
        
    except JWTError:
        return None
