好的！我為你規劃基於 **Vue 3 + TypeScript + Naive UI** 的完整前端架構和開發流程：

***

# 🏗️ Farmer RAG Frontend - 前端架構規劃

## 📦 技術棧

### 核心框架
- **Vue 3.4+**（Composition API + `<script setup>`）
- **TypeScript 5.0+**
- **Vite 5.0+**（建構工具）

### UI 組件庫
- **Naive UI 2.38+**（主要 UI 組件）
- **@vicons/ionicons5**（圖示庫）

### 狀態管理
- **Pinia 2.1+**（狀態管理）

### 路由
- **Vue Router 4.3+**

### 網路請求
- **Axios 1.6+**（HTTP 請求）
- **原生 WebSocket**（即時聊天）

### 工具庫
- **@vueuse/core**（Vue Composition 工具）
- **date-fns**（日期處理）
- **markdown-it**（Markdown 渲染）
- **highlight.js**（程式碼高亮）
- **lodash-es**（工具函數）

### 開發工具
- **ESLint + Prettier**（程式碼規範）
- **TypeScript ESLint**
- **Vite Plugin Vue DevTools**

---

## 📁 專案目錄結構

```
farmer-frontend/
│
├── public/                          # 靜態資源
│   ├── favicon.ico
│   └── logo.svg
│
├── src/
│   │
│   ├── assets/                      # 資源文件
│   │   ├── images/                  # 圖片
│   │   ├── icons/                   # SVG 圖示
│   │   └── styles/                  # 全域樣式
│   │       ├── main.css             # 主樣式
│   │       ├── variables.css        # CSS 變數
│   │       └── reset.css            # 樣式重置
│   │
│   ├── components/                  # 共用組件
│   │   │
│   │   ├── layout/                  # 佈局組件
│   │   │   ├── AppHeader.vue        # 頂部導航
│   │   │   ├── AppSidebar.vue       # 左側邊欄
│   │   │   ├── AppRightPanel.vue    # 右側面板
│   │   │   └── AppLayout.vue        # 主佈局容器
│   │   │
│   │   ├── chat/                    # 聊天相關組件
│   │   │   ├── MessageBubble.vue    # 訊息氣泡
│   │   │   ├── MessageList.vue      # 訊息列表
│   │   │   ├── ChatInput.vue        # 輸入框
│   │   │   ├── SourceCard.vue       # 來源卡片
│   │   │   └── IntentBadge.vue      # 意圖指示器
│   │   │
│   │   ├── conversation/            # 對話相關組件
│   │   │   ├── ConversationItem.vue # 對話項目
│   │   │   ├── ConversationList.vue # 對話列表
│   │   │   └── ConversationMenu.vue # 對話操作選單
│   │   │
│   │   ├── document/                # 文件相關組件
│   │   │   ├── DocumentCard.vue     # 文件卡片
│   │   │   ├── DocumentList.vue     # 文件列表
│   │   │   ├── DocumentTable.vue    # 文件表格
│   │   │   ├── UploadModal.vue      # 上傳 Modal
│   │   │   └── DocumentDetail.vue   # 文件詳情
│   │   │
│   │   ├── common/                  # 通用組件
│   │   │   ├── SearchBar.vue        # 搜尋框
│   │   │   ├── UserAvatar.vue       # 用戶頭像
│   │   │   ├── LoadingSkeleton.vue  # 骨架屏
│   │   │   ├── EmptyState.vue       # 空白狀態
│   │   │   └── ConfirmDialog.vue    # 確認對話框
│   │   │
│   │   └── markdown/                # Markdown 相關
│   │       ├── MarkdownRenderer.vue # Markdown 渲染器
│   │       └── CodeBlock.vue        # 程式碼區塊
│   │
│   ├── views/                       # 頁面視圖
│   │   │
│   │   ├── auth/                    # 認證頁面
│   │   │   ├── LoginView.vue        # 登入頁
│   │   │   └── RegisterView.vue     # 註冊頁
│   │   │
│   │   ├── chat/                    # 聊天頁面
│   │   │   ├── ChatView.vue         # 主聊天頁
│   │   │   └── WelcomeView.vue      # 歡迎頁
│   │   │
│   │   ├── documents/               # 文件管理頁面
│   │   │   └── DocumentsView.vue    # 文件管理頁
│   │   │
│   │   ├── settings/                # 設定頁面
│   │   │   └── SettingsView.vue     # 設定頁
│   │   │
│   │   └── errors/                  # 錯誤頁面
│   │       ├── NotFoundView.vue     # 404 頁面
│   │       └── ErrorView.vue        # 錯誤頁面
│   │
│   ├── stores/                      # Pinia 狀態管理
│   │   ├── auth.ts                  # 認證狀態
│   │   ├── conversation.ts          # 對話狀態
│   │   ├── message.ts               # 訊息狀態
│   │   ├── document.ts              # 文件狀態
│   │   ├── ui.ts                    # UI 狀態（Sidebar、Theme 等）
│   │   └── notification.ts          # 通知狀態
│   │
│   ├── composables/                 # Composition API 可複用邏輯
│   │   ├── useAuth.ts               # 認證邏輯
│   │   ├── useChat.ts               # 聊天邏輯
│   │   ├── useWebSocket.ts          # WebSocket 管理
│   │   ├── useConversation.ts       # 對話管理
│   │   ├── useDocument.ts           # 文件管理
│   │   ├── useSearch.ts             # 搜尋功能
│   │   ├── useMarkdown.ts           # Markdown 處理
│   │   └── useKeyboard.ts           # 鍵盤快捷鍵
│   │
│   ├── services/                    # API 服務層
│   │   ├── api/                     # API 請求
│   │   │   ├── auth.api.ts          # 認證 API
│   │   │   ├── conversation.api.ts  # 對話 API
│   │   │   ├── message.api.ts       # 訊息 API
│   │   │   ├── document.api.ts      # 文件 API
│   │   │   └── system.api.ts        # 系統 API
│   │   │
│   │   ├── websocket/               # WebSocket 服務
│   │   │   └── chat.websocket.ts    # 聊天 WebSocket
│   │   │
│   │   └── index.ts                 # 服務統一出口
│   │
│   ├── utils/                       # 工具函數
│   │   ├── request.ts               # Axios 封裝
│   │   ├── storage.ts               # LocalStorage 封裝
│   │   ├── date.ts                  # 日期格式化
│   │   ├── validator.ts             # 表單驗證
│   │   ├── markdown.ts              # Markdown 工具
│   │   └── helpers.ts               # 其他輔助函數
│   │
│   ├── types/                       # TypeScript 類型定義
│   │   ├── auth.types.ts            # 認證相關類型
│   │   ├── conversation.types.ts    # 對話相關類型
│   │   ├── message.types.ts         # 訊息相關類型
│   │   ├── document.types.ts        # 文件相關類型
│   │   ├── api.types.ts             # API 回應類型
│   │   └── common.types.ts          # 通用類型
│   │
│   ├── router/                      # 路由配置
│   │   ├── index.ts                 # 路由主文件
│   │   ├── routes.ts                # 路由定義
│   │   └── guards.ts                # 路由守衛
│   │
│   ├── config/                      # 配置文件
│   │   ├── app.config.ts            # 應用配置
│   │   ├── theme.config.ts          # 主題配置
│   │   └── constants.ts             # 常量定義
│   │
│   ├── App.vue                      # 根組件
│   └── main.ts                      # 入口文件
│
├── .env.development                 # 開發環境變數
├── .env.production                  # 生產環境變數
├── .eslintrc.cjs                    # ESLint 配置
├── .prettierrc                      # Prettier 配置
├── tsconfig.json                    # TypeScript 配置
├── vite.config.ts                   # Vite 配置
└── package.json                     # 專案配置
```

