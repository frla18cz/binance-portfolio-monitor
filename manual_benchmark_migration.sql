-- Complete benchmark_configs table migration
-- Run this SQL in Supabase SQL Editor
-- Date: 2025-01-11

-- Step 1: Add account_name column as second column
ALTER TABLE benchmark_configs 
ADD COLUMN IF NOT EXISTS account_name VARCHAR(255);

-- Step 2: Add rebalancing history columns
ALTER TABLE benchmark_configs 
ADD COLUMN IF NOT EXISTS last_rebalance_timestamp TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_rebalance_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS last_rebalance_error TEXT,
ADD COLUMN IF NOT EXISTS rebalance_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_rebalance_btc_units DECIMAL(20,8),
ADD COLUMN IF NOT EXISTS last_rebalance_eth_units DECIMAL(20,8);

-- Step 3: Add check constraint for status values
ALTER TABLE benchmark_configs 
ADD CONSTRAINT IF NOT EXISTS chk_rebalance_status 
CHECK (last_rebalance_status IN ('pending', 'success', 'failed', 'skipped'));

-- Step 4: Create function to automatically populate account_name
CREATE OR REPLACE FUNCTION populate_benchmark_configs_account_name()
RETURNS TRIGGER AS $$
BEGIN
    -- Populate account_name from binance_accounts table
    SELECT account_name INTO NEW.account_name
    FROM binance_accounts
    WHERE id = NEW.account_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create trigger to automatically populate account_name
DROP TRIGGER IF EXISTS benchmark_configs_account_name_trigger ON benchmark_configs;
CREATE TRIGGER benchmark_configs_account_name_trigger
    BEFORE INSERT OR UPDATE ON benchmark_configs
    FOR EACH ROW
    EXECUTE FUNCTION populate_benchmark_configs_account_name();

-- Step 6: Update existing records to populate account_name
UPDATE benchmark_configs bc
SET account_name = ba.account_name
FROM binance_accounts ba
WHERE bc.account_id = ba.id
AND bc.account_name IS NULL;

-- Step 7: Update existing records to set default values for new columns
UPDATE benchmark_configs 
SET 
    last_rebalance_status = 'pending',
    rebalance_count = 0
WHERE last_rebalance_status IS NULL;

-- Step 8: Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_benchmark_configs_account_name ON benchmark_configs(account_name);
CREATE INDEX IF NOT EXISTS idx_benchmark_configs_last_rebalance ON benchmark_configs(last_rebalance_timestamp);
CREATE INDEX IF NOT EXISTS idx_benchmark_configs_rebalance_status ON benchmark_configs(last_rebalance_status);

-- Step 9: Add comments for documentation
COMMENT ON COLUMN benchmark_configs.account_name IS 'Account name from binance_accounts table, populated automatically via trigger';
COMMENT ON COLUMN benchmark_configs.last_rebalance_timestamp IS 'When the last rebalancing was performed';
COMMENT ON COLUMN benchmark_configs.last_rebalance_status IS 'Status of last rebalancing: pending, success, failed, skipped';
COMMENT ON COLUMN benchmark_configs.last_rebalance_error IS 'Error message if last rebalancing failed';
COMMENT ON COLUMN benchmark_configs.rebalance_count IS 'Total number of rebalancings performed';
COMMENT ON COLUMN benchmark_configs.last_rebalance_btc_units IS 'BTC units before last rebalancing';
COMMENT ON COLUMN benchmark_configs.last_rebalance_eth_units IS 'ETH units before last rebalancing';

-- Verification queries
SELECT 
    id, 
    account_name, 
    account_id, 
    btc_units, 
    eth_units,
    last_rebalance_timestamp,
    last_rebalance_status,
    rebalance_count
FROM benchmark_configs 
ORDER BY id;