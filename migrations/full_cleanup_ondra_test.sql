-- Full cleanup of all data for Ondra(test) account
-- This removes all historical data so the account can start fresh
-- Account ID: 6236a826-b352-4696-83ad-7cb1f8be1556
-- Date: 2025-07-20

BEGIN;

-- 1. Delete all NAV history
DELETE FROM nav_history
WHERE account_id = '6236a826-b352-4696-83ad-7cb1f8be1556';

-- 2. Delete all processed transactions
DELETE FROM processed_transactions
WHERE account_id = '6236a826-b352-4696-83ad-7cb1f8be1556';

-- 3. Delete account processing status
DELETE FROM account_processing_status
WHERE account_id = '6236a826-b352-4696-83ad-7cb1f8be1556';

-- 4. Reset benchmark config to initial state (0 units = will reinitialize)
UPDATE benchmark_configs
SET btc_units = 0,
    eth_units = 0,
    initialized_at = NULL,
    last_rebalance_timestamp = NULL,
    last_rebalance_status = NULL,
    last_rebalance_error = NULL,
    rebalance_count = 0,
    last_rebalance_btc_units = NULL,
    last_rebalance_eth_units = NULL,
    last_transaction_check_timestamp = NULL,
    updated_at = NOW()
WHERE account_id = '6236a826-b352-4696-83ad-7cb1f8be1556';

-- 5. Delete related system logs (optional - uncomment if you want to clean logs too)
-- DELETE FROM system_logs
-- WHERE account_id = '6236a826-b352-4696-83ad-7cb1f8be1556';

-- Summary of what will remain:
-- - Account still exists in binance_accounts with API keys
-- - Benchmark config exists but reset to 0 (will initialize on next run)
-- - No historical data

-- Verify the cleanup
SELECT 
    'nav_history' as table_name,
    COUNT(*) as records
FROM nav_history
WHERE account_id = '6236a826-b352-4696-83ad-7cb1f8be1556'
UNION ALL
SELECT 
    'processed_transactions',
    COUNT(*)
FROM processed_transactions
WHERE account_id = '6236a826-b352-4696-83ad-7cb1f8be1556'
UNION ALL
SELECT 
    'benchmark_configs',
    COUNT(*)
FROM benchmark_configs
WHERE account_id = '6236a826-b352-4696-83ad-7cb1f8be1556';

COMMIT;