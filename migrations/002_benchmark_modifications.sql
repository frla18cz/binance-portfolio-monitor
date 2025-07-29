-- Migration: Create benchmark_modifications table
-- Purpose: Track all benchmark adjustments due to deposits/withdrawals
-- Date: 2025-07-29

CREATE TABLE IF NOT EXISTS benchmark_modifications (
    id BIGSERIAL PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES binance_accounts(id) ON DELETE CASCADE,
    account_name VARCHAR(255),
    modification_timestamp TIMESTAMPTZ NOT NULL,
    modification_type VARCHAR(20) NOT NULL CHECK (modification_type IN ('deposit', 'withdrawal', 'fee_withdrawal')),
    
    -- State before modification
    btc_units_before NUMERIC(20,10) NOT NULL,
    eth_units_before NUMERIC(20,10) NOT NULL,
    
    -- Cashflow details
    cashflow_amount NUMERIC(20,8) NOT NULL,
    btc_price NUMERIC(20,8) NOT NULL,
    eth_price NUMERIC(20,8) NOT NULL,
    
    -- Allocation calculation (50/50 split)
    btc_allocation NUMERIC(20,8), -- 50% of cashflow
    eth_allocation NUMERIC(20,8), -- 50% of cashflow
    btc_units_bought NUMERIC(20,10), -- btc_allocation / btc_price
    eth_units_bought NUMERIC(20,10), -- eth_allocation / eth_price
    
    -- State after modification
    btc_units_after NUMERIC(20,10) NOT NULL,
    eth_units_after NUMERIC(20,10) NOT NULL,
    
    -- Total values for verification
    total_value_before NUMERIC(20,8) GENERATED ALWAYS AS 
        (btc_units_before * btc_price + eth_units_before * eth_price) STORED,
    total_value_after NUMERIC(20,8) GENERATED ALWAYS AS 
        (btc_units_after * btc_price + eth_units_after * eth_price) STORED,
    
    -- Reference to original transaction
    transaction_id VARCHAR(255),
    transaction_type VARCHAR(50), -- Original transaction type from processed_transactions
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_benchmark_mods_account_timestamp 
    ON benchmark_modifications(account_id, modification_timestamp DESC);
CREATE INDEX idx_benchmark_mods_timestamp 
    ON benchmark_modifications(modification_timestamp DESC);
CREATE INDEX idx_benchmark_mods_transaction_id 
    ON benchmark_modifications(transaction_id);
CREATE INDEX idx_benchmark_mods_type 
    ON benchmark_modifications(modification_type);

-- Trigger to populate account_name from binance_accounts
CREATE OR REPLACE FUNCTION populate_benchmark_mods_account_name()
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

CREATE TRIGGER benchmark_mods_account_name_trigger
    BEFORE INSERT ON benchmark_modifications
    FOR EACH ROW
    EXECUTE FUNCTION populate_benchmark_mods_account_name();

-- Comment on table
COMMENT ON TABLE benchmark_modifications IS 'Tracks all benchmark adjustments for deposits/withdrawals with full calculation details';

-- Add audit columns to benchmark_configs
ALTER TABLE benchmark_configs 
    ADD COLUMN IF NOT EXISTS last_modification_type VARCHAR(20),
    ADD COLUMN IF NOT EXISTS last_modification_timestamp TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_modification_amount NUMERIC(20,8),
    ADD COLUMN IF NOT EXISTS last_modification_id BIGINT REFERENCES benchmark_modifications(id);

-- Comment on new columns
COMMENT ON COLUMN benchmark_configs.last_modification_type IS 'Type of last modification (deposit/withdrawal/fee_withdrawal)';
COMMENT ON COLUMN benchmark_configs.last_modification_timestamp IS 'Timestamp of last modification';
COMMENT ON COLUMN benchmark_configs.last_modification_amount IS 'Amount of last modification in USD';
COMMENT ON COLUMN benchmark_configs.last_modification_id IS 'Reference to last modification record';