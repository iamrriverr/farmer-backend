CREATE TABLE chat_history (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL, --對話 ID。邏輯上對應 conversations.id。雖然您使用了 TEXT 而非 UUID 類型，這通常是為了配合 LangChain 的 PostgresChatMessageHistory 介面，它預設使用 TEXT 來表示 Session ID
    message JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_chat_history_session ON chat_history(session_id, created_at);  --核心查詢索引。用於快速檢索特定對話 (session_id) 的所有訊息，並按時間順序 (created_at) 排序，這是載入聊天畫面所必需的。
CREATE INDEX idx_chat_history_message_gin ON chat_history USING GIN (message); --內容搜索加速。GIN (Generalized Inverted Index) 索引專門用於加速對 JSONB 欄位內部鍵值的查詢。例如，您可以使用這個索引快速搜索特定訊息內容或帶有特定 RAG 來源 ID 的所有訊息。

-- 自動更新對話的 message_count 和 last_message_at
CREATE OR REPLACE FUNCTION update_conversation_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET message_count = message_count + 1,
        last_message_at = NEW.created_at,
        updated_at = NOW()
    WHERE id::text = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_conversation_stats_trigger
    AFTER INSERT ON chat_history
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_stats();