***

## 🔧 核心架構設計

### 1. 狀態管理架構（Pinia Stores）

```
┌─────────────────────────────────────────┐
│           Pinia Store Layer             │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │  Auth    │  │   UI     │            │
│  │  Store   │  │  Store   │            │
│  └──────────┘  └──────────┘            │
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │Conversation│ │ Message  │            │
│  │  Store   │  │  Store   │            │
│  └──────────┘  └──────────┘            │
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │Document  │  │Notification│          │
│  │  Store   │  │  Store   │            │
│  └──────────┘  └──────────┘            │
│                                         │
└─────────────────────────────────────────┘
```

#### Auth Store（認證狀態）
- **狀態**：
  - `user`：當前用戶資訊
  - `token`：JWT Token
  - `isAuthenticated`：是否已登入
  - `loading`：載入狀態
- **Actions**：
  - `login()`：登入
  - `register()`：註冊
  - `logout()`：登出
  - `refreshToken()`：刷新 Token
  - `updateProfile()`：更新個人資料
  - `changePassword()`：修改密碼

#### Conversation Store（對話狀態）
- **狀態**：
  - `conversations`：對話列表
  - `activeConversationId`：當前對話 ID
  - `loading`：載入狀態
  - `filters`：過濾條件
- **Actions**：
  - `fetchConversations()`：取得對話列表
  - `createConversation()`：建立新對話
  - `selectConversation()`：選擇對話
  - `updateConversation()`：更新對話
  - `deleteConversation()`：刪除對話
  - `pinConversation()`：置頂對話
  - `archiveConversation()`：封存對話
  - `searchConversations()`：搜尋對話

