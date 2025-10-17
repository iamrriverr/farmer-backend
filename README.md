好的！根據你的系統功能，這裡是完整的 API 文件：

***

# 📚 Farmer RAG System - 完整 API 文件

## 🎯 基本資訊

**Base URL**: `http://localhost:8000`

**API 文件**: 
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**認證方式**: JWT Bearer Token

**Content-Type**: `application/json`

**版本**: v2.0.0

***

## 📋 目錄

1. [認證 API](#1-認證-api)
2. [對話管理 API](#2-對話管理-api)
3. [即時聊天 API](#3-即時聊天-api)
4. [文件管理 API](#4-文件管理-api)
5. [歷史記錄 API](#5-歷史記錄-api)
6. [智能功能 API](#6-智能功能-api)
7. [系統 API](#7-系統-api)

***

## 1. 認證 API

### 1.1 用戶註冊

註冊新用戶並自動登入

```http
POST /auth/register
Content-Type: application/json
```

**請求 Body**:
```json
{
  "username": "farmer123",
  "email": "farmer@example.com",
  "password": "SecurePass123"
}
```

**回應** (201 Created):
```json
{
  "message": "註冊成功",
  "user": {
    "id": 1,
    "username": "farmer123",
    "email": "farmer@example.com",
    "role": "user",
    "created_at": "2025-10-11T00:00:00"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**錯誤回應**:
- `400 Bad Request` - 驗證失敗
- `409 Conflict` - Email 已存在

***

### 1.2 用戶登入

使用 Email 和密碼登入

```http
POST /auth/login
Content-Type: application/json
```

**請求 Body**:
```json
{
  "email": "farmer@example.com",
  "password": "SecurePass123"
}
```

**回應** (200 OK):
```json
{
  "message": "登入成功",
  "user": {
    "id": 1,
    "username": "farmer123",
    "email": "farmer@example.com",
    "role": "user",
    "last_login": "2025-10-11T09:00:00"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**錯誤回應**:
- `401 Unauthorized` - 帳號或密碼錯誤
- `403 Forbidden` - 帳號已停用

***

### 1.3 取得當前用戶資訊

取得目前登入用戶的詳細資訊

```http
GET /auth/me
Authorization: Bearer {token}
```

**回應** (200 OK):
```json
{
  "id": 1,
  "username": "farmer123",
  "email": "farmer@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2025-10-10T00:00:00",
  "last_login": "2025-10-11T09:00:00"
}
```

***

### 1.4 驗證 Token

驗證 JWT Token 是否有效

```http
GET /auth/verify
Authorization: Bearer {token}
```

**回應** (200 OK):
```json
{
  "valid": true,
  "user_id": 1,
  "username": "farmer123",
  "role": "user",
  "expires_at": "2025-10-12T09:00:00"
}
```

***

### 1.5 登出

登出當前用戶

```http
POST /auth/logout
Authorization: Bearer {token}
```

**回應** (200 OK):
```json
{
  "message": "登出成功",
  "user_id": 1
}
```

***

### 1.6 修改密碼

修改用戶密碼

```http
PUT /auth/password
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "old_password": "SecurePass123",
  "new_password": "NewSecurePass456"
}
```

**回應** (200 OK):
```json
{
  "message": "密碼修改成功"
}
```

***

### 1.7 取得用戶統計

取得用戶的使用統計資訊

```http
GET /auth/stats
Authorization: Bearer {token}
```

**回應** (200 OK):
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
      "storage_bytes": 10485760,
      "storage_mb": 10.0
    },
    "messages": {
      "total": 150
    },
    "notifications": {
      "unread": 3
    }
  }
}
```

***

### 1.8 取得/更新用戶偏好設定

取得用戶偏好設定

```http
GET /auth/preferences
Authorization: Bearer {token}
```

**回應** (200 OK):
```json
{
  "user_id": 1,
  "preferences": {
    "theme": "light",
    "language": "zh-TW",
    "rag_top_k": 5,
    "auto_save": true,
    "notifications_enabled": true
  }
}
```

更新用戶偏好設定

```http
PUT /auth/preferences
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "theme": "dark",
  "rag_top_k": 10,
  "notifications_enabled": false
}
```

**回應** (200 OK):
```json
{
  "message": "偏好設定已更新",
  "updated_count": 3
}
```

***

## 2. 對話管理 API

### 2.1 建立新對話

建立一個新的對話

```http
POST /conversations/
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "title": "水稻種植諮詢"
}
```

**回應** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "title": "水稻種植諮詢",
  "message_count": 0,
  "is_pinned": false,
  "is_archived": false,
  "created_at": "2025-10-11T09:30:00",
  "updated_at": "2025-10-11T09:30:00",
  "last_message_at": null
}
```

***

### 2.2 取得對話列表

取得用戶的所有對話

```http
GET /conversations/
Authorization: Bearer {token}
```

**查詢參數**:
- `include_archived` (boolean) - 是否包含已封存的對話，預設 `false`
- `limit` (integer) - 返回數量，預設 `50`
- `offset` (integer) - 偏移量，預設 `0`

**回應** (200 OK):
```json
{
  "conversations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "水稻病蟲害防治",
      "message_count": 10,
      "is_pinned": true,
      "is_archived": false,
      "last_message_at": "2025-10-11T09:00:00",
      "created_at": "2025-10-10T10:00:00",
      "updated_at": "2025-10-11T09:00:00"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "title": "補助申請諮詢",
      "message_count": 5,
      "is_pinned": false,
      "is_archived": false,
      "last_message_at": "2025-10-11T08:00:00",
      "created_at": "2025-10-11T07:00:00",
      "updated_at": "2025-10-11T08:00:00"
    }
  ],
  "total": 2
}
```

***

### 2.3 取得對話詳情

取得特定對話的詳細資訊

```http
GET /conversations/{conversation_id}
Authorization: Bearer {token}
```

**回應** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "title": "水稻病蟲害防治",
  "message_count": 10,
  "is_pinned": true,
  "is_archived": false,
  "llm_config": {
    "model": "gpt-4o-mini",
    "temperature": 0.7
  },
  "last_message_at": "2025-10-11T09:00:00",
  "created_at": "2025-10-10T10:00:00",
  "updated_at": "2025-10-11T09:00:00",
  "tags": ["水稻", "病蟲害"],
  "shares": []
}
```

***

### 2.4 取得對話訊息

取得對話中的所有訊息

```http
GET /conversations/{conversation_id}/messages
Authorization: Bearer {token}
```

**查詢參數**:
- `limit` (integer) - 返回數量，預設 `50`
- `offset` (integer) - 偏移量，預設 `0`

**回應** (200 OK):
```json
{
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "水稻病蟲害如何防治？",
      "timestamp": "2025-10-11T09:00:00",
      "sources": null,
      "intent": null
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "水稻常見病蟲害包括稻熱病、紋枯病、白葉枯病等...",
      "timestamp": "2025-10-11T09:00:05",
      "sources": [
        {
          "source": "水稻病蟲害防治手冊.pdf",
          "department": "農業推廣科",
          "content": "稻熱病是水稻最常見的病害之一..."
        }
      ],
      "intent": {
        "type": "business_question",
        "use_rag": true,
        "confidence": 0.95
      }
    }
  ],
  "total": 10,
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

***

### 2.5 更新對話

更新對話的標題或其他屬性

```http
PUT /conversations/{conversation_id}
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "title": "水稻病蟲害防治進階諮詢",
  "is_pinned": true
}
```

**回應** (200 OK):
```json
{
  "message": "對話已更新",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

***

### 2.6 刪除對話

刪除指定對話

```http
DELETE /conversations/{conversation_id}
Authorization: Bearer {token}
```

**回應** (200 OK):
```json
{
  "message": "對話已刪除",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

***

### 2.7 置頂/取消置頂對話

```http
PUT /conversations/{conversation_id}/pin
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "is_pinned": true
}
```

**回應** (200 OK):
```json
{
  "message": "對話已置頂",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

***

### 2.8 封存/取消封存對話

```http
PUT /conversations/{conversation_id}/archive
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "is_archived": true
}
```

**回應** (200 OK):
```json
{
  "message": "對話已封存",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

***

## 3. 即時聊天 API

### 3.1 REST 查詢（非串流）

發送問題並取得完整回答

```http
POST /chat/query
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "question": "水稻病蟲害如何防治？",
  "k": 5,
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**參數說明**:
- `question` (string, required) - 用戶問題
- `k` (integer, optional) - RAG 檢索數量，預設 `5`，範圍 `1-20`
- `conversation_id` (string, optional) - 對話 ID，提供則啟用對話記憶

**回應** (200 OK):
```json
{
  "answer": "水稻常見病蟲害包括稻熱病、紋枯病、白葉枯病等。\n\n防治方法：\n1. 選用抗病品種\n2. 適期施用藥劑\n3. 加強田間管理...",
  "sources": [
    {
      "source": "水稻病蟲害防治手冊.pdf",
      "department": "農業推廣科",
      "content": "稻熱病是水稻最常見的病害之一，主要發生在..."
    },
    {
      "source": "水稻栽培技術指南.pdf",
      "department": "技術服務組",
      "content": "防治方法包括選用抗病品種、合理施肥..."
    }
  ],
  "context_count": 5,
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "intent": {
    "type": "business_question",
    "use_rag": true,
    "confidence": 0.95,
    "reason": "問題涉及農業技術"
  }
}
```

***

### 3.2 WebSocket 即時聊天（串流）

建立 WebSocket 連線進行即時對話

**連線 URL**:
```
ws://localhost:8000/chat/ws/{conversation_id}?token={jwt_token}
```

**範例**:
```javascript
const ws = new WebSocket(
  'ws://localhost:8000/chat/ws/550e8400-e29b-41d4-a716-446655440000?token=eyJ0eXAi...'
);

ws.onopen = () => {
  console.log('✅ 已連線');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('收到訊息:', data);
};

// 發送問題
ws.send(JSON.stringify({
  type: 'message',
  content: '水稻病蟲害如何防治？',
  k: 5
}));
```

***

#### WebSocket 訊息格式

**1. 連線成功訊息**

```json
{
  "type": "connected",
  "message": "✅ WebSocket 已連線（使用 gpt-4o-mini (OpenAI)）",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "ai_model": "gpt-4o-mini (OpenAI)"
}
```

***

**2. 意圖判斷訊息**

```json
{
  "type": "intent",
  "use_rag": true,
  "intent": "business_question",
  "confidence": 0.95,
  "reason": "問題涉及農業技術"
}
```

**intent 類型**:
- `business_question` - 業務問題（使用 RAG）
- `general_greeting` - 一般問候（不使用 RAG）
- `out_of_scope` - 超出範圍（不使用 RAG）

***

**3. 串流回答片段**

```json
{
  "type": "chunk",
  "content": "水稻",
  "chunk_index": 0
}
```

持續接收多個 chunk，逐字組合成完整回答。

***

**4. 回答完成訊息**

```json
{
  "type": "done",
  "total_chunks": 50,
  "sources": [
    {
      "source": "水稻病蟲害防治手冊.pdf",
      "department": "農業推廣科",
      "content": "稻熱病是水稻最常見的病害之一..."
    }
  ],
  "full_response": "水稻常見病蟲害包括稻熱病、紋枯病..."
}
```

***

**5. 錯誤訊息**

```json
{
  "type": "error",
  "message": "處理失敗: 連線逾時"
}
```

***

**6. 警告訊息**

```json
{
  "type": "warning",
  "message": "對話記錄儲存失敗，但不影響使用"
}
```

***

## 4. 文件管理 API

### 4.1 上傳文件

上傳新文件到系統

```http
POST /documents/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

**請求 Body** (form-data):
```
file: <binary file>
department: "農業推廣科"
job_type: "技術諮詢"
year: 2024
document_type: "manual"
```

**參數說明**:
- `file` (file, required) - 文件檔案
- `department` (string, optional) - 部門名稱
- `job_type` (string, optional) - 業務類型
- `year` (integer, optional) - 年份
- `document_type` (string, optional) - 文件類型

**支援格式**: PDF, DOCX, TXT, MD, CSV, XLSX

**回應** (200 OK):
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "filename": "水稻病蟲害防治手冊.pdf",
  "file_path": "/uploads/660e8400-e29b-41d4-a716-446655440000.pdf",
  "file_size": 1048576,
  "file_type": "pdf",
  "status": "pending",
  "metadata": {
    "department": "農業推廣科",
    "job_type": "技術諮詢",
    "year": 2024,
    "document_type": "manual"
  },
  "created_at": "2025-10-11T10:00:00"
}
```

***

### 4.2 取得文件列表

取得所有文件

```http
GET /documents/
Authorization: Bearer {token}
```

**查詢參數**:
- `status` (string) - 狀態過濾 (`pending`, `processing`, `completed`, `failed`)
- `department` (string) - 部門過濾
- `year` (integer) - 年份過濾
- `limit` (integer) - 返回數量，預設 `50`
- `offset` (integer) - 偏移量，預設 `0`

**回應** (200 OK):
```json
{
  "documents": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "filename": "水稻病蟲害防治手冊.pdf",
      "file_size": 1048576,
      "file_type": "pdf",
      "status": "completed",
      "chunk_count": 50,
      "vector_count": 50,
      "metadata": {
        "department": "農業推廣科",
        "year": 2024
      },
      "created_at": "2025-10-11T10:00:00",
      "processed_at": "2025-10-11T10:05:00"
    }
  ],
  "total": 1
}
```

**status 說明**:
- `pending` - 等待處理
- `processing` - 處理中
- `completed` - 已完成
- `failed` - 處理失敗

***

### 4.3 取得文件詳情

取得特定文件的詳細資訊

```http
GET /documents/{document_id}
Authorization: Bearer {token}
```

**回應** (200 OK):
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "filename": "水稻病蟲害防治手冊.pdf",
  "file_path": "/uploads/660e8400-e29b-41d4-a716-446655440000.pdf",
  "file_size": 1048576,
  "file_type": "pdf",
  "content_hash": "abc123def456...",
  "status": "completed",
  "error_message": null,
  "chunk_count": 50,
  "vector_count": 50,
  "embedding_model": "text-embedding-3-small",
  "metadata": {
    "department": "農業推廣科",
    "job_type": "技術諮詢",
    "year": 2024,
    "document_type": "manual"
  },
  "preview": "水稻病蟲害防治手冊\n\n第一章：稻熱病...",
  "uploaded_by": 1,
  "processed_at": "2025-10-11T10:05:00",
  "created_at": "2025-10-11T10:00:00",
  "updated_at": "2025-10-11T10:05:00"
}
```

