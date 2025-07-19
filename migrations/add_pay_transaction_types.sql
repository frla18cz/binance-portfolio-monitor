-- Add PAY_DEPOSIT and PAY_WITHDRAWAL to transaction_type enum
-- First, we need to drop and recreate the check constraint

-- Drop the existing check constraint
ALTER TABLE processed_transactions 
DROP CONSTRAINT IF EXISTS processed_transactions_transaction_type_check;

-- Add new check constraint that includes PAY transaction types
ALTER TABLE processed_transactions 
ADD CONSTRAINT processed_transactions_transaction_type_check 
CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL'));

-- Verify the constraint was added
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'processed_transactions'::regclass 
AND contype = 'c';