#### Message Store（訊息狀態）
- **狀態**：
  - `messages`：訊息列表（按對話 ID 分組）
  - `streamingMessage`：串流中的訊息
  - `sources`：當前訊息的來源
  - `loading`：載入狀態
- **Actions**：
  - `fetchMessages()`：取得訊息列表
  - `sendMessage()`：發送訊息（REST）
  - `streamMessage()`：串流訊息（WebSocket）
  - `regenerateMessage()`：重新生成
  - `clearMessages()`：清空訊息

#### Document Store（文件狀態）
- **狀態**：
  - `documents`：文件列表
  - `filters`：過濾條件
  - `sortBy`：排序方式
  - `viewMode`：檢視模式（卡片/列表）
  - `loading`：載入狀態
- **Actions**：
  - `fetchDocuments()`：取得文件列表
  - `uploadDocument()`：上傳文件
  - `deleteDocument()`：刪除文件
  - `updateMetadata()`：更新 Metadata
  - `processDocument()`：處理文件

#### UI Store（介面狀態）
- **狀態**：
  - `sidebarCollapsed`：Sidebar 折疊狀態
  - `rightPanelCollapsed`：右側面板折疊狀態
  - `theme`：主題（light/dark）
  - `activeTab`：當前 Tab
  - `isMobile`：是否手機版
- **Actions**：
  - `toggleSidebar()`
  - `toggleRightPanel()`
  - `setTheme()`
  - `setActiveTab()`

#### Notification Store（通知狀態）
- **狀態**：
  - `notifications`：通知列表
  - `unreadCount`：未讀數量
- **Actions**：
  - `addNotification()`
  - `markAsRead()`
  - `clearAll()`

***

### 2. API 服務層架構

