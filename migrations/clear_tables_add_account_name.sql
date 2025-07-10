-- Migration: Clear specified tables and add account_name to nav_history
-- Date: 2025-01-10
-- Description: Clears data from system_metadata, system_logs, processed_transactions, 
--              price_history, nav_history tables and adds account_name column to nav_history

-- Step 1: Clear data from specified tables
-- Using TRUNCATE for efficient data removal (also resets sequences)
TRUNCATE TABLE system_metadata CASCADE;
TRUNCATE TABLE system_logs CASCADE;
TRUNCATE TABLE processed_transactions CASCADE;
TRUNCATE TABLE price_history CASCADE;
TRUNCATE TABLE nav_history CASCADE;

-- Step 2: Add account_name column to nav_history table
ALTER TABLE nav_history 
ADD COLUMN IF NOT EXISTS account_name VARCHAR(255);

-- Step 3: Create function to automatically populate account_name on insert
-- This ensures new records get the account name from binance_accounts
CREATE OR REPLACE FUNCTION populate_nav_history_account_name()
RETURNS TRIGGER AS $$
BEGIN
    -- Populate account_name from binance_accounts table
    SELECT account_name INTO NEW.account_name
    FROM binance_accounts
    WHERE id = NEW.account_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Create trigger to automatically populate account_name
DROP TRIGGER IF EXISTS nav_history_account_name_trigger ON nav_history;
CREATE TRIGGER nav_history_account_name_trigger
    BEFORE INSERT ON nav_history
    FOR EACH ROW
    EXECUTE FUNCTION populate_nav_history_account_name();

-- Step 5: Update existing records (if any remain after truncate)
-- This is defensive programming in case truncate is skipped
UPDATE nav_history nh
SET account_name = ba.account_name
FROM binance_accounts ba
WHERE nh.account_id = ba.id
AND nh.account_name IS NULL;

-- Step 6: Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_nav_history_account_name ON nav_history(account_name);

-- Step 7: Add comment for documentation
COMMENT ON COLUMN nav_history.account_name IS 'Account name from binance_accounts table, populated automatically via trigger';

-- Verification queries (uncomment to test):
-- SELECT COUNT(*) FROM system_metadata;
-- SELECT COUNT(*) FROM system_logs;
-- SELECT COUNT(*) FROM processed_transactions;
-- SELECT COUNT(*) FROM price_history;
-- SELECT COUNT(*) FROM nav_history;
-- SELECT id, account_id, account_name, timestamp FROM nav_history ORDER BY timestamp DESC LIMIT 5;