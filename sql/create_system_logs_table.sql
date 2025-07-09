-- Create system_logs table for storing application logs
-- This table stores all system logs when running in serverless environments (Vercel)

CREATE TABLE IF NOT EXISTS system_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    account_id TEXT,
    account_name VARCHAR(255),
    operation VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    duration_ms DECIMAL(10,2),
    success BOOLEAN,
    error TEXT,
    session_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_category ON system_logs(category);
CREATE INDEX IF NOT EXISTS idx_system_logs_account_id ON system_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_session_id ON system_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);

-- Create composite index for dashboard queries
CREATE INDEX IF NOT EXISTS idx_system_logs_recent ON system_logs(created_at DESC, level, category);

-- Add RLS (Row Level Security) policies if needed
-- ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;

-- Create function to automatically cleanup old logs (optional)
CREATE OR REPLACE FUNCTION cleanup_old_system_logs()
RETURNS void AS $$
BEGIN
    -- Delete logs older than retention period (configurable)
    DELETE FROM system_logs 
    WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Create scheduled cleanup (run weekly)
-- SELECT cron.schedule('cleanup-system-logs', '0 2 * * 0', 'SELECT cleanup_old_system_logs();');

COMMENT ON TABLE system_logs IS 'System logs for Binance Portfolio Monitor - used in serverless environments';
COMMENT ON COLUMN system_logs.level IS 'Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL';
COMMENT ON COLUMN system_logs.category IS 'Log category: account_processing, api_call, database, etc.';
COMMENT ON COLUMN system_logs.account_id IS 'Account UUID as text (supports both UUIDs and legacy integer IDs)';
COMMENT ON COLUMN system_logs.data IS 'Additional structured data in JSON format';
COMMENT ON COLUMN system_logs.duration_ms IS 'Operation duration in milliseconds (for performance tracking)';
COMMENT ON COLUMN system_logs.success IS 'Whether the operation was successful (TRUE/FALSE)';
COMMENT ON COLUMN system_logs.error IS 'Error message if operation failed';
COMMENT ON COLUMN system_logs.session_id IS 'Unique session identifier for grouping related logs';