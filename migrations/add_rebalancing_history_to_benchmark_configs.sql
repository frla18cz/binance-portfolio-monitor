-- Migration: Add rebalancing history columns to benchmark_configs table
-- Date: 2025-01-11
-- Description: Adds columns to track rebalancing history and status

-- Step 1: Add rebalancing history columns
ALTER TABLE benchmark_configs 
ADD COLUMN IF NOT EXISTS last_rebalance_timestamp TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_rebalance_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS last_rebalance_error TEXT,
ADD COLUMN IF NOT EXISTS rebalance_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_rebalance_btc_units DECIMAL(20,8),
ADD COLUMN IF NOT EXISTS last_rebalance_eth_units DECIMAL(20,8);

-- Step 2: Add check constraint for status values
ALTER TABLE benchmark_configs 
ADD CONSTRAINT chk_rebalance_status 
CHECK (last_rebalance_status IN ('pending', 'success', 'failed', 'skipped'));

-- Step 3: Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_benchmark_configs_last_rebalance ON benchmark_configs(last_rebalance_timestamp);
CREATE INDEX IF NOT EXISTS idx_benchmark_configs_rebalance_status ON benchmark_configs(last_rebalance_status);

-- Step 4: Add comments for documentation
COMMENT ON COLUMN benchmark_configs.last_rebalance_timestamp IS 'When the last rebalancing was performed';
COMMENT ON COLUMN benchmark_configs.last_rebalance_status IS 'Status of last rebalancing: pending, success, failed, skipped';
COMMENT ON COLUMN benchmark_configs.last_rebalance_error IS 'Error message if last rebalancing failed';
COMMENT ON COLUMN benchmark_configs.rebalance_count IS 'Total number of rebalancings performed';
COMMENT ON COLUMN benchmark_configs.last_rebalance_btc_units IS 'BTC units before last rebalancing';
COMMENT ON COLUMN benchmark_configs.last_rebalance_eth_units IS 'ETH units before last rebalancing';

-- Step 5: Update existing records to set initial values
UPDATE benchmark_configs 
SET 
    last_rebalance_status = 'pending',
    rebalance_count = 0
WHERE last_rebalance_status IS NULL;

-- Verification queries (uncomment to test):
-- SELECT id, account_name, last_rebalance_timestamp, last_rebalance_status, rebalance_count FROM benchmark_configs ORDER BY id;
-- SELECT COUNT(*) FROM benchmark_configs WHERE last_rebalance_status IS NOT NULL;