***

### 4.4 處理文件（向量化）

手動觸發文件向量化處理

```http
POST /documents/process
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "document_ids": ["660e8400-e29b-41d4-a716-446655440000"]
}
```

**回應** (200 OK):
```json
{
  "message": "文件處理完成",
  "processed_count": 1,
  "total_chunks": 50,
  "results": [
    {
      "document_id": "660e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "chunks": 50
    }
  ]
}
```

***

### 4.5 刪除文件

刪除指定文件

```http
DELETE /documents/{document_id}
Authorization: Bearer {token}
```

**回應** (200 OK):
```json
{
  "message": "文件已刪除",
  "document_id": "660e8400-e29b-41d4-a716-446655440000"
}
```

***

### 4.6 更新文件 Metadata

更新文件的 Metadata

```http
PUT /documents/{document_id}/metadata
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "department": "農業技術科",
  "year": 2025,
  "document_type": "guide"
}
```

**回應** (200 OK):
```json
{
  "message": "Metadata 已更新",
  "document_id": "660e8400-e29b-41d4-a716-446655440000"
}
```

***

## 5. 歷史記錄 API

### 5.1 搜尋對話

在對話中搜尋關鍵字

```http
GET /conversations/search
Authorization: Bearer {token}
```

**查詢參數**:
- `q` (string, required) - 搜尋關鍵字
- `limit` (integer, optional) - 返回數量，預設 `20`

