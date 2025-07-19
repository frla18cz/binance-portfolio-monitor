-- Complete Migration for Binance Pay Support
-- Date: 2025-01-19
-- Purpose: Ensure all requirements for Pay transaction detection are met

-- Start transaction
BEGIN;

-- 1. Check if metadata column exists (from previous migration)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'processed_transactions' 
        AND column_name = 'metadata'
    ) THEN
        -- Add metadata column if it doesn't exist
        ALTER TABLE processed_transactions 
        ADD COLUMN metadata JSONB;
        
        COMMENT ON COLUMN processed_transactions.metadata IS 
        'Additional transaction data including transfer type, network info, and contact details';
        
        -- Create index for metadata queries
        CREATE INDEX idx_processed_transactions_metadata_transfer_type 
        ON processed_transactions ((metadata->>'transfer_type'))
        WHERE metadata IS NOT NULL;
        
        RAISE NOTICE 'Added metadata column to processed_transactions table';
    ELSE
        RAISE NOTICE 'Metadata column already exists';
    END IF;
END $$;

-- 2. Update transaction type constraint to include PAY types
ALTER TABLE processed_transactions 
DROP CONSTRAINT IF EXISTS processed_transactions_transaction_type_check;

ALTER TABLE processed_transactions 
ADD CONSTRAINT processed_transactions_transaction_type_check 
CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL'));

-- 3. Verify the changes
SELECT 
    'Constraint updated' as status,
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint 
WHERE conrelid = 'processed_transactions'::regclass 
AND contype = 'c';

-- 4. Show table structure
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'processed_transactions'
ORDER BY ordinal_position;

-- Commit all changes
COMMIT;

-- 5. Post-migration verification (run this separately)
-- Check if any PAY transactions already exist
SELECT 
    transaction_type,
    COUNT(*) as count,
    MIN(timestamp) as earliest,
    MAX(timestamp) as latest
FROM processed_transactions
WHERE transaction_type LIKE 'PAY%'
GROUP BY transaction_type
ORDER BY transaction_type;

-- Show sample of metadata content
SELECT 
    transaction_id,
    transaction_type,
    amount,
    metadata
FROM processed_transactions
WHERE metadata IS NOT NULL
LIMIT 5;