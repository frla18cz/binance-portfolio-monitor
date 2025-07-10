-- Create nav_history table for hourly data collection
CREATE TABLE IF NOT EXISTS nav_history (
    id BIGSERIAL PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES binance_accounts(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    nav NUMERIC NOT NULL,
    benchmark_value NUMERIC NOT NULL,
    btc_price NUMERIC,
    eth_price NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_nav_history_account_id ON nav_history(account_id);
CREATE INDEX IF NOT EXISTS idx_nav_history_timestamp ON nav_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_nav_history_account_timestamp ON nav_history(account_id, timestamp DESC);

-- Add comment
COMMENT ON TABLE nav_history IS 'Stores hourly NAV and benchmark values for each account';