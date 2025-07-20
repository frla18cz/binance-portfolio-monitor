# Transaction Type Field Migration

## Overview
This document describes the migration from `transaction_type` to `type` field in the `processed_transactions` table, completed on 2025-07-20.

## Background

### The Problem
The codebase had an inconsistency in field naming:
- **Saving**: Transactions were saved with field name `transaction_type`
- **Reading**: Code expected field name `type` when processing transactions

This mismatch caused:
1. Transactions to be marked as "UNKNOWN" type
2. Deposits and withdrawals not being processed
3. Benchmark adjustments not being applied
4. Incorrect portfolio performance calculations

### Example Impact
A PAY_WITHDRAWAL of $5 from ondra(test) account was saved but never processed, causing the benchmark to remain unchanged when it should have decreased proportionally.

## Migration Details

### Database Changes

#### Before Migration
```sql
CREATE TABLE processed_transactions (
    -- other fields...
    transaction_type VARCHAR(20) NOT NULL,
    -- other fields...
);
```

#### After Migration
```sql
CREATE TABLE processed_transactions (
    -- other fields...
    type TEXT NOT NULL CHECK (type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL')),
    -- other fields...
);
```

### Migration Steps Performed

1. **Data Migration**
   ```sql
   -- Add new column
   ALTER TABLE processed_transactions ADD COLUMN IF NOT EXISTS type TEXT;
   
   -- Copy data
   UPDATE processed_transactions 
   SET type = transaction_type 
   WHERE type IS NULL AND transaction_type IS NOT NULL;
   ```

2. **Constraint Updates**
   ```sql
   -- Add NOT NULL constraint
   ALTER TABLE processed_transactions ALTER COLUMN type SET NOT NULL;
   
   -- Add CHECK constraint
   ALTER TABLE processed_transactions 
   ADD CONSTRAINT processed_transactions_type_check 
   CHECK (type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL'));
   ```

3. **Index Updates**
   ```sql
   -- Create new index
   CREATE INDEX idx_processed_transactions_type ON processed_transactions(type);
   
   -- Drop old index
   DROP INDEX idx_processed_transactions_type; -- old one on transaction_type
   ```

4. **Column Removal**
   ```sql
   -- Drop old constraints
   ALTER TABLE processed_transactions 
   DROP CONSTRAINT processed_transactions_transaction_type_check;
   
   -- Drop old column
   ALTER TABLE processed_transactions DROP COLUMN transaction_type;
   ```

### Code Changes

#### api/index.py
Removed backward compatibility code:
```python
# Before
txn_type = txn.get('type') or txn.get('transaction_type')

# After
if not txn.get('type'):
    # error handling
```

#### sql/create_missing_tables.sql
Updated schema definition to use `type` field with proper constraints.

## Impact Analysis

### Data Integrity
- ✅ All existing transactions preserved
- ✅ Data successfully migrated from `transaction_type` to `type`
- ✅ No data loss during migration

### Historical Data
- ⚠️ Transactions processed before migration remain marked as processed
- The $5 PAY_WITHDRAWAL from ondra(test) will not be reprocessed
- This is acceptable for a test account

### Future Operations
- ✅ New transactions will be saved with correct `type` field
- ✅ All transaction processing will work correctly
- ✅ Benchmark adjustments will be applied properly

## Rollback Procedure

⚠️ **Warning**: This is a destructive migration. Rollback requires recreating the old column and may cause data inconsistencies.

If absolutely necessary to rollback:

1. **Recreate old column**
   ```sql
   ALTER TABLE processed_transactions 
   ADD COLUMN transaction_type VARCHAR(20);
   
   UPDATE processed_transactions 
   SET transaction_type = type;
   
   ALTER TABLE processed_transactions 
   ALTER COLUMN transaction_type SET NOT NULL;
   ```

2. **Restore old constraints**
   ```sql
   ALTER TABLE processed_transactions 
   ADD CONSTRAINT processed_transactions_transaction_type_check 
   CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL'));
   ```

3. **Update code** to use `transaction_type` again

## Verification

Run these queries to verify migration success:

```sql
-- Check column exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'processed_transactions' 
AND column_name = 'type';

-- Verify constraint
SELECT conname, contype, consrc
FROM pg_constraint
WHERE conrelid = 'processed_transactions'::regclass
AND conname LIKE '%type%';

-- Check data integrity
SELECT type, COUNT(*) 
FROM processed_transactions 
GROUP BY type;
```

## Lessons Learned

1. **Consistency**: Always use consistent field names between database and code
2. **Testing**: Test migrations on development data before production
3. **Documentation**: Document schema changes immediately
4. **Validation**: Add validation to catch field mismatches early

## Related Files
- Migration SQL: `migrations/complete_type_migration.sql`
- Original issue fix: `migrations/rename_transaction_type_column.sql`
- Schema definition: `sql/create_missing_tables.sql`