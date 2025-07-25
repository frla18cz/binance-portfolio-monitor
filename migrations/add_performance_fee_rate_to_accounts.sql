-- Migration: Add performance_fee_rate to binance_accounts
-- Date: 2025-07-25
-- Purpose: Allow individual performance fee rates per account

-- Add performance_fee_rate column to binance_accounts
ALTER TABLE binance_accounts 
ADD COLUMN IF NOT EXISTS performance_fee_rate DECIMAL(5,4) DEFAULT 0.50 
CHECK (performance_fee_rate >= 0 AND performance_fee_rate <= 1);

-- Add comment
COMMENT ON COLUMN binance_accounts.performance_fee_rate IS 'Performance fee rate for this account (0.50 = 50%, default from settings.json)';

-- Update existing accounts to use the default rate
UPDATE binance_accounts 
SET performance_fee_rate = 0.50 
WHERE performance_fee_rate IS NULL;

-- Verify the column was added
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'binance_accounts' 
        AND column_name = 'performance_fee_rate'
    ) THEN
        RAISE NOTICE 'performance_fee_rate column successfully added to binance_accounts';
    ELSE
        RAISE EXCEPTION 'Failed to add performance_fee_rate column';
    END IF;
END $$;