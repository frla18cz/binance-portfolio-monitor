-- Complete Migration: Remove transaction_type column
-- Date: 2025-07-20
-- Purpose: Complete the migration from transaction_type to type column

-- Step 1: Final data integrity check
DO $$
BEGIN
    -- Check for any mismatches or null values
    IF EXISTS (
        SELECT 1 FROM processed_transactions 
        WHERE transaction_type != type OR type IS NULL
    ) THEN
        RAISE EXCEPTION 'Data integrity check failed: Found mismatched or NULL type values';
    END IF;
    
    RAISE NOTICE 'Data integrity check passed';
END $$;

-- Step 2: Update type column constraints
ALTER TABLE processed_transactions 
ALTER COLUMN type SET NOT NULL;

-- Keep as TEXT type (it's already text, no need to change to varchar)

-- Step 3: Create new constraint on type column
ALTER TABLE processed_transactions 
ADD CONSTRAINT processed_transactions_type_check 
CHECK (type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL'));

-- Step 4: Create index on type column if not exists
CREATE INDEX IF NOT EXISTS idx_processed_transactions_new_type 
ON processed_transactions(type);

-- Step 5: Drop old constraints and indexes
DROP INDEX IF EXISTS idx_processed_transactions_type;

ALTER TABLE processed_transactions 
DROP CONSTRAINT IF EXISTS processed_transactions_transaction_type_check;

-- Step 6: Drop the old column
ALTER TABLE processed_transactions 
DROP COLUMN transaction_type;

-- Step 7: Rename the new index to the standard name
ALTER INDEX idx_processed_transactions_new_type 
RENAME TO idx_processed_transactions_type;

-- Step 8: Verify the migration
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    -- Check that transaction_type column no longer exists
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns 
    WHERE table_name = 'processed_transactions' 
    AND column_name = 'transaction_type';
    
    IF col_count > 0 THEN
        RAISE EXCEPTION 'Migration failed: transaction_type column still exists';
    END IF;
    
    -- Check that type column exists with correct constraints
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns 
    WHERE table_name = 'processed_transactions' 
    AND column_name = 'type'
    AND is_nullable = 'NO';
    
    IF col_count != 1 THEN
        RAISE EXCEPTION 'Migration failed: type column not properly configured';
    END IF;
    
    RAISE NOTICE 'Migration completed successfully!';
END $$;