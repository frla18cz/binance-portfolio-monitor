-- Migration script to update existing system_logs table
-- Run this in Supabase Dashboard > SQL Editor

-- 1. Change account_id from INTEGER to TEXT to support UUIDs
ALTER TABLE system_logs ALTER COLUMN account_id TYPE TEXT;

-- 2. Add missing columns that the logger expects
ALTER TABLE system_logs ADD COLUMN IF NOT EXISTS success BOOLEAN;
ALTER TABLE system_logs ADD COLUMN IF NOT EXISTS error TEXT;

-- 3. Update comments for new columns
COMMENT ON COLUMN system_logs.account_id IS 'Account UUID as text (supports both UUIDs and legacy integer IDs)';
COMMENT ON COLUMN system_logs.success IS 'Whether the operation was successful (TRUE/FALSE)';
COMMENT ON COLUMN system_logs.error IS 'Error message if operation failed';

-- 4. Verify the migration worked
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'system_logs' 
    AND table_schema = 'public'
ORDER BY ordinal_position;