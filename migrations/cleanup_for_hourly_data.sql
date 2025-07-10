-- Cleanup script for transitioning to hourly data collection
-- This will remove all historical data and start fresh

-- Drop tables with historical data
DROP TABLE IF EXISTS nav_history CASCADE;
DROP TABLE IF EXISTS price_history CASCADE;
DROP TABLE IF EXISTS processed_transactions CASCADE;

-- Clear system logs but keep the table structure
TRUNCATE TABLE system_logs;

-- Reset system metadata for fresh start
UPDATE system_metadata 
SET value = NOW()::text, updated_at = NOW()
WHERE key = 'last_log_cleanup';

-- Reset account processing status
TRUNCATE TABLE account_processing_status;

-- Note: We keep these tables as they contain configuration and constants:
-- - binance_accounts (API keys and account settings)
-- - benchmark_configs (benchmark portfolio settings)
-- - system_metadata (system state tracking)