**回應** (200 OK):
```json
{
  "query": "水稻",
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "水稻病蟲害防治",
      "message_count": 10,
      "last_message_at": "2025-10-11T09:00:00",
      "created_at": "2025-10-10T10:00:00",
      "matched_content": "...水稻常見病蟲害包括..."
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "title": "水稻種植技術",
      "message_count": 5,
      "last_message_at": "2025-10-11T08:00:00",
      "created_at": "2025-10-11T07:00:00",
      "matched_content": "...水稻最佳種植時機..."
    }
  ],
  "total": 2
}
```

***

## 6. 智能功能 API

### 6.1 自動生成對話標題

根據對話內容自動生成標題

```http
POST /conversations/{conversation_id}/generate-title
Authorization: Bearer {token}
```

**回應** (200 OK):
```json
{
  "message": "標題已自動生成",
  "title": "水稻病蟲害防治諮詢",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

***

### 6.2 意圖分類測試

測試問題的意圖分類（開發/測試用）

```http
POST /chat/classify-intent
Authorization: Bearer {token}
Content-Type: application/json
```

**請求 Body**:
```json
{
  "question": "水稻病蟲害如何防治？"
}
```

**回應** (200 OK):
```json
{
  "question": "水稻病蟲害如何防治？",
  "intent": {
    "type": "business_question",
    "use_rag": true,
    "confidence": 0.95,
    "reason": "問題涉及農業技術諮詢"
  }
}
```

***

## 7. 系統 API

### 7.1 根端點

取得 API 基本資訊

```http
GET /
```

**回應** (200 OK):
```json
{
  "message": "Welcome to Farmer RAG System API",
  "version": "2.0.0",
  "status": "running",
  "docs": "/docs",
  "redoc": "/redoc",
  "test_ui": "http://localhost:8080/test.html",
  "endpoints": {
    "auth": "/auth",
    "conversations": "/conversations",
    "chat": "/chat",
    "documents": "/documents"
  },
  "features": {
    "conversation_memory": "✅ 支援多輪對話記憶",
    "intent_classification": "✅ 自動意圖判斷（使用 LLM）",
    "rag_integration": "✅ 智能文件檢索",
    "streaming_chat": "✅ WebSocket 即時串流",
    "source_citation": "✅ 文件來源引用",
    "user_management": "✅ 完整用戶認證系統"
  }
}
```

***

### 7.2 健康檢查

檢查系統各組件狀態

```http
GET /health
```

**回應** (200 OK):
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "vector_store": "healthy (vectors: 250)",
    "openai_api": "configured",
    "google_api": "configured"
  },
  "timestamp": "2025-10-11T21:30:00"
}
```

