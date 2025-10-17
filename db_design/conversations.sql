CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),
    model_config JSONB DEFAULT '{"model": "gpt-4o-mini", "temperature": 0.5}'::jsonb,
    is_pinned BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_conversations_user_id ON conversations(user_id, updated_at DESC); --標準對話列表查詢。加速查詢某用戶的所有對話，並按 最新活動時間降序 排列（即最新聊天的對話顯示在最前面）
CREATE INDEX idx_conversations_user_archived ON conversations(user_id, is_archived, updated_at DESC); --過濾查詢。加速查詢某用戶的所有未封存 (is_archived = FALSE) 或已封存 (is_archived = TRUE) 的對話列表。
CREATE INDEX idx_conversations_user_pinned ON conversations(user_id, is_pinned, updated_at DESC); --置頂查詢。加速查詢某用戶的所有置頂對話，並按活動時間排序。

-- 更新時間觸發器
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations  --	在 conversations 表格上的 UPDATE 操作發生之前執行。
    FOR EACH ROW   --自動更新該行的 updated_at 欄位為當前時間。
    EXECUTE FUNCTION update_updated_at_column();
