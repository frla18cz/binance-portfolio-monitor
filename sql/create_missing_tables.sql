-- Create missing tables for transaction processing
-- These tables are required for the transaction processing functionality

-- 1. Transaction processing tracking (prevents duplicates)
CREATE TABLE IF NOT EXISTS processed_transactions (
    id SERIAL PRIMARY KEY,
    account_id UUID REFERENCES binance_accounts(id),
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount DECIMAL(20,8) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Processing status per account
CREATE TABLE IF NOT EXISTS account_processing_status (
    account_id UUID PRIMARY KEY REFERENCES binance_accounts(id),
    last_processed_timestamp TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Price history table (optional but useful)
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    asset VARCHAR(10) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_processed_transactions_account_id ON processed_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_processed_transactions_timestamp ON processed_transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_processed_transactions_transaction_id ON processed_transactions(transaction_id);

CREATE INDEX IF NOT EXISTS idx_account_processing_status_account_id ON account_processing_status(account_id);
CREATE INDEX IF NOT EXISTS idx_account_processing_status_updated_at ON account_processing_status(updated_at);

CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_price_history_asset ON price_history(asset);

-- Add comments for documentation
COMMENT ON TABLE processed_transactions IS 'Tracks all processed deposit/withdrawal transactions to prevent duplicate processing';
COMMENT ON TABLE account_processing_status IS 'Stores the last processed timestamp for each account to track transaction processing state';
COMMENT ON TABLE price_history IS 'Historical price data for BTC and ETH used for benchmark calculations';

-- Verify tables were created
SELECT 
    table_name,
    obj_description(oid, 'pg_class') as description
FROM 
    information_schema.tables t
    JOIN pg_class c ON c.relname = t.table_name
WHERE 
    table_schema = 'public' 
    AND table_name IN ('processed_transactions', 'account_processing_status', 'price_history')
ORDER BY 
    table_name;