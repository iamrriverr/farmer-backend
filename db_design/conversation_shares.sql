CREATE TABLE conversation_shares (
    id SERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    shared_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    shared_with INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_level VARCHAR(20) NOT NULL CHECK (permission_level IN ('view', 'comment', 'edit')),
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(conversation_id, shared_with),
    CHECK (shared_by != shared_with)
);

-- 索引
CREATE INDEX idx_conversation_shares_shared_with ON conversation_shares(shared_with, is_active);
CREATE INDEX idx_conversation_shares_conversation ON conversation_shares(conversation_id);

-- 更新時間觸發器
CREATE TRIGGER update_conversation_shares_updated_at
    BEFORE UPDATE ON conversation_shares
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
