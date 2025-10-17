# src/models.py
"""
Pydantic 模型定義
用於 API 請求/回應的數據驗證和序列化
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
# 認證相關模型
# ============================================================

class UserRegister(BaseModel):
    """用戶註冊請求"""
    username: str = Field(..., min_length=3, max_length=50, description="用戶名稱")
    email: EmailStr = Field(..., description="電子郵件")
    password: str = Field(..., min_length=6, description="密碼（至少6字元）")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """驗證用戶名只包含字母、數字和底線"""
        if not v.replace('_', '').isalnum():
            raise ValueError('用戶名只能包含字母、數字和底線')
        return v


class UserLogin(BaseModel):
    """用戶登入請求"""
    email: EmailStr = Field(..., description="電子郵件")
    password: str = Field(..., description="密碼")


class Token(BaseModel):
    """JWT Token 回應"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 解碼後的數據"""
    user_id: Optional[int] = None


class UserResponse(BaseModel):
    """用戶資訊回應"""
    id: int
    username: str
    email: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# 對話相關模型
# ============================================================

class ConversationCreate(BaseModel):
    """建立對話請求"""
    title: Optional[str] = Field("新對話", max_length=200, description="對話標題")


class ConversationUpdate(BaseModel):
    """更新對話請求"""
    title: Optional[str] = Field(None, max_length=200, description="對話標題")
    is_pinned: Optional[bool] = Field(None, description="是否置頂")
    is_archived: Optional[bool] = Field(None, description="是否封存")


class ConversationResponse(BaseModel):
    """對話資訊回應"""
    id: str
    title: Optional[str]
    message_count: int
    is_pinned: bool
    is_archived: bool
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """對話詳細資訊回應"""
    id: str
    title: Optional[str]
    message_count: int
    is_pinned: bool
    is_archived: bool
    llm_config: Dict[str, Any] = {}
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    tags: List[Dict[str, Any]] = []
    shares: List[Dict[str, Any]] = []
    
    class Config:
        from_attributes = True


# ============================================================
# 聊天相關模型
# ============================================================

class ChatMessage(BaseModel):
    """聊天訊息請求"""
    message: str = Field(..., min_length=1, max_length=5000, description="訊息內容")
    k: Optional[int] = Field(5, ge=1, le=20, description="RAG 檢索數量")


class ChatMessageResponse(BaseModel):
    """聊天訊息回應"""
    role: str = Field(..., description="訊息角色（user/assistant）")
    content: str = Field(..., description="訊息內容")
    timestamp: Optional[datetime] = None
    sources: Optional[List[Dict[str, Any]]] = None
    intent: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class WebSocketMessage(BaseModel):
    """WebSocket 訊息"""
    type: str = Field(..., description="訊息類型")
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# ============================================================
# RAG 查詢相關模型
# ============================================================

class QueryRequest(BaseModel):
    """RAG 查詢請求"""
    question: str = Field(..., min_length=1, max_length=2000, description="問題")
    k: int = Field(5, ge=1, le=20, description="檢索結果數量")
    conversation_id: Optional[str] = Field(None, description="對話 ID（選填）")


class Source(BaseModel):
    """來源文件"""
    source: str = Field(..., description="來源檔案名稱")
    department: str = Field("", description="部門")
    content: str = Field("", description="內容片段")
    
    class Config:
        from_attributes = True


class QueryResponse(BaseModel):
    """RAG 查詢回應"""
    answer: str = Field(..., description="回答")
    sources: List[Source] = Field([], description="來源列表")
    context_count: int = Field(0, description="上下文數量")
    conversation_id: Optional[str] = None
    intent: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# ============================================================
# 文件管理相關模型
# ============================================================

class DocumentUploadResponse(BaseModel):
    """文件上傳回應"""
    id: str
    filename: str
    file_path: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """文件資訊回應"""
    id: str
    filename: str
    file_size: int
    file_type: str
    status: str
    chunk_count: int
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentDetail(BaseModel):
    """文件詳細資訊"""
    id: str
    filename: str
    file_path: str
    file_size: int
    file_type: str
    content_hash: Optional[str]
    status: str
    error_message: Optional[str]
    chunk_count: int
    vector_count: int
    embedding_model: str
    metadata: Dict[str, Any]
    preview: Optional[str]
    processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentMetadataUpdate(BaseModel):
    """更新文件 metadata"""
    department: Optional[str] = Field(None, max_length=50)
    job_type: Optional[str] = Field(None, max_length=50)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    document_type: Optional[str] = Field(None, max_length=50)


# ============================================================
# 標籤相關模型
# ============================================================

