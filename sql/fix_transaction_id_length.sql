-- Migration: Increase transaction_id column size to handle longer Binance transaction IDs
-- Issue: Current VARCHAR(50) is too small for some Binance transaction IDs
-- Fix: Increase to VARCHAR(255) to accommodate all possible transaction ID lengths

-- Step 1: Alter the column to increase size
ALTER TABLE processed_transactions 
ALTER COLUMN transaction_id TYPE VARCHAR(255);

-- Step 2: Verify the change
SELECT 
    column_name,
    data_type,
    character_maximum_length
FROM 
    information_schema.columns
WHERE 
    table_name = 'processed_transactions' 
    AND column_name = 'transaction_id';

-- Step 3: Add comment documenting the change
COMMENT ON COLUMN processed_transactions.transaction_id IS 'Unique transaction ID from Binance - increased to VARCHAR(255) to handle longer IDs';