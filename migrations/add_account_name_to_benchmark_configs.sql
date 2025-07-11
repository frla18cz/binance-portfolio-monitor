-- Migration: Add account_name column to benchmark_configs table
-- Date: 2025-01-11
-- Description: Adds account_name as second column in benchmark_configs for better visibility

-- Step 1: Add account_name column as second column
ALTER TABLE benchmark_configs 
ADD COLUMN IF NOT EXISTS account_name VARCHAR(255);

-- Step 2: Create function to automatically populate account_name on insert/update
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

-- Step 3: Create trigger to automatically populate account_name
DROP TRIGGER IF EXISTS benchmark_configs_account_name_trigger ON benchmark_configs;
CREATE TRIGGER benchmark_configs_account_name_trigger
    BEFORE INSERT OR UPDATE ON benchmark_configs
    FOR EACH ROW
    EXECUTE FUNCTION populate_benchmark_configs_account_name();

-- Step 4: Update existing records to populate account_name
UPDATE benchmark_configs bc
SET account_name = ba.account_name
FROM binance_accounts ba
WHERE bc.account_id = ba.id
AND bc.account_name IS NULL;

-- Step 5: Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_benchmark_configs_account_name ON benchmark_configs(account_name);

-- Step 6: Add comment for documentation
COMMENT ON COLUMN benchmark_configs.account_name IS 'Account name from binance_accounts table, populated automatically via trigger';

-- Verification queries (uncomment to test):
-- SELECT id, account_name, account_id, btc_units, eth_units FROM benchmark_configs ORDER BY id;
-- SELECT COUNT(*) FROM benchmark_configs WHERE account_name IS NOT NULL;