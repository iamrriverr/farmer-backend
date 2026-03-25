
***

## 系統資訊

**基礎 URL**: `http://localhost:8000`  
**API 版本**: 1.0.0  
**認證方式**: JWT Bearer Token  
**文件最後更新**: 2025-10-17

***

## 認證說明

大部分 API 需要在 HTTP Header 中提供 JWT Token：

```
Authorization: Bearer <your_token>
```

Token 可透過註冊或登入端點取得，有效期限預設為 7 天。[1]

***

## 1. 認證模組 (`/auth`)

### 1.1 用戶註冊
- **端點**: `POST /auth/register`
- **描述**: 建立新用戶帳號
- **請求體**:
```json
{
  "username": "string (3-50字元)",
  "email": "user@example.com",
  "password": "string (至少6字元)"
}
```
- **前端驗證**:[1]
  - Email 格式驗證
  - 密碼強度檢查（至少 6 字元）
  - 用戶名長度（3-50 字元）
- **回應**:
```json
{
  "message": "註冊成功",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "user@example.com",
    "role": "user"
  },
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### 1.2 用戶登入
- **端點**: `POST /auth/login`
- **描述**: 用戶登入並取得 JWT Token
- **請求體**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
- **回應**: 同註冊回應

### 1.3 OAuth2 表單登入
- **端點**: `POST /auth/login/form`
- **描述**: 用於 Swagger UI 的 OAuth2 登入
- **Content-Type**: `application/x-www-form-urlencoded`
- **表單參數**:
  - `username`: email
  - `password`: 密碼

### 1.4 取得當前用戶資訊
- **端點**: `GET /auth/me`
- **需要認證**: ✅
- **回應**:
```json
{
  "id": 1,
  "username": "testuser",
  "email": "user@example.com",
  "role": "user",
  "is_active": true,
  "last_login_at": "2025-10-17T10:00:00",
  "created_at": "2025-10-17T10:00:00"
}
```

### 1.5 驗證 Token
- **端點**: `GET /auth/verify`
- **需要認證**: ✅
- **回應**:
```json
{
  "valid": true,
  "user_id": 1,
  "username": "testuser",
  "role": "user"
}
```

### 1.6 登出
- **端點**: `POST /auth/logout`
- **需要認證**: ✅
- **回應**:
```json
{
  "message": "登出成功",
  "user_id": 1
}
```

### 1.7 修改密碼
- **端點**: `PUT /auth/password`
- **需要認證**: ✅
- **請求體**:
```json
{
  "old_password": "oldpass123",
  "new_password": "newpass456"
}
```
- **驗證規則**:[1]
  - 新密碼至少 6 字元
  - 舊密碼必須正確
- **回應**:
```json
{
  "message": "密碼修改成功"
}
```

### 1.8 取得用戶偏好設定
- **端點**: `GET /auth/preferences`
- **需要認證**: ✅
- **回應**:
```json
{
  "user_id": 1,
  "preferences": {
    "theme": "light",
    "language": "zh-TW",
    "rag_top_k": 5,
    "auto_save": true
  }
}
```

### 1.9 更新用戶偏好設定
- **端點**: `PUT /auth/preferences`
- **需要認證**: ✅
- **請求體**:
```json
{
  "theme": "dark",
  "language": "zh-TW",
  "rag_top_k": 10,
  "auto_save": false
}
```
- **可用選項**:[1]
  - `theme`: "light" | "dark"
  - `language`: "zh-TW" | "en"
  - `rag_top_k`: 1-20
  - `auto_save`: boolean

### 1.10 取得用戶統計
- **端點**: `GET /auth/stats`
- **需要認證**: ✅
- **回應**:
```json
{
  "user_id": 1,
  "stats": {
    "conversations": {
      "active": 5,
      "total": 10,
      "archived": 5
    },
    "documents": {
      "total": 15,
      "storage_bytes": 1048576,
      "storage_mb": 1.0
    },
    "messages": {
      "total": 120
    },
    "notifications": {
      "unread": 3
    }
  }
}
```

***

## 2. 對話管理 (`/conversations`)

### 2.1 建立新對話
- **端點**: `POST /conversations/`
- **需要認證**: ✅
- **請求體**:
```json
{
  "title": "新對話"
}
```
- **回應**:
```json
{
  "message": "對話建立成功",
  "conversation": {
    "id": "uuid-string",
    "title": "新對話",
    "created_at": "2025-10-17T10:00:00"
  }
}
```

### 2.2 取得對話列表
- **端點**: `GET /conversations/`
- **需要認證**: ✅
- **查詢參數**:
  - `include_archived` (bool, 預設 false): 是否包含已封存對話
- **排序規則**:[2]
  - 置頂對話優先 (`is_pinned DESC`)
  - 按最後訊息時間排序 (`last_message_at DESC`)
- **回應**:
```json
[
  {
    "id": "conv-uuid-1",
    "title": "對話標題",
    "message_count": 10,
    "is_pinned": false,
    "is_archived": false,
    "last_message_at": "2025-10-17T12:00:00",
    "created_at": "2025-10-16T10:00:00",
    "updated_at": "2025-10-17T12:00:00"
  }
]
```

### 2.3 取得對話詳情
- **端點**: `GET /conversations/{conversation_id}`
- **需要認證**: ✅
- **回應**:
```json
{
  "id": "conv-uuid",
  "title": "對話標題",
  "message_count": 10,
  "is_pinned": false,
  "is_archived": false,
  "model_config": {},
  "last_message_at": "2025-10-17T12:00:00",
  "created_at": "2025-10-16T10:00:00",
  "updated_at": "2025-10-17T12:00:00",
  "tags": [
    {
      "id": 1,
      "name": "工作",
      "color": "#FF0000",
      "icon": "work"
    }
  ],
  "shares": [
    {
      "share_id": 1,
      "shared_with_user_id": 2,
      "shared_with_username": "colleague",
      "permission_level": "view",
      "expires_at": "2025-11-17T12:00:00",
      "created_at": "2025-10-17T12:00:00"
    }
  ]
}
```

### 2.4 取得對話訊息記錄
- **端點**: `GET /conversations/{conversation_id}/messages`
- **需要認證**: ✅
- **查詢參數**:
  - `limit` (int, 1-500, 預設100): 返回訊息數量
  - `offset` (int, 預設0): 分頁偏移量
- **回應**:
```json
[
  {
    "role": "user",
    "content": "問題內容",
    "timestamp": "2025-10-17T12:00:00"
  },
  {
    "role": "assistant",
    "content": "AI 回答",
    "timestamp": "2025-10-17T12:00:05"
  }
]
```

### 2.5 更新對話資訊
- **端點**: `PATCH /conversations/{conversation_id}`
- **需要認證**: ✅
- **請求體** (所有欄位皆選填):
```json
{
  "title": "新標題",
  "is_pinned": true,
  "is_archived": false
}
```
- **回應**:
```json
{
  "message": "對話更新成功",
  "conversation_id": "conv-uuid",
  "updated_fields": ["title", "is_pinned"]
}
```

### 2.6 刪除對話
- **端點**: `DELETE /conversations/{conversation_id}`
- **需要認證**: ✅
- **查詢參數**:
  - `create_snapshot` (bool, 預設 true): 刪除前是否建立快照備份
- **快照保留期限**: 365 天[2]
- **級聯刪除**: 同時刪除聊天記錄、標籤關聯、分享記錄[2]
- **回應**: 204 No Content

### 2.7 搜尋對話
- **端點**: `GET /conversations/search`
- **需要認證**: ✅
- **查詢參數**:
  - `q` (string, 至少1字元): 搜尋關鍵字
- **搜尋範圍**: 對話標題 + 訊息內容[2]
- **回應**:
```json
{
  "query": "水稻",
  "results": [
    {
      "id": "conv-uuid",
      "title": "水稻病蟲害討論",
      "message_count": 15,
      "last_message_at": "2025-10-17T12:00:00",
      "created_at": "2025-10-16T10:00:00"
    }
  ],
  "total": 5
}
```

### 2.8 取得對話標籤
- **端點**: `GET /conversations/{conversation_id}/tags`
- **需要認證**: ✅
- **回應**:
```json
[
  {
    "id": 1,
    "name": "重要",
    "color": "#FF0000",
    "icon": "star"
  }
]
```

### 2.9 為對話新增標籤
- **端點**: `POST /conversations/{conversation_id}/tags/{tag_id}`
- **需要認證**: ✅
- **回應**:
```json
{
  "message": "標籤新增成功",
  "conversation_id": "conv-uuid",
  "tag_id": 1,
  "tag_name": "重要"
}
```

### 2.10 移除對話標籤
- **端點**: `DELETE /conversations/{conversation_id}/tags/{tag_id}`
- **需要認證**: ✅
- **回應**: 204 No Content

### 2.11 分享對話
- **端點**: `POST /conversations/{conversation_id}/share`
- **需要認證**: ✅
- **查詢參數**:
  - `shared_with_email` (string, 必填): 分享對象 email
  - `permission_level` (string, 必填): 權限等級
  - `expires_days` (int, 可選): 過期天數
- **權限等級**:[1]
  - `view`: 僅可查看
  - `comment`: 可查看和評論
  - `edit`: 可編輯
- **回應**:
```json
{
  "message": "對話分享成功",
  "share_id": 1,
  "shared_with": {
    "user_id": 2,
    "username": "colleague",
    "email": "colleague@example.com"
  },
  "permission_level": "view",
  "expires_at": "2025-11-17T12:00:00"
}
```

### 2.12 查詢分享給我的對話
- **端點**: `GET /conversations/shared-with-me`
- **需要認證**: ✅
- **回應**:
```json
[
  {
    "id": "conv-uuid",
    "title": "共享對話",
    "message_count": 20,
    "updated_at": "2025-10-17T12:00:00",
    "owner_username": "owner_name",
    "permission_level": "view",
    "expires_at": "2025-11-17T12:00:00"
  }
]
```

### 2.13 撤銷對話分享
- **端點**: `DELETE /conversations/{conversation_id}/share/{share_id}`
- **需要認證**: ✅ (需為對話擁有者)
- **描述**: 將 `is_active` 設為 FALSE，保留記錄但停用分享[2]
- **回應**: 204 No Content

### 2.14 自動生成對話標題
- **端點**: `POST /conversations/{conversation_id}/generate-title`
- **需要認證**: ✅
- **描述**: 使用 AI 分析前 3 則用戶訊息，自動生成 4-10 字的標題[1]
- **使用的 LLM**: 根據 `PRIMARY_LLM` 配置選擇 GPT 或 Gemini[2]
- **回應**:
```json
{
  "message": "標題生成成功",
  "title": "水稻病蟲害防治討論",
  "conversation_id": "conv-uuid"
}
```

### 2.15 查詢對話快照列表
- **端點**: `GET /conversations/snapshots`
- **需要認證**: ✅
- **查詢參數**:
  - `snapshot_type` (string, 可選): 快照類型（預設 "pre_delete"）
- **回應**:
```json
[
  {
    "id": 1,
    "conversation_id": "original-uuid",
    "title": "原對話標題",
    "message_count": 50,
    "snapshot_type": "pre_delete",
    "snapshot_version": 1,
    "retention_days": 365,
    "created_at": "2025-10-17T12:00:00",
    "expires_at": "2026-10-17T12:00:00",
    "snapshot_data": {
      "conversation_id": "original-uuid",
      "title": "原對話標題",
      "messages": [...],
      "tags": [...],
      "model_config": {},
      "created_at": "2025-10-16T10:00:00"
    }
  }
]
```

### 2.16 從快照還原對話
- **端點**: `POST /conversations/restore-from-snapshot`
- **需要認證**: ✅
- **請求體**:
```json
{
  "snapshot_id": 1,
  "new_title": "已還原 - 原標題"
}
```
- **還原內容**:[1]
  - 建立新對話（新 UUID）
  - 還原所有訊息記錄
  - 還原標籤關聯
  - 還原模型配置
- **回應**:
```json
{
  "message": "對話已成功還原",
  "conversation_id": "new-uuid",
  "restored_message_count": 50,
  "original_conversation_id": "original-uuid"
}
```

***

## 3. 聊天功能 (`/chat`)

### 3.1 REST API 查詢
- **端點**: `POST /chat/query`
- **需要認證**: ✅
- **描述**: 支援對話記憶 + RAG 混合搜尋的同步查詢
- **請求體**:
```json
{
  "question": "水稻病蟲害如何防治?",
  "k": 5,
  "conversation_id": "conv-uuid"
}
```
- **處理流程**:[3]
  1. 意圖分類（判斷是否需要 RAG）
  2. 載入對話歷史（最近 10 輪）
  3. 執行混合搜尋（BM25 + 向量）
  4. 構建 Prompt 並調用 LLM
  5. 儲存對話記錄
- **回應**:
```json
{
  "answer": "AI 生成的回答內容...",
  "sources": [
    {
      "source": "文件名.pdf",
      "department": "農業部",
      "content": "文件片段..."
    }
  ],
  "context_count": 5,
  "conversation_id": "conv-uuid",
  "intent": {
    "type": "rag_query",
    "use_rag": true,
    "confidence": 0.95
  }
}
```

### 3.2 WebSocket 即時聊天
- **端點**: `ws://localhost:8000/chat/ws/{conversation_id}?token={jwt_token}`
- **描述**: 支援串流輸出、對話記憶、混合搜尋、心跳檢測

