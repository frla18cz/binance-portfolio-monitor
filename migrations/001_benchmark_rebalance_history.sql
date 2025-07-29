-- Migration: Create benchmark_rebalance_history table
-- Purpose: Store complete history of all benchmark rebalancing operations
-- Date: 2025-07-29

CREATE TABLE IF NOT EXISTS benchmark_rebalance_history (
    id BIGSERIAL PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES binance_accounts(id) ON DELETE CASCADE,
    account_name VARCHAR(255),
    rebalance_timestamp TIMESTAMPTZ NOT NULL,
    
    -- State BEFORE rebalancing
    btc_units_before NUMERIC(20,10) NOT NULL,
    eth_units_before NUMERIC(20,10) NOT NULL,
    btc_price NUMERIC(20,8) NOT NULL,
    eth_price NUMERIC(20,8) NOT NULL,
    btc_value_before NUMERIC(20,8) NOT NULL,
    eth_value_before NUMERIC(20,8) NOT NULL,
    total_value_before NUMERIC(20,8) NOT NULL,
    btc_percentage_before NUMERIC(6,4),
    eth_percentage_before NUMERIC(6,4),
    
    -- State AFTER rebalancing
    btc_units_after NUMERIC(20,10) NOT NULL,
    eth_units_after NUMERIC(20,10) NOT NULL,
    btc_value_after NUMERIC(20,8) NOT NULL,
    eth_value_after NUMERIC(20,8) NOT NULL,
    total_value_after NUMERIC(20,8) NOT NULL,
    
    -- Changes
    btc_units_change NUMERIC(20,10) GENERATED ALWAYS AS (btc_units_after - btc_units_before) STORED,
    eth_units_change NUMERIC(20,10) GENERATED ALWAYS AS (eth_units_after - eth_units_before) STORED,
    
    -- Metadata
    rebalance_type VARCHAR(20) NOT NULL DEFAULT 'scheduled' CHECK (rebalance_type IN ('scheduled', 'manual', 'init')),
    status VARCHAR(20) NOT NULL DEFAULT 'success' CHECK (status IN ('success', 'failed', 'validated')),
    error_message TEXT,
    validation_error NUMERIC(6,4), -- % deviation from expected value
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_rebalance_history_account_timestamp 
    ON benchmark_rebalance_history(account_id, rebalance_timestamp DESC);
CREATE INDEX idx_rebalance_history_timestamp 
    ON benchmark_rebalance_history(rebalance_timestamp DESC);
CREATE INDEX idx_rebalance_history_account_name 
    ON benchmark_rebalance_history(account_name);

-- Trigger to populate account_name from binance_accounts
CREATE OR REPLACE FUNCTION populate_rebalance_history_account_name()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.account_name IS NULL THEN
        SELECT account_name INTO NEW.account_name
        FROM binance_accounts
        WHERE id = NEW.account_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER rebalance_history_account_name_trigger
    BEFORE INSERT ON benchmark_rebalance_history
    FOR EACH ROW
    EXECUTE FUNCTION populate_rebalance_history_account_name();

-- Comment on table
COMMENT ON TABLE benchmark_rebalance_history IS 'Complete history of all benchmark rebalancing operations with full audit trail';