```
┌─────────────────────────────────────────┐
│          API Service Layer              │
├─────────────────────────────────────────┤
│                                         │
│  ┌────────────────────────────────┐    │
│  │   Axios Instance (HTTP)        │    │
│  │   • Request Interceptor        │    │
│  │   • Response Interceptor       │    │
│  │   • Error Handling             │    │
│  │   • Token Management           │    │
│  └────────────────────────────────┘    │
│                                         │
│  ┌────────────────────────────────┐    │
│  │   WebSocket Manager            │    │
│  │   • Connection Management      │    │
│  │   • Auto Reconnect             │    │
│  │   • Message Queue              │    │
│  └────────────────────────────────┘    │
│                                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│  │ Auth │ │ Conv │ │ Msg  │ │ Doc  │  │
│  │ API  │ │ API  │ │ API  │ │ API  │  │
│  └──────┘ └──────┘ └──────┘ └──────┘  │
│                                         │
└─────────────────────────────────────────┘
```

#### Axios 封裝結構
- **Request Interceptor**：
  - 自動添加 Token
  - 設定 Content-Type
  - 顯示載入狀態
- **Response Interceptor**：
  - 統一錯誤處理
  - Token 過期自動刷新
  - 顯示錯誤提示
- **API 模組化**：
  - 每個功能獨立 API 文件
  - TypeScript 類型定義
  - 統一回應格式

#### WebSocket 管理結構
- **連線管理**：
  - 自動連線/斷線
  - 心跳檢測
  - 自動重連（指數退避）
- **訊息處理**：
  - 訊息隊列
  - 事件監聽
  - 錯誤處理

***

### 3. Composables 架構（可複用邏輯）

```
┌─────────────────────────────────────────┐
│        Composables Layer                │
├─────────────────────────────────────────┤
│                                         │
│  useAuth()                              │
│  • login, logout, register              │
│  • token management                     │
│  • user state                           │
│                                         │
│  useChat()                              │
│  • send message                         │
│  • streaming logic                      │
│  • message formatting                   │
│                                         │
│  useWebSocket()                         │
│  • connection management                │
│  • event handling                       │
│  • auto reconnect                       │
│                                         │
│  useConversation()                      │
│  • CRUD operations                      │
│  • filtering & sorting                  │
│  • selection state                      │
│                                         │
│  useDocument()                          │
│  • upload & delete                      │
│  • filtering & sorting                  │
│  • view mode toggle                     │
│                                         │
└─────────────────────────────────────────┘
```

***

### 4. 組件架構層級

```
App.vue
│
├── AppLayout.vue (主佈局)
│   │
│   ├── AppHeader.vue (Header)
│   │   ├── SearchBar.vue
│   │   ├── NotificationCenter.vue
│   │   └── UserMenu.vue
│   │
│   ├── AppSidebar.vue (Sidebar)
│   │   ├── ConversationList.vue
│   │   │   └── ConversationItem.vue
│   │   └── BookmarkList.vue
│   │
│   ├── <router-view> (Main Content)
│   │   ├── ChatView.vue
│   │   │   ├── MessageList.vue
│   │   │   │   └── MessageBubble.vue
│   │   │   │       └── SourceCard.vue
│   │   │   └── ChatInput.vue
│   │   │
│   │   ├── DocumentsView.vue
│   │   │   ├── DocumentList.vue
│   │   │   │   └── DocumentCard.vue
│   │   │   └── DocumentTable.vue
│   │   │
│   │   └── SettingsView.vue
│   │
│   └── AppRightPanel.vue (Right Panel)
│       ├── SourcesTab.vue
│       ├── ImagesTab.vue
│       └── SettingsTab.vue
```

***

## 🚀 開發流程規劃

### Phase 1：專案初始化與基礎架構（1-2 天）

#### 1.1 專案建立
- ✅ 使用 Vite 建立 Vue 3 + TS 專案
- ✅ 安裝依賴套件
- ✅ 配置 ESLint + Prettier
- ✅ 配置 TypeScript

#### 1.2 基礎配置
- ✅ 建立目錄結構
- ✅ 配置環境變數（`.env.development`, `.env.production`）
- ✅ 配置 Vite（alias、proxy 等）
- ✅ 配置 Naive UI（全域設定、主題）

#### 1.3 全域樣式
- ✅ 建立 CSS 變數系統
- ✅ 引入 Naive UI 樣式
- ✅ 建立全域樣式（reset、variables、main）