#### 連線流程[3]
1. 驗證 JWT Token
2. 接受 WebSocket 連線
3. 發送連線成功訊息

#### 發送訊息格式

**標準查詢**:
```json
{
  "type": "message",
  "content": "問題內容",
  "k": 5
}
```

**心跳檢測**:[1]
```json
{
  "type": "ping",
  "timestamp": "2025-10-17T12:00:00"
}
```

**停止生成**:[1]
```json
{
  "type": "stop_generation"
}
```

#### 接收訊息格式

**1. 連線成功**:
```json
{
  "type": "connected",
  "message": "✅ WebSocket 已連線 - AI 模型: gpt-4",
  "conversation_id": "conv-uuid",
  "user_id": 1,
  "ai_model": "gpt-4",
  "hybrid_search": "enabled"
}
```

**2. 意圖判斷**:
```json
{
  "type": "intent",
  "intent": "rag_query",
  "use_rag": true,
  "confidence": 0.95
}
```

**3. 串流內容片段**:
```json
{
  "type": "chunk",
  "content": "AI 回答片段...",
  "chunk_index": 0
}
```

**4. 完成訊息**:
```json
{
  "type": "done",
  "total_chunks": 50,
  "sources": [
    {
      "source": "文件名.pdf",
      "department": "農業部",
      "content": "相關內容..."
    }
  ],
  "full_response": "完整回答內容"
}
```