***

### 7.3 系統資訊

取得系統詳細資訊

```http
GET /system/info
```

**回應** (200 OK):
```json
{
  "system": {
    "title": "Farmer RAG System",
    "version": "2.0.0",
    "environment": "development"
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "farmer_rag"
  },
  "vector_store": {
    "type": "Chroma",
    "collection": "farmer_documents",
    "persist_directory": "./.chromadb",
    "vector_count": 250
  },
  "statistics": {
    "users": 10,
    "conversations": 50,
    "documents": 25,
    "messages": 500,
    "storage_bytes": 104857600,
    "storage_mb": 100.0
  },
  "config": {
    "max_upload_size_mb": 100,
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "embedding_model": "text-embedding-3-small",
    "gpt_model": "gpt-4o-mini"
  },
  "features": {
    "conversation_memory": true,
    "intent_classification": true,
    "rag_integration": true,
    "streaming_chat": true,
    "source_citation": true
  }
}
```

***

### 7.4 取得系統標籤

取得可用的系統標籤

```http
GET /system/tags
```

**回應** (200 OK):
```json
{
  "tags": [
    {
      "id": 1,
      "name": "水稻",
      "color": "#10B981",
      "icon": "plant",
      "usage_count": 15
    },
    {
      "id": 2,
      "name": "病蟲害",
      "color": "#EF4444",
      "icon": "bug",
      "usage_count": 12
    }
  ],
  "total": 4
}
```