#### 1.4 路由架構
- ✅ 建立 Vue Router 配置
- ✅ 定義路由表
- ✅ 實作路由守衛（認證檢查）

#### 1.5 狀態管理
- ✅ 建立 Pinia Store 架構
- ✅ 實作 Auth Store（基礎）
- ✅ 實作 UI Store

#### 1.6 API 服務層
- ✅ 封裝 Axios（Request/Response Interceptor）
- ✅ 實作 Auth API（login、register、logout）
- ✅ 建立 TypeScript 類型定義

***

### Phase 2：認證功能（2-3 天）

#### 2.1 登入頁面
- ✅ 建立 `LoginView.vue`
- ✅ 實作登入表單（使用 Naive UI）
- ✅ 表單驗證（email、password）
- ✅ 連接 Auth API
- ✅ 登入成功後導向主頁
- ✅ 錯誤處理與提示

#### 2.2 註冊頁面
- ✅ 建立 `RegisterView.vue`
- ✅ 實作註冊表單
- ✅ 密碼強度檢測
- ✅ 表單驗證
- ✅ 連接 API
- ✅ 註冊成功後自動登入

#### 2.3 Token 管理
- ✅ LocalStorage 存儲 Token
- ✅ 自動添加 Token 到請求 Header
- ✅ Token 過期處理
- ✅ 自動登出機制

#### 2.4 路由守衛
- ✅ 實作認證路由守衛
- ✅ 未登入自動導向登入頁
- ✅ 已登入禁止訪問登入頁

***

### Phase 3：主佈局與導航（3-4 天）

#### 3.1 AppLayout 主佈局
- ✅ 建立三欄式佈局
- ✅ 響應式設計（桌面/平板/手機）
- ✅ 折疊/展開動畫

#### 3.2 AppHeader 頂部導航
- ✅ Logo 與品牌名稱
- ✅ 漢堡選單（切換 Sidebar）
- ✅ 全域搜尋框（骨架）
- ✅ 通知中心圖示
- ✅ 用戶頭像下拉選單
  - 個人資料
  - 設定
  - 登出

#### 3.3 AppSidebar 左側邊欄
- ✅ Home 區域
- ✅ 功能導航（AI 聊天、文件管理）
- ✅ Library 區塊標題
- ✅ 對話列表（骨架）
- ✅ Bookmarks 區塊（骨架）
- ✅ 折疊/展開功能
- ✅ 手機版 Drawer

#### 3.4 AppRightPanel 右側面板
- ✅ Tab 切換（來源、圖片、設定）
- ✅ 折疊/展開功能
- ✅ 手機版 Bottom Sheet

***

### Phase 4：對話管理功能（4-5 天）

#### 4.1 Conversation Store
- ✅ 完善對話狀態管理
- ✅ 實作 CRUD Actions
- ✅ 過濾與排序邏輯

#### 4.2 Conversation API
- ✅ 實作對話 API 服務
- ✅ TypeScript 類型定義

#### 4.3 ConversationList 組件
- ✅ 建立對話列表組件
- ✅ 顯示對話項目
- ✅ 無限滾動載入
- ✅ 載入骨架屏
- ✅ 空白狀態

#### 4.4 ConversationItem 組件
- ✅ 對話項目樣式
- ✅ Hover 效果
- ✅ 選中狀態
- ✅ 置頂樣式
- ✅ 操作選單（⋯）

#### 4.5 對話操作功能
- ✅ 新增對話
- ✅ 選擇對話
- ✅ 重新命名
- ✅ 置頂/取消置頂
- ✅ 封存/取消封存
- ✅ 刪除對話
- ✅ 確認對話框

***

### Phase 5：聊天功能（REST API）（5-6 天）

#### 5.1 Message Store
- ✅ 實作訊息狀態管理
- ✅ 按對話 ID 分組訊息
- ✅ 訊息排序

