CREATE TABLE file_processing_queue (
    id BIGSERIAL PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    processing_stage VARCHAR(50),
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    total_chunks INTEGER,
    processed_chunks INTEGER DEFAULT 0,
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(file_id)
);

-- 索引
CREATE INDEX idx_file_processing_user_status ON file_processing_queue(user_id, status, created_at DESC);
CREATE INDEX idx_file_processing_status_retry ON file_processing_queue(status, retry_count);

-- 更新時間觸發器
CREATE TRIGGER update_file_processing_queue_updated_at
    BEFORE UPDATE ON file_processing_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