***

## 📊 錯誤碼說明

| 狀態碼 | 說明 | 處理建議 |
|--------|------|---------|
| `200 OK` | 請求成功 | - |
| `201 Created` | 資源建立成功 | - |
| `400 Bad Request` | 請求參數錯誤 | 檢查請求格式 |
| `401 Unauthorized` | 未授權（Token 無效或過期） | 重新登入 |
| `403 Forbidden` | 禁止訪問（權限不足） | 檢查權限 |
| `404 Not Found` | 資源不存在 | 檢查 ID 是否正確 |
| `409 Conflict` | 資源衝突（如 Email 已存在） | 使用不同的資料 |
| `422 Unprocessable Entity` | 驗證錯誤 | 檢查必填欄位 |
| `500 Internal Server Error` | 伺服器錯誤 | 聯繫管理員 |

**錯誤回應格式**:
```json
{
  "detail": "錯誤訊息",
  "message": "詳細說明"
}
```

***

## 🔗 相關連結

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **測試頁面**: http://localhost:8080/test.html
- **GitHub**: [專案連結]

***

## 💡 使用範例

### Python 範例

```python
import requests

# 登入
response = requests.post('http://localhost:8000/auth/login', json={
    'email': 'farmer@example.com',
    'password': 'SecurePass123'
})
token = response.json()['access_token']

# 使用 Token 建立對話
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('http://localhost:8000/conversations/', 
    headers=headers,
    json={'title': '新對話'}
)
conversation = response.json()

# 發送問題
response = requests.post('http://localhost:8000/chat/query', 
    headers=headers,
    json={
        'question': '水稻病蟲害如何防治？',
        'k': 5,
        'conversation_id': conversation['id']
    }
)
print(response.json()['answer'])
```

### JavaScript/TypeScript 範例

```typescript
// 登入
const loginResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'farmer@example.com',
    password: 'SecurePass123'
  })
});
const { access_token } = await loginResponse.json();

// WebSocket 連線
const ws = new WebSocket(
  `ws://localhost:8000/chat/ws/${conversationId}?token=${access_token}`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'chunk':
      console.log(data.content);
      break;
    case 'done':
      console.log('完成！來源:', data.sources);
      break;
  }
};

// 發送問題
ws.send(JSON.stringify({
  type: 'message',
  content: '水稻病蟲害如何防治？',
  k: 5
}));
```

***


涵蓋了所有核心功能：
- ✅ 認證（註冊、登入、登出、Token 管理）
- ✅ 對話管理（建立、列表、更新、刪除、置頂、封存）
- ✅ 即時聊天（REST 查詢、WebSocket 串流）
- ✅ 文件管理（上傳、列表、詳情、向量化、刪除）
- ✅ 歷史記錄（搜尋、分組）
- ✅ 智能功能（自動標題、意圖判斷）
- ✅ 系統資訊（健康檢查、統計資訊）