**5. 心跳回應**:[1]
```json
{
  "type": "pong",
  "timestamp": "2025-10-17T12:00:01"
}
```

**6. 錯誤訊息**:
```json
{
  "type": "error",
  "message": "錯誤描述"
}
```

**7. 警告訊息**:
```json
{
  "type": "warning",
  "message": "資料庫儲存失敗，但回答已生成"
}
```

#### 重連機制[1]
- **策略**: 指數退避（Exponential Backoff）
- **初始延遲**: 1 秒
- **最大重試次數**: 5 次
- **延遲公式**: `delay = min(1000 * 2^attempt, 30000)` 毫秒

### 3.3 測試搜尋方式對比
- **端點**: `POST /chat/test-search-comparison`
- **需要認證**: ✅
- **查詢參數**:
  - `query` (string): 測試查詢
  - `k` (int, 1-20, 預設5): 返回數量
- **描述**: 對比純向量搜尋、純 BM25 搜尋、混合搜尋的結果[3]
- **回應**:
```json
{
  "query": "水稻病蟲害",
  "k": 5,
  "comparison": {
    "vector_only": {
      "method": "Semantic Vector Search",
      "count": 5,
      "results": [...]
    },
    "bm25_only": {
      "method": "BM25 Keyword Search",
      "count": 5,
      "results": [...]
    },
    "hybrid": {
      "method": "Hybrid (BM25 + Vector)",
      "count": 5,
      "weights": {
        "bm25": 0.3,
        "vector": 0.7
      },
      "results": [...]
    }
  }
}
```

