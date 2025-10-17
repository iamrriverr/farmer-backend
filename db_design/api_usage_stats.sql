CREATE TABLE api_usage_stats (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 1,
    token_input INTEGER DEFAULT 0,
    token_output INTEGER DEFAULT 0,
    token_total INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6) DEFAULT 0,
    window_start TIMESTAMP NOT NULL,
    window_duration INTERVAL NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, endpoint, window_start, window_duration)
);

-- 索引
CREATE INDEX idx_api_usage_user_endpoint ON api_usage_stats(user_id, endpoint, window_start DESC);
CREATE INDEX idx_api_usage_user_window ON api_usage_stats(user_id, window_start);
CREATE INDEX idx_api_usage_created_at ON api_usage_stats(created_at DESC);
