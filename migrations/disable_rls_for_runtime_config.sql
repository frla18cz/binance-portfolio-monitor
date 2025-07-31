-- Disable Row Level Security for runtime configuration tables
-- This makes development easier - run this if you already created the tables with RLS

-- Disable RLS
ALTER TABLE IF EXISTS runtime_config DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS runtime_config_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS account_config_overrides DISABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Service role can manage runtime config" ON runtime_config;
DROP POLICY IF EXISTS "Service role can view config history" ON runtime_config_history;
DROP POLICY IF EXISTS "Service role can manage account overrides" ON account_config_overrides;

-- Verify RLS is disabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('runtime_config', 'runtime_config_history', 'account_config_overrides');