### 3.4 測試意圖分類
- **端點**: `POST /chat/classify-intent`
- **需要認證**: ✅
- **查詢參數**:
  - `question` (string): 問題內容
- **回應**:
```json
{
  "question": "水稻病蟲害如何防治?",
  "intent": {
    "type": "rag_query",
    "use_rag": true,
    "confidence": 0.95,
    "reasoning": "問題需要查詢專業文件知識"
  }
}
```

***

## 4. 文件管理 (`/documents`)

### 4.1 上傳文件
- **端點**: `POST /documents/upload`
- **需要認證**: ✅
- **Content-Type**: `multipart/form-data`
- **表單參數**:
  - `file` (File, 必填): 文件檔案
  - `department` (string, 可選): 部門名稱
  - `jobtype` (string, 可選): 工作類型
  - `year` (int, 可選): 年份
  - `documenttype` (string, 預設 "general"): 文件類型
  - `auto_process` (bool, 預設 true): 是否自動處理向量化
- **支援格式**: PDF, TXT, DOCX, DOC, MD, CSV, XLSX, XLS, JSON, XML[1]
- **檔案大小限制**: 根據 `MAX_UPLOAD_SIZE_MB` 配置
- **處理流程**:[1]
  1. 驗證檔案格式和大小
  2. 計算 SHA-256 Hash（檢查重複）
  3. 儲存到 `UPLOAD_DIR/{user_id}/`
  4. 建立資料庫記錄
  5. 背景任務處理向量化
- **回應**:
```json
{
  "id": "doc-uuid",
  "filename": "document.pdf",
  "file_path": "/data/uploads/1/20251017_120000_document.pdf",
  "file_size": 1024000,
  "status": "processing",
  "created_at": "2025-10-17T12:00:00"
}
```

### 4.2 取得文件列表
- **端點**: `GET /documents/`
- **需要認證**: ✅
- **查詢參數**:
  - `status_filter` (string): 過濾狀態（pending/processing/completed/failed）
  - `department` (string): 過濾部門
  - `year` (int): 過濾年份
  - `limit` (int, 1-500, 預設100): 返回數量
  - `offset` (int, 預設0): 分頁偏移量
- **排序規則**: 按建立時間降序 (`created_at DESC`)[1]
- **回應**:
```json
[
  {
    "id": "doc-uuid",
    "filename": "document.pdf",
    "file_size": 1024000,
    "file_type": "application/pdf",
    "status": "completed",
    "chunk_count": 50,
    "metadata": {
      "department": "農業部",
      "year": 2024,
      "jobtype": "研究報告"
    },
    "created_at": "2025-10-17T12:00:00",
    "processed_at": "2025-10-17T12:05:00"
  }
]
```

### 4.3 取得文件詳情
- **端點**: `GET /documents/{document_id}`
- **需要認證**: ✅
- **回應**:
```json
{
  "id": "doc-uuid",
  "filename": "document.pdf",
  "file_path": "/data/uploads/1/document.pdf",
  "file_size": 1024000,
  "file_type": "application/pdf",
  "content_hash": "sha256hash...",
  "status": "completed",
  "error_message": null,
  "chunk_count": 50,
  "vector_count": 50,
  "embedding_model": "text-embedding-3-small",
  "metadata": {
    "department": "農業部",
    "year": 2024
  },
  "preview": "文件內容前 500 字元...",
  "processed_at": "2025-10-17T12:05:00",
  "created_at": "2025-10-17T12:00:00",
  "updated_at": "2025-10-17T12:05:00"
}
```

### 4.4 更新文件 Metadata
- **端點**: `PATCH /documents/{document_id}/metadata`
- **需要認證**: ✅
- **請求體** (所有欄位皆選填):
```json
{
  "department": "農業部",
  "jobtype": "研究報告",
  "year": 2024,
  "documenttype": "report"
}
```
- **回應**:
```json
{
  "message": "Metadata 更新成功",
  "document_id": "doc-uuid",
  "updated_fields": ["department", "year"]
}
```