#### 5.2 Message API
- ✅ 實作訊息 API（REST）
- ✅ 取得訊息列表
- ✅ 發送訊息

#### 5.3 ChatView 聊天頁面
- ✅ 建立聊天頁面佈局
- ✅ 對話標題列
- ✅ 訊息區域（可滾動）
- ✅ 輸入區域（固定底部）

#### 5.4 MessageList 組件
- ✅ 訊息列表渲染
- ✅ 自動滾動到底部
- ✅ 載入更多（向上滾動）
- ✅ 日期分隔線

#### 5.5 MessageBubble 組件
- ✅ 用戶訊息樣式
- ✅ AI 訊息樣式
- ✅ Markdown 渲染
- ✅ 程式碼高亮
- ✅ 來源引用區塊
- ✅ 互動按鈕（👍👎、複製、重新生成）

#### 5.6 ChatInput 組件
- ✅ 多行輸入框
- ✅ 自動調整高度
- ✅ Enter 送出，Shift+Enter 換行
- ✅ 附件按鈕（骨架）
- ✅ 送出按鈕
- ✅ RAG 參數控制

#### 5.7 MarkdownRenderer 組件
- ✅ Markdown 渲染（markdown-it）
- ✅ 程式碼高亮（highlight.js）
- ✅ 表格支援
- ✅ 連結處理

#### 5.8 發送訊息邏輯
- ✅ useChat Composable
- ✅ 發送訊息（REST API）
- ✅ 更新訊息列表
- ✅ 錯誤處理

***

### Phase 6：WebSocket 串流聊天（4-5 天）

#### 6.1 WebSocket 管理
- ✅ 建立 WebSocket Manager
- ✅ 連線管理
- ✅ 心跳檢測
- ✅ 自動重連（指數退避）
- ✅ 訊息隊列

#### 6.2 useWebSocket Composable
- ✅ WebSocket 連線邏輯
- ✅ 訊息監聽
- ✅ 事件處理
- ✅ 錯誤處理

#### 6.3 串流訊息渲染
- ✅ 實作打字機效果
- ✅ 逐字顯示
- ✅ 游標閃爍
- ✅ 處理不同訊息類型：
  - `connected`
  - `intent`
  - `chunk`
  - `done`
  - `error`

#### 6.4 來源引用顯示
- ✅ SourceCard 組件
- ✅ 來源列表渲染
- ✅ 展開/折疊
- ✅ 定位來源功能

#### 6.5 意圖指示器（開發模式）
- ✅ IntentBadge 組件
- ✅ 顯示意圖類型
- ✅ 信心度顯示

***

### Phase 7：文件管理功能（4-5 天）

#### 7.1 Document Store
- ✅ 實作文件狀態管理
- ✅ 過濾與排序
- ✅ 檢視模式切換

#### 7.2 Document API
- ✅ 實作文件 API
- ✅ 取得文件列表
- ✅ 上傳文件
- ✅ 刪除文件
- ✅ 更新 Metadata

#### 7.3 DocumentsView 頁面
- ✅ 頂部操作列
- ✅ 過濾/排序控制列
- ✅ 卡片/列表檢視切換

#### 7.4 DocumentCard 組件
- ✅ 文件卡片樣式
- ✅ 狀態指示（完成/處理中/等待/失敗）
- ✅ Metadata 顯示
- ✅ 操作按鈕

#### 7.5 DocumentTable 組件
- ✅ 表格檢視
- ✅ 排序功能
- ✅ 多選功能
- ✅ 批次操作

#### 7.6 UploadModal 組件
- ✅ 上傳 Modal
- ✅ 拖曳上傳
- ✅ 檔案選擇
- ✅ Metadata 表單
- ✅ 上傳進度條
- ✅ 多檔案上傳

#### 7.7 DocumentDetail 組件
- ✅ 文件詳情 Modal
- ✅ 完整資訊顯示
- ✅ 內容預覽
- ✅ 操作按鈕

