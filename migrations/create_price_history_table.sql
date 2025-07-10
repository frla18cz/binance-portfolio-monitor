-- Create price_history table for hourly price tracking
CREATE TABLE IF NOT EXISTS price_history (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    btc_price NUMERIC NOT NULL,
    eth_price NUMERIC NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for timestamp queries
CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp DESC);

-- Add comment
COMMENT ON TABLE price_history IS 'Stores hourly BTC and ETH prices in USDT';