-- Table for storing system metadata like last cleanup time
CREATE TABLE IF NOT EXISTS system_metadata (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_system_metadata_key ON system_metadata(key);

-- Add RLS policy
ALTER TABLE system_metadata ENABLE ROW LEVEL SECURITY;

-- Policy to allow service role full access
CREATE POLICY "Service role can manage system metadata" ON system_metadata
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

COMMENT ON TABLE system_metadata IS 'System metadata storage for tracking internal state';
COMMENT ON COLUMN system_metadata.key IS 'Unique identifier for the metadata entry';
COMMENT ON COLUMN system_metadata.value IS 'JSON or text value for the metadata';