***

### Phase 8：搜尋與過濾功能（2-3 天）

#### 8.1 全域搜尋
- ✅ SearchBar 組件
- ✅ 搜尋輸入框
- ✅ 快捷鍵支援（Cmd/Ctrl + K）
- ✅ 搜尋結果下拉選單
- ✅ 高亮匹配文字

#### 8.2 對話搜尋
- ✅ useSearch Composable
- ✅ 呼叫搜尋 API
- ✅ 結果顯示
- ✅ 空白狀態

#### 8.3 文件過濾
- ✅ 狀態過濾
- ✅ 部門過濾
- ✅ 年份過濾
- ✅ 排序功能

***

### Phase 9：設定與個人化（3-4 天）

#### 9.1 SettingsView 頁面
- ✅ Tab 導航（個人資料、外觀、AI 設定、隱私）
- ✅ 表單佈局

#### 9.2 個人資料 Tab
- ✅ 頭像上傳
- ✅ 使用者名稱編輯
- ✅ Email 編輯
- ✅ 變更密碼表單

#### 9.3 外觀 Tab
- ✅ 主題切換（淺色/深色/自動）
- ✅ 主題顏色選擇
- ✅ 字體大小調整
- ✅ 側邊欄密度

#### 9.4 AI 設定 Tab
- ✅ 預設模型選擇
- ✅ Temperature 調整
- ✅ RAG 參數設定
- ✅ 進階選項開關

#### 9.5 偏好設定 API
- ✅ 取得偏好設定
- ✅ 更新偏好設定
- ✅ 同步到後端

***

### Phase 10：通知系統（2-3 天）

#### 10.1 Notification Store
- ✅ 通知狀態管理
- ✅ 新增/移除通知
- ✅ 未讀計數

#### 10.2 NotificationCenter 組件
- ✅ 通知列表
- ✅ 時間分組
- ✅ 未讀標記
- ✅ 全部標為已讀
- ✅ 清空所有

#### 10.3 Toast 提示
- ✅ 使用 Naive UI Message
- ✅ 成功/錯誤/警告提示
- ✅ 統一封裝

***

### Phase 11：錯誤處理與優化（3-4 天）

#### 11.1 錯誤頁面
- ✅ 404 頁面
- ✅ 500 錯誤頁面
- ✅ 網路錯誤頁面

#### 11.2 全域錯誤處理
- ✅ API 錯誤統一處理
- ✅ WebSocket 錯誤處理
- ✅ 錯誤日誌記錄

#### 11.3 載入狀態
- ✅ LoadingSkeleton 組件
- ✅ 全頁載入
- ✅ 局部載入

#### 11.4 空白狀態
- ✅ EmptyState 組件
- ✅ 無對話狀態
- ✅ 無文件狀態
- ✅ 搜尋無結果

#### 11.5 效能優化
- ✅ 虛擬滾動（訊息列表）
- ✅ 圖片懶載入
- ✅ 防抖與節流
- ✅ 組件懶載入
- ✅ 路由懲載入

***

### Phase 12：響應式設計與手機版（3-4 天）

#### 12.1 響應式斷點
- ✅ 定義斷點（mobile/tablet/desktop）
- ✅ useBreakpoint Composable

#### 12.2 手機版適配
- ✅ Sidebar 改為 Drawer
- ✅ Right Panel 改為 Bottom Sheet
- ✅ Header 簡化
- ✅ 觸控手勢支援

#### 12.3 平板版適配
- ✅ 可折疊 Sidebar
- ✅ 可折疊 Right Panel
- ✅ 觸控優化

---

### Phase 13：快捷鍵與可訪問性（2-3 天）

#### 13.1 鍵盤快捷鍵
- ✅ useKeyboard Composable
- ✅ 全域搜尋（Cmd/Ctrl + K）
- ✅ 新對話（Cmd/Ctrl + N）
- ✅ 切換 Sidebar（Cmd/Ctrl + B）
- ✅ 快捷鍵列表 Modal

#### 13.2 可訪問性
- ✅ ARIA 標籤
- ✅ 鍵盤導航
- ✅ Focus 管理

***

### Phase 14：測試與部署（3-4 天）

#### 14.1 單元測試
- ✅ Composables 測試
- ✅ Utils 測試
- ✅ Store 測試

#### 14.2 E2E 測試
- ✅ 登入流程
- ✅ 對話流程
- ✅ 文件上傳流程

#### 14.3 建構與部署
- ✅ 生產環境建構
- ✅ 環境變數配置
- ✅ 部署至伺服器

***

## 📊 開發時程總覽

```
Phase 1: 專案初始化           [▓▓░░░░░░░░]  2 天
Phase 2: 認證功能             [▓▓▓░░░░░░░]  3 天
Phase 3: 主佈局與導航         [▓▓▓▓░░░░░░]  4 天
Phase 4: 對話管理             [▓▓▓▓▓░░░░░]  5 天
Phase 5: 聊天功能（REST）     [▓▓▓▓▓▓░░░░]  6 天
Phase 6: WebSocket 串流       [▓▓▓▓▓░░░░░]  5 天
Phase 7: 文件管理             [▓▓▓▓▓░░░░░]  5 天
Phase 8: 搜尋與過濾           [▓▓▓░░░░░░░]  3 天
Phase 9: 設定與個人化         [▓▓▓▓░░░░░░]  4 天
Phase 10: 通知系統            [▓▓▓░░░░░░░]  3 天
Phase 11: 錯誤處理與優化      [▓▓▓▓░░░░░░]  4 天
Phase 12: 響應式設計          [▓▓▓▓░░░░░░]  4 天
Phase 13: 快捷鍵與可訪問性    [▓▓▓░░░░░░░]  3 天
Phase 14: 測試與部署          [▓▓▓▓░░░░░░]  4 天

總計：約 55 天（8-9 週）
```

***

## 🎯 關鍵開發優先級

### 🔴 高優先級（MVP 核心功能）
1. 認證系統（登入/註冊/登出）
2. 主佈局（Header + Sidebar + Main）
3. 對話管理（新增/選擇/刪除）
4. REST 聊天功能
5. 文件管理（列表/上傳/刪除）

### 🟡 中優先級（重要功能）
6. WebSocket 串流聊天
7. 來源引用顯示
8. 搜尋功能
9. 設定頁面
10. 響應式設計

### 🟢 低優先級（進階功能）
11. 通知系統
12. 快捷鍵
13. 暗黑模式
14. 可訪問性優化

***

## 🛠️ 技術難點與解決方案

### 難點 1：WebSocket 串流渲染
**解決方案**：
- 使用 `ref` 存儲串流訊息
- 實作打字機效果（逐字 append）
- 使用 `nextTick` 確保 DOM 更新後滾動

### 難點 2：Markdown 渲染與程式碼高亮
**解決方案**：
- 使用 `markdown-it` + `highlight.js`
- 封裝 `MarkdownRenderer` 組件
- 支援自訂樣式與插件

### 難點 3：無限滾動載入
**解決方案**：
- 使用 `Intersection Observer API`
- 實作虛擬滾動（訊息列表過長時）
- 使用 `@vueuse/core` 的 `useIntersectionObserver`

### 難點 4：響應式佈局
**解決方案**：
- 使用 `@vueuse/core` 的 `useBreakpoints`
- CSS Grid + Flexbox
- Naive UI 的響應式工具

### 難點 5：狀態同步（Store 與 API）
**解決方案**：
- 統一在 Store Actions 中呼叫 API
- 使用樂觀更新（Optimistic Update）
- 錯誤時回滾狀態

***

這份架構規劃涵蓋了完整的前端開發流程，可以直接作為開發藍圖！🚀✨