### 4.5 手動處理文件
- **端點**: `POST /documents/{document_id}/process`
- **需要認證**: ✅
- **描述**: 適用於上傳時未自動處理或處理失敗後重試[1]
- **處理步驟**:[1]
  1. 載入文件內容
  2. 文字切塊（Chunking）
  3. 生成 Embeddings
  4. 儲存到 ChromaDB
  5. 建立 BM25 索引
  6. 更新狀態為 "completed"
- **回應**:
```json
{
  "message": "文件處理已啟動",
  "document_id": "doc-uuid",
  "status": "processing"
}
```

### 4.6 刪除文件
- **端點**: `DELETE /documents/{document_id}`
- **需要認證**: ✅
- **查詢參數**:
  - `delete_vectors` (bool, 預設 true): 是否同時刪除向量資料
- **刪除內容**:[1]
  - 實體檔案
  - 資料庫記錄
  - ChromaDB 向量
  - BM25 索引
- **回應**: 204 No Content

### 4.7 取得文件統計
- **端點**: `GET /documents/stats/overview`
- **需要認證**: ✅
- **回應**:
```json
{
  "total_files": 15,
  "total_size_bytes": 10485760,
  "total_size_mb": 10.0,
  "status_distribution": {
    "completed": 12,
    "processing": 1,
    "pending": 1,
    "failed": 1
  },
  "file_types": [
    {"extension": "pdf", "count": 8},
    {"extension": "txt", "count": 5},
    {"extension": "docx", "count": 2}
  ],
  "department_distribution": [
    {"department": "農業部", "count": 10},
    {"department": "環境部", "count": 5}
  ]
}
```

***

## 5. 用戶管理 (`/users`)

### 5.1 取得個人完整資料
- **端點**: `GET /users/me/profile`
- **需要認證**: ✅
- **回應**:
```json
{
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "user@example.com",
    "role": "user",
    "is_active": true,
    "last_login_at": "2025-10-17T10:00:00",
    "created_at": "2025-10-17T10:00:00"
  },
  "statistics": {
    "active_conversations": 5,
    "total_conversations": 10,
    "total_documents": 15,
    "storage_used": 10485760
  },
  "preferences": {
    "theme": "dark",
    "language": "zh-TW",
    "rag_top_k": 5
  }
}
```

### 5.2 更新個人資料
- **端點**: `PATCH /users/me/profile`
- **需要認證**: ✅
- **請求體**:
```json
{
  "username": "newusername"
}
```
- **回應**:
```json
{
  "message": "個人資料更新成功",
  "user": {
    "id": 1,
    "username": "newusername",
    "email": "user@example.com"
  }
}
```

### 5.3 取得通知列表
- **端點**: `GET /users/me/notifications`
- **需要認證**: ✅
- **查詢參數**:
  - `unread_only` (bool, 預設 false): 只顯示未讀通知
  - `limit` (int, 1-200, 預設50): 返回數量
  - `offset` (int, 預設0): 分頁偏移量
- **通知類型**:[1]
  - `system_announcement`: 系統公告
  - `conversation_created`: 對話建立
  - `conversation_deleted`: 對話刪除
  - `file_processing`: 文件處理中
  - `file_processed`: 文件處理完成
  - `file_failed`: 文件處理失敗
  - `share_received`: 收到分享
  - `security`: 安全提醒
  - `system_maintenance`: 系統維護
- **回應**:
```json
[
  {
    "id": 1,
    "type": "file_processed",
    "title": "文件處理完成",
    "message": "document.pdf 已成功處理",
    "priority": "normal",
    "is_read": false,
    "action_url": "/documents/doc-uuid",
    "related_entity_type": "document",
    "related_entity_id": "doc-uuid",
    "created_at": "2025-10-17T12:05:00",
    "read_at": null
  }
]
```

### 5.4 標記通知為已讀
- **端點**: `PATCH /users/me/notifications/{notification_id}/read`
- **需要認證**: ✅
- **回應**:
```json
{
  "message": "通知已標記為已讀",
  "notification_id": 1
}
```

### 5.5 標記所有通知為已讀
- **端點**: `POST /users/me/notifications/mark-all-read`
- **需要認證**: ✅
- **回應**:
```json
{
  "message": "所有通知已標記為已讀",
  "updated_count": 5
}
```

### 5.6 刪除通知
- **端點**: `DELETE /users/me/notifications/{notification_id}`
- **需要認證**: ✅
- **回應**: 204 No Content

### 5.7 取得標籤列表
- **端點**: `GET /users/me/tags`
- **需要認證**: ✅
- **描述**: 返回用戶自訂標籤 + 系統預設標籤[1]
- **回應**:
```json
[
  {
    "id": 1,
    "name": "重要",
    "color": "#FF0000",
    "icon": "star",
    "user_id": 1,
    "is_system": false,
    "created_at": "2025-10-17T10:00:00"
  },
  {
    "id": 2,
    "name": "工作",
    "color": "#0000FF",
    "icon": "work",
    "user_id": null,
    "is_system": true,
    "created_at": "2025-10-01T00:00:00"
  }
]
```

### 5.8 建立自訂標籤
- **端點**: `POST /users/me/tags`
- **需要認證**: ✅
- **請求體**:
```json
{
  "name": "重要",
  "color": "#FF0000",
  "icon": "star"
}
```
- **回應**:
```json
{
  "message": "標籤建立成功",
  "tag": {
    "id": 1,
    "name": "重要",
    "color": "#FF0000",
    "icon": "star"
  }
}
```

### 5.9 更新標籤
- **端點**: `PATCH /users/me/tags/{tag_id}`
- **需要認證**: ✅
- **請求體** (所有欄位皆選填):
```json
{
  "name": "超重要",
  "color": "#FF00FF",
  "icon": "flag"
}
```

### 5.10 刪除標籤
- **端點**: `DELETE /users/me/tags/{tag_id}`
- **需要認證**: ✅
- **描述**: 級聯刪除所有對話的標籤關聯[1]
- **回應**: 204 No Content

### 5.11 取得活動統計
- **端點**: `GET /users/me/activity`
- **需要認證**: ✅
- **查詢參數**:
  - `days` (int, 1-90, 預設7): 查詢最近幾天的活動
- **回應**:
```json
{
  "period": "last_7_days",
  "daily_stats": [
    {
      "date": "2025-10-17",
      "conversations_created": 2,
      "messages_sent": 15,
      "documents_uploaded": 3
    }
  ],
  "top_conversations": [
    {
      "id": "conv-uuid",
      "title": "水稻病蟲害討論",
      "message_count": 50
    }
  ],
  "summary": {
    "total_messages": 120,
    "total_documents": 10,
    "most_active_day": "2025-10-15"
  }
}
```

### 5.12 取得所有用戶 (管理員)
- **端點**: `GET /users/admin/all`
- **需要認證**: ✅ (需要 admin 角色)
- **查詢參數**:
  - `limit` (int, 1-1000, 預設100)
  - `offset` (int, 預設0)
- **回應**:
```json
[
  {
    "id": 1,
    "username": "user1",
    "email": "user1@example.com",
    "role": "user",
    "is_active": true,
    "last_login_at": "2025-10-17T10:00:00",
    "created_at": "2025-10-01T00:00:00"
  }
]
```

### 5.13 啟用/停用用戶 (管理員)
- **端點**: `PATCH /users/admin/{user_id}/toggle-active`
- **需要認證**: ✅ (需要 admin 角色)
- **描述**: 切換用戶的 `is_active` 狀態[1]
- **回應**:
```json
{
  "message": "用戶狀態已更新",
  "user_id": 2,
  "is_active": false
}
```

***

## 6. 系統端點

### 6.1 系統首頁
- **端點**: `GET /`
- **回應**:
```json
{
  "message": "Welcome to Farmer RAG System API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "redoc": "/redoc",
  "endpoints": {
    "auth": "/auth",
    "conversations": "/conversations",
    "chat": "/chat",
    "documents": "/documents",
    "users": "/users"
  },
  "features": {
    "rag_enabled": true,
    "hybrid_search": true,
    "websocket_chat": true,
    "intent_classification": true
  }
}
```

### 6.2 健康檢查
- **端點**: `GET /health`
- **回應**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-17T12:00:00",
  "components": {
    "database": "healthy",
    "vector_store": "healthy (vectors: 1000)",
    "hybrid_search": "enabled (bm25_docs: 500)",
    "openai_api": "configured",
    "google_api": "configured"
  },
  "uptime_seconds": 86400
}
```

### 6.3 系統資訊
- **端點**: `GET /system/info`
- **回應**:
```json
{
  "system": {
    "title": "Farmer RAG System",
    "version": "1.0.0",
    "environment": "development",
    "primary_llm": "gpt",
    "ai_model": "gpt-4"
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "farmer_rag"
  },
  "vector_store": {
    "type": "chromadb",
    "collection": "farmer_documents",
    "total_vectors": 1000
  },
  "hybrid_search": {
    "enabled": true,
    "bm25_weight": 0.3,
    "vector_weight": 0.7
  },
  "statistics": {
    "total_users": 50,
    "total_conversations": 200,
    "total_documents": 100,
    "total_messages": 5000
  },
  "config": {
    "max_upload_size_mb": 50,
    "chunk_size": 500,
    "chunk_overlap": 50,
    "rag_top_k": 5
  },
  "features": {
    "websocket": true,
    "intent_classification": true,
    "conversation_memory": true,
    "auto_title_generation": true,
    "snapshots": true
  }
}
```

### 6.4 系統標籤
- **端點**: `GET /system/tags`
- **描述**: 取得系統預設標籤列表
- **回應**:
```json
[
  {"id": 1, "name": "工作", "color": "#0000FF", "icon": "work"},
  {"id": 2, "name": "個人", "color": "#00FF00", "icon": "person"},
  {"id": 3, "name": "學習", "color": "#FFFF00", "icon": "school"}
]
```

***

## 7. 錯誤碼說明

| 狀態碼 | 說明 | 常見原因 |
|--------|------|----------|
| 200 | 成功 | - |
| 201 | 建立成功 | POST 請求成功建立資源 |
| 204 | 刪除成功 (無內容) | DELETE 請求成功 |
| 400 | 請求參數錯誤 | 缺少必填欄位、格式錯誤 |
| 401 | 未認證或 Token 無效 | Token 過期、未提供 Token |
| 403 | 權限不足 | 嘗試訪問其他用戶資源、非管理員訪問管理端點 |
| 404 | 資源不存在 | 無效的 ID、資源已刪除 |
| 409 | 資源衝突 | Email 已存在、檔案 Hash 重複 |
| 422 | 請求驗證失敗 | Pydantic 模型驗證失敗 |
| 500 | 伺服器內部錯誤 | 資料庫連線失敗、未預期錯誤 |
| 503 | 服務不可用 | 向量資料庫未啟動、LLM API 失敗 |

***

## 8. 快速開始範例

### Python 範例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 註冊
response = requests.post(f"{BASE_URL}/auth/register", json={
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
})
token = response.json()["access_token"]

# 2. 設定認證 Header
headers = {"Authorization": f"Bearer {token}"}

# 3. 建立對話
conversation = requests.post(
    f"{BASE_URL}/conversations/",
    json={"title": "測試對話"},
    headers=headers
).json()

conversation_id = conversation["conversation"]["id"]

# 4. 上傳文件
with open("document.pdf", "rb") as f:
    files = {"file": f}
    data = {
        "department": "農業部",
        "year": 2024,
        "auto_process": True
    }
    doc_response = requests.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        data=data,
        headers=headers
    )

print(f"文件上傳: {doc_response.json()}")

# 5. 等待處理完成（輪詢狀態）
import time
doc_id = doc_response.json()["id"]
while True:
    status = requests.get(
        f"{BASE_URL}/documents/{doc_id}",
        headers=headers
    ).json()
    
    if status["status"] == "completed":
        print("文件處理完成")
        break
    elif status["status"] == "failed":
        print(f"處理失敗: {status['error_message']}")
        break
    
    time.sleep(2)

# 6. 發送查詢
response = requests.post(
    f"{BASE_URL}/chat/query",
    json={
        "question": "水稻病蟲害如何防治?",
        "k": 5,
        "conversation_id": conversation_id
    },
    headers=headers
)

result = response.json()
print(f"AI 回答: {result['answer']}")
print(f"來源數量: {result['context_count']}")
for source in result["sources"]:
    print(f"- {source['source']} ({source['department']})")
```

### JavaScript (WebSocket) 範例

```javascript
const BASE_URL = "http://localhost:8000";
const WS_URL = "ws://localhost:8000";

// 1. 登入取得 Token
async function login() {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      email: 'test@example.com',
      password: 'password123'
    })
  });
  
  const data = await response.json();
  return data.access_token;
}

// 2. 建立對話
async function createConversation(token) {
  const response = await fetch(`${BASE_URL}/conversations/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({title: '測試對話'})
  });
  
  const data = await response.json();
  return data.conversation.id;
}

// 3. WebSocket 聊天
async function startChat() {
  const token = await login();
  const conversationId = await createConversation(token);
  
  const ws = new WebSocket(`${WS_URL}/chat/ws/${conversationId}?token=${token}`);
  
  // 心跳檢測
  let heartbeatInterval;
  
  ws.onopen = () => {
    console.log("WebSocket 已連線");
    
    // 每 30 秒發送心跳
    heartbeatInterval = setInterval(() => {
      ws.send(JSON.stringify({
        type: "ping",
        timestamp: new Date().toISOString()
      }));
    }, 30000);
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
      case "connected":
        console.log(`✅ ${data.message}`);
        console.log(`AI 模型: ${data.ai_model}`);
        
        // 發送查詢
        ws.send(JSON.stringify({
          type: "message",
          content: "水稻病蟲害如何防治?",
          k: 5
        }));
        break;
        
      case "intent":
        console.log(`意圖: ${data.intent} (confidence: ${data.confidence})`);
        break;
        
      case "chunk":
        process.stdout.write(data.content);
        break;
        
      case "done":
        console.log(`\n\n✅ 完成 (共 ${data.total_chunks} 個片段)`);
        console.log(`\n來源 (${data.sources.length}):`);
        data.sources.forEach(s => {
          console.log(`- ${s.source} (${s.department})`);
        });
        break;
        
      case "pong":
        console.log("心跳回應收到");
        break;
        
      case "error":
        console.error(`❌ 錯誤: ${data.message}`);
        break;
        
      case "warning":
        console.warn(`⚠️ 警告: ${data.message}`);
        break;
    }
  };
  
  ws.onerror = (error) => {
    console.error("WebSocket 錯誤:", error);
  };
  
  ws.onclose = (event) => {
    console.log(`WebSocket 已關閉 (code: ${event.code})`);
    clearInterval(heartbeatInterval);
    
    // 實作重連機制
    if (event.code !== 1000) {
      console.log("嘗試重新連線...");
      setTimeout(() => startChat(), 1000);
    }
  };
}

// 啟動
startChat();
```

### cURL 範例

```bash
# 1. 註冊
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"password123"}'

# 2. 登入
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  | jq -r '.access_token')

# 3. 建立對話
CONV_ID=$(curl -X POST http://localhost:8000/conversations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"測試對話"}' \
  | jq -r '.conversation.id')

# 4. 上傳文件
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "department=農業部" \
  -F "year=2024" \
  -F "auto_process=true"

# 5. 發送查詢
curl -X POST http://localhost:8000/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"水稻病蟲害如何防治?\",\"k\":5,\"conversation_id\":\"$CONV_ID\"}"

# 6. 查詢對話列表
curl -X GET "http://localhost:8000/conversations/?include_archived=false" \
  -H "Authorization: Bearer $TOKEN"

# 7. 搜尋對話
curl -X GET "http://localhost:8000/conversations/search?q=水稻" \
  -H "Authorization: Bearer $TOKEN"

# 8. 健康檢查（無需認證）
curl -X GET http://localhost:8000/health
```

***

## 9. 進階功能說明

### 9.1 混合搜尋 (Hybrid Search)

系統整合 **BM25 關鍵字搜尋** 和 **向量語義搜尋**，透過加權組合提升檢索精確度。[1]

**配置參數**:
- `ENABLE_HYBRID_SEARCH`: true/false
- `BM25_WEIGHT`: BM25 權重（預設 0.3）
- `VECTOR_WEIGHT`: 向量權重（預設 0.7）

**優勢**:
- 關鍵字搜尋捕捉精確匹配
- 向量搜尋理解語義相似性
- 組合後精確度提升 15-30%

### 9.2 對話記憶 (Conversation Memory)

系統自動記住最近 **10 輪對話**，支援上下文理解和代詞指涉解析。[3]

**範例**:
```
用戶: 水稻病蟲害有哪些?
AI: 主要有稻熱病、稻螟蟲...

用戶: 如何防治它們?  ← AI 能理解「它們」指的是前述病蟲害
AI: 針對稻熱病和稻螟蟲，可以採用...
```

### 9.3 意圖分類 (Intent Classification)

系統自動判斷用戶問題是否需要 RAG 檢索。[1]

**意圖類型**:
- `rag_query`: 需要文件知識（觸發 RAG）
- `general_chat`: 一般對話（直接回答）

**範例**:
- "水稻病蟲害如何防治?" → `rag_query`
- "你好" → `general_chat`
- "今天天氣如何?" → `general_chat`

### 9.4 文件處理流程

**完整流程**:[1]
1. 上傳檔案
2. 計算 SHA-256 Hash（防止重複）
3. 儲存到 `UPLOAD_DIR/{user_id}/`
4. 背景任務啟動
5. DocumentLoader 載入文件
6. 文字切塊（Chunk Size: 500, Overlap: 50）
7. 生成 Embeddings (OpenAI text-embedding-3-small)
8. 儲存到 ChromaDB
9. 建立 BM25 索引
10. 更新狀態為 "completed"
11. 建立通知

**支援的文件類型**:
- 文字: TXT, MD
- 文件: PDF, DOCX, DOC
- 資料: CSV, XLSX, XLS, JSON, XML

### 9.5 快照與備份

**自動快照**:[2]
- 刪除對話前自動建立快照（`create_snapshot=true`）
- 保留期限: 365 天
- 包含內容: 對話標題、所有訊息、標籤、模型配置

**手動還原**:
- 從快照列表選擇要還原的對話
- 系統建立新對話（新 UUID）
- 還原所有歷史訊息和標籤

### 9.6 分享與協作

**權限等級**:[1]
- `view`: 僅可查看對話內容
- `comment`: 可查看和評論
- `edit`: 可編輯和新增訊息

**過期機制**:
- 可設定分享過期天數
- 過期後自動失效
- 擁有者可隨時撤銷分享

***

## 10. 互動式文件

### Swagger UI
訪問 `http://localhost:8000/docs` 使用互動式 API 文件進行測試。

**功能**:
- 瀏覽所有端點
- 直接測試 API
- 查看請求/回應範例
- OAuth2 認證整合

### ReDoc
訪問 `http://localhost:8000/redoc` 查看美觀的 API 文件。

***

## 11. 最佳實踐

### 安全性
- 永不在前端儲存明文密碼
- Token 儲存在 localStorage，定期檢查有效性
- HTTPS 部署環境必須啟用
- 定期更新密碼

### 效能優化
- 使用 WebSocket 進行即時聊天（減少 HTTP 開銷）
- 文件上傳後使用背景任務處理（避免阻塞）
- 對話列表使用分頁（limit/offset）
- 啟用混合搜尋提升檢索精確度

### 錯誤處理
- 實作 WebSocket 重連機制（指數退避）
- 上傳大文件前檢查檔案大小
- 捕捉並顯示友善錯誤訊息
- 記錄錯誤日誌供調試

***

**文件生成日期**: 2025-10-17  
**文件版本**: 2.0  
**適用系統版本**: 1.0.0

[1](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/80394444/71b83f46-83b9-4149-b2af-ec5b1190ed59/Wan-Zheng-Liu-Cheng.pdf)
[2](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/80394444/26ec485a-86b6-4038-a74c-facc48b3326f/conversations.py)
[3](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/80394444/d4cdcbb4-90d7-4e36-bc01-1f14b5bd2f74/chat.py)
[4](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/80394444/3b210bbc-1881-45b2-ac09-dae89c286225/main.py)