class TagCreate(BaseModel):
    """建立標籤請求"""
    name: str = Field(..., min_length=1, max_length=50, description="標籤名稱")
    color: Optional[str] = Field("#3B82F6", pattern="^#[0-9A-Fa-f]{6}$", description="標籤顏色")
    icon: Optional[str] = Field(None, max_length=50, description="圖示名稱")


class TagResponse(BaseModel):
    """標籤資訊回應"""
    id: int
    name: str
    color: str
    icon: Optional[str]
    usage_count: int
    
    class Config:
        from_attributes = True


# ============================================================
# 分享相關模型
# ============================================================

class ConversationShareCreate(BaseModel):
    """分享對話請求"""
    shared_with_email: EmailStr = Field(..., description="分享對象的 email")
    permission_level: str = Field(..., pattern="^(view|comment|edit)$", description="權限等級")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="過期天數")


class ConversationShareResponse(BaseModel):
    """分享資訊回應"""
    share_id: int
    shared_with_user_id: int
    shared_with_username: str
    permission_level: str
    expires_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# 通知相關模型
# ============================================================

class NotificationResponse(BaseModel):
    """通知回應"""
    id: int
    notification_type: str
    title: str
    message: str
    related_entity_type: Optional[str]
    related_entity_id: Optional[str]
    action_url: Optional[str]
    priority: str
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# 統計相關模型
# ============================================================

class UserStats(BaseModel):
    """用戶統計資訊"""
    user_id: int
    stats: Dict[str, Any]


class DocumentStats(BaseModel):
    """文件統計資訊"""
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    status_distribution: Dict[str, int]
    file_types: List[Dict[str, Any]]


class SystemInfo(BaseModel):
    """系統資訊"""
    system: Dict[str, Any]
    database: Dict[str, Any]
    vector_store: Dict[str, Any]
    statistics: Dict[str, Any]
    config: Dict[str, Any]


# ============================================================
# 偏好設定相關模型
# ============================================================

class UserPreferences(BaseModel):
    """用戶偏好設定"""
    theme: Optional[str] = "light"
    language: Optional[str] = "zh-TW"
    rag_top_k: Optional[int] = 5
    auto_save: Optional[bool] = True


class PreferencesUpdate(BaseModel):
    """更新偏好設定"""
    preferences: Dict[str, Any]


# ============================================================
# 匯出相關模型
# ============================================================

class ConversationExport(BaseModel):
    """對話匯出"""
    conversation_id: str
    title: str
    created_at: str
    message_count: int
    messages: List[Dict[str, Any]]


# ============================================================
# 錯誤回應模型
# ============================================================

class ErrorResponse(BaseModel):
    """錯誤回應"""
    detail: str
    message: Optional[str] = None
    error_code: Optional[str] = None


class ValidationError(BaseModel):
    """驗證錯誤"""
    loc: List[str]
    msg: str
    type: str


# ============================================================
# 健康檢查模型
# ============================================================

class HealthCheck(BaseModel):
    """健康檢查回應"""
    status: str
    components: Dict[str, str]


# ============================================================
# 批次操作模型
# ============================================================

class BatchDeleteRequest(BaseModel):
    """批次刪除請求"""
    ids: List[str] = Field(..., min_length=1, description="要刪除的 ID 列表")


class BatchUpdateRequest(BaseModel):
    """批次更新請求"""
    ids: List[str] = Field(..., min_length=1, description="要更新的 ID 列表")
    updates: Dict[str, Any] = Field(..., description="更新內容")


# ============================================================
# 搜尋過濾模型
# ============================================================

class ConversationFilter(BaseModel):
    """對話過濾條件"""
    include_archived: bool = False
    is_pinned: Optional[bool] = None
    tag_ids: Optional[List[int]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class DocumentFilter(BaseModel):
    """文件過濾條件"""
    status: Optional[str] = None
    department: Optional[str] = None
    year: Optional[int] = None
    file_type: Optional[str] = None


# ============================================================
# WebSocket 事件模型
# ============================================================

class WSConnectEvent(BaseModel):
    """WebSocket 連線事件"""
    type: str = "connected"
    message: str
    conversation_id: str
    user_id: int


class WSMessageEvent(BaseModel):
    """WebSocket 訊息事件"""
    type: str
    content: Optional[str] = None
    chunk_index: Optional[int] = None
    sources: Optional[List[Dict[str, Any]]] = None
    intent: Optional[Dict[str, Any]] = None


class WSErrorEvent(BaseModel):
    """WebSocket 錯誤事件"""
    type: str = "error"
    message: str
    error_code: Optional[str] = None
