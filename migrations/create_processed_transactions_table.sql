-- Create processed_transactions table for tracking deposits/withdrawals
CREATE TABLE IF NOT EXISTS processed_transactions (
    id BIGSERIAL PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES binance_accounts(id) ON DELETE CASCADE,
    transaction_id VARCHAR(255) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL')),
    amount NUMERIC NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(account_id, transaction_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_processed_transactions_account_id ON processed_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_processed_transactions_timestamp ON processed_transactions(timestamp DESC);

-- Add comment
COMMENT ON TABLE processed_transactions IS 'Tracks processed deposits and withdrawals to adjust benchmark accordingly';