-- Migration: Add PAY_DEPOSIT and PAY_WITHDRAWAL transaction types
-- Date: 2025-01-19
-- Purpose: Support Binance Pay transactions (email/phone transfers)

-- Start transaction for atomicity
BEGIN;

-- Drop the existing check constraint
ALTER TABLE processed_transactions 
DROP CONSTRAINT IF EXISTS processed_transactions_transaction_type_check;

-- Add new check constraint that includes PAY transaction types
ALTER TABLE processed_transactions 
ADD CONSTRAINT processed_transactions_transaction_type_check 
CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL'));

-- Verify the constraint was added (will show in query results)
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint 
WHERE conrelid = 'processed_transactions'::regclass 
AND contype = 'c';

-- Commit the transaction
COMMIT;

-- Additional verification query (run separately to see results)
-- This shows all existing transaction types in the database
SELECT DISTINCT transaction_type, COUNT(*) as count
FROM processed_transactions
GROUP BY transaction_type
ORDER BY transaction_type;