CREATE TABLE conversation_snapshots (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    snapshot_data JSONB NOT NULL,
    snapshot_version INTEGER DEFAULT 1,
    message_count INTEGER,
    total_tokens INTEGER,
    snapshot_type VARCHAR(20) NOT NULL CHECK (snapshot_type IN ('auto', 'manual', 'pre_delete')),
    created_by INTEGER REFERENCES users(id),
    retention_days INTEGER DEFAULT 90,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_conversation_snapshots_conversation ON conversation_snapshots(conversation_id, created_at DESC);
CREATE INDEX idx_conversation_snapshots_expires_at ON conversation_snapshots(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_conversation_snapshots_data_gin ON conversation_snapshots USING GIN (snapshot_data);

-- 自動設定過期時間
CREATE OR REPLACE FUNCTION set_snapshot_expires_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.expires_at IS NULL THEN
        NEW.expires_at = NEW.created_at + (NEW.retention_days || ' days')::INTERVAL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_snapshot_expires_at_trigger
    BEFORE INSERT ON conversation_snapshots
    FOR EACH ROW
    EXECUTE FUNCTION set_snapshot_expires_at();
