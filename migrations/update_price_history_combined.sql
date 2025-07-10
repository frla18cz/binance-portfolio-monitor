-- Migration: Update price_history table to store BTC and ETH prices on the same row
-- Date: 2025-01-10
-- Purpose: Improve performance and simplify queries by storing both prices together

-- Step 1: Drop the existing price_history table (it's unused)
DROP TABLE IF EXISTS price_history CASCADE;

-- Step 2: Create new price_history table with combined price columns
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    btc_price DECIMAL(20,8) NOT NULL,
    eth_price DECIMAL(20,8) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 3: Create indexes for efficient querying
CREATE INDEX idx_price_history_timestamp ON price_history (timestamp);
CREATE INDEX idx_price_history_created_at ON price_history (created_at);

-- Step 4: Add unique constraint to prevent duplicate timestamps
CREATE UNIQUE INDEX idx_price_history_timestamp_unique ON price_history (timestamp);

-- Add comment to explain the table purpose
COMMENT ON TABLE price_history IS 'Historical BTC and ETH prices for benchmark calculations';
COMMENT ON COLUMN price_history.timestamp IS 'The exact time when prices were captured';
COMMENT ON COLUMN price_history.btc_price IS 'BTC price in USDT';
COMMENT ON COLUMN price_history.eth_price IS 'ETH price in USDT';