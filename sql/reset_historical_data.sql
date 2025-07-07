-- Reset Historical Data for Fresh Portfolio Monitoring Start
-- This script clears all historical data while preserving critical configuration
-- 
-- PRESERVES:
-- - binance_accounts (API credentials and account settings)
-- - benchmark_configs (current BTC/ETH benchmark units)
--
-- CLEARS:
-- - nav_history (portfolio performance history)
-- - price_history (historical price data) 
-- - processed_transactions (transaction tracking)
-- - account_processing_status (processing timestamps)
-- - system_logs (application logs)

-- Clear historical portfolio performance data
DELETE FROM nav_history;

-- Clear historical price data
DELETE FROM price_history;

-- Clear processed transaction history
DELETE FROM processed_transactions;

-- Clear account processing status (will reset last processed timestamps)
DELETE FROM account_processing_status;

-- Clear system logs
DELETE FROM system_logs;

-- Verify what's preserved (should return data)
SELECT 'binance_accounts' as table_name, count(*) as records_preserved FROM binance_accounts
UNION ALL
SELECT 'benchmark_configs', count(*) FROM benchmark_configs;

-- Verify what's cleared (should return 0)
SELECT 'nav_history' as table_name, count(*) as records_remaining FROM nav_history
UNION ALL
SELECT 'price_history', count(*) FROM price_history  
UNION ALL
SELECT 'processed_transactions', count(*) FROM processed_transactions
UNION ALL
SELECT 'account_processing_status', count(*) FROM account_processing_status
UNION ALL
SELECT 'system_logs', count(*) FROM system_logs;

-- Reset database sequences if needed
-- This ensures fresh IDs start from 1 again
SELECT setval(pg_get_serial_sequence('nav_history', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('price_history', 'id'), 1, false); 
SELECT setval(pg_get_serial_sequence('processed_transactions', 'id'), 1, false);
SELECT setval(pg_get_serial_sequence('system_logs', 'id'), 1, false);

COMMENT ON SCRIPT 'reset_historical_data.sql' IS 'Clears all historical monitoring data for fresh start while preserving account configuration and benchmark state';