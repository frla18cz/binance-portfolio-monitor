-- Migration: Rename transaction_type column to type in processed_transactions table
-- Date: 2025-07-20
-- Purpose: Fix field name inconsistency between saving and reading transactions

-- First, add the new column if it doesn't exist
ALTER TABLE processed_transactions 
ADD COLUMN IF NOT EXISTS type TEXT;

-- Copy data from transaction_type to type
UPDATE processed_transactions 
SET type = transaction_type 
WHERE type IS NULL AND transaction_type IS NOT NULL;

-- Optional: Drop the old column after verification
-- ALTER TABLE processed_transactions DROP COLUMN transaction_type;

-- Add index on type column for better query performance
CREATE INDEX IF NOT EXISTS idx_processed_transactions_type 
ON processed_transactions(type);

-- Verify the migration
SELECT 
    COUNT(*) as total_records,
    COUNT(transaction_type) as records_with_transaction_type,
    COUNT(type) as records_with_type,
    COUNT(CASE WHEN type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL') THEN 1 END) as valid_types
FROM processed_transactions;