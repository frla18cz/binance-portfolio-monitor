-- Migration: Move account_name to second position in nav_history table
-- Date: 2025-07-10
-- Description: Recreate nav_history table with account_name as the second column

BEGIN;

-- Step 1: Create backup table with current data
CREATE TABLE nav_history_backup AS 
SELECT * FROM nav_history;

-- Step 2: Drop existing table (this will also drop the trigger and indexes)
DROP TABLE nav_history CASCADE;

-- Step 3: Recreate table with account_name as second column
CREATE TABLE nav_history (
    id BIGSERIAL PRIMARY KEY,
    account_name VARCHAR(255),
    account_id UUID NOT NULL REFERENCES binance_accounts(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    nav NUMERIC NOT NULL,
    benchmark_value NUMERIC NOT NULL,
    btc_price NUMERIC,
    eth_price NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Step 4: Restore data from backup
INSERT INTO nav_history (id, account_name, account_id, timestamp, nav, benchmark_value, btc_price, eth_price, created_at)
SELECT id, account_name, account_id, timestamp, nav, benchmark_value, btc_price, eth_price, created_at
FROM nav_history_backup
ORDER BY id;

-- Step 5: Reset sequence to continue from max ID
SELECT setval('nav_history_id_seq', COALESCE((SELECT MAX(id) FROM nav_history), 1), true);

-- Step 6: Recreate indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_nav_history_account_id ON nav_history(account_id);
CREATE INDEX IF NOT EXISTS idx_nav_history_timestamp ON nav_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_nav_history_account_timestamp ON nav_history(account_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_nav_history_account_name ON nav_history(account_name);

-- Step 7: Recreate trigger function and trigger
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

CREATE TRIGGER nav_history_account_name_trigger
    BEFORE INSERT ON nav_history
    FOR EACH ROW
    EXECUTE FUNCTION populate_nav_history_account_name();

-- Step 8: Add table and column comments
COMMENT ON TABLE nav_history IS 'Stores hourly NAV and benchmark values for each account';
COMMENT ON COLUMN nav_history.account_name IS 'Account name from binance_accounts table, populated automatically via trigger';

-- Step 9: Clean up backup table
DROP TABLE nav_history_backup;

COMMIT;

-- Verification queries:
-- SELECT column_name, ordinal_position, data_type FROM information_schema.columns WHERE table_name = 'nav_history' ORDER BY ordinal_position;
-- SELECT id, account_name, account_id, nav, timestamp FROM nav_history ORDER BY timestamp DESC LIMIT 5;