CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7) DEFAULT '#3B82F6',
    icon VARCHAR(50),
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- 系統標籤的唯一約束（user_id 為 NULL）
CREATE UNIQUE INDEX idx_tags_system_name ON tags(name) WHERE user_id IS NULL;

-- 索引
CREATE INDEX idx_tags_user_id ON tags(user_id, name);
CREATE INDEX idx_tags_usage_count ON tags(usage_count DESC);
