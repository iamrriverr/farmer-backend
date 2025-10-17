CREATE TABLE conversation_tags (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (conversation_id, tag_id)
);

-- 索引
CREATE INDEX idx_conversation_tags_tag_id ON conversation_tags(tag_id);
CREATE INDEX idx_conversation_tags_conversation_id ON conversation_tags(conversation_id);

-- 自動更新標籤使用次數
CREATE OR REPLACE FUNCTION update_tag_usage_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE tags SET usage_count = GREATEST(usage_count - 1, 0) WHERE id = OLD.tag_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tag_usage_count_trigger
    AFTER INSERT OR DELETE ON conversation_tags
    FOR EACH ROW
    EXECUTE FUNCTION update_tag_usage_count();
