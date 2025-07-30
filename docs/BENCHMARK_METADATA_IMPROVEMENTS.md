# Benchmark Metadata Improvements

## Overview
This feature enhances benchmark tracking by storing complete metadata for all rebalancing operations and modifications, enabling full audit trail and consistency validation.

## What Was Added

### 1. New Database Tables

#### benchmark_rebalance_history
- Stores complete history of all rebalancing operations
- Tracks before/after states with exact calculations
- Includes prices at rebalance time
- Records validation errors

#### benchmark_modifications  
- Tracks all deposit/withdrawal impacts on benchmark
- Stores 50/50 split calculations for deposits
- Records proportional reductions for withdrawals
- Links to original transactions

### 2. Code Changes

#### api/index.py
- `rebalance_benchmark()` now saves full history to benchmark_rebalance_history
- `adjust_benchmark_for_cashflow()` now saves modification details
- Both functions preserve all calculation details for auditing

### 3. Validation Tools

#### scripts/validate_benchmark_consistency.py
- Recalculates benchmark from transaction history
- Compares with current values
- Reports any discrepancies
- Can be run on demand or scheduled

### 4. SQL Migrations
- `001_benchmark_rebalance_history.sql` - Creates rebalance history table
- `002_benchmark_modifications.sql` - Creates modifications table and audit columns

## How to Use

### Apply Migrations
```bash
# Use MCP tool in Supabase
mcp__supabase__apply_migration(
    project_id="axvqumsxlncbqzecjlxy",
    name="benchmark_metadata_tables", 
    query=<migration SQL>
)
```

### Validate Consistency
```bash
# Check all accounts
python scripts/validate_benchmark_consistency.py

# Check specific account
python scripts/validate_benchmark_consistency.py --account "Simple"
```

### Query Historical Data
```sql
-- View rebalancing history
SELECT * FROM benchmark_rebalance_history 
WHERE account_name = 'Simple'
ORDER BY rebalance_timestamp DESC;

-- View modification history
SELECT * FROM benchmark_modifications
WHERE account_name = 'Simple' 
ORDER BY modification_timestamp DESC;

-- Verify calculations
SELECT 
    rebalance_timestamp,
    btc_units_before * btc_price as calc_btc_value,
    btc_value_before as stored_btc_value,
    ABS(btc_units_before * btc_price - btc_value_before) as difference
FROM benchmark_rebalance_history;
```

## Benefits

1. **Full Auditability** - Can trace every change to benchmark
2. **Debugging** - See exact calculations and values at each step
3. **Validation** - Automated consistency checking
4. **Analysis** - Study rebalancing patterns and effectiveness
5. **Recovery** - Can reconstruct benchmark state from history

## Example Use Cases

### 1. Verify Yesterday's Rebalancing
```sql
SELECT 
    account_name,
    rebalance_timestamp,
    btc_units_before,
    btc_units_after,
    btc_percentage_before,
    validation_error
FROM benchmark_rebalance_history
WHERE DATE(rebalance_timestamp) = '2025-07-28'
ORDER BY account_name;
```

### 2. Track Deposit Impact
```sql
SELECT 
    modification_timestamp,
    cashflow_amount,
    btc_units_before,
    btc_units_after,
    btc_units_after - btc_units_before as btc_change
FROM benchmark_modifications
WHERE modification_type = 'deposit'
AND account_name = 'Simple'
ORDER BY modification_timestamp DESC
LIMIT 10;
```

### 3. Validate Specific Period
```python
# In validation script
validator = BenchmarkValidator(db_client, account_id, account_name)
validator.validate()  # Full validation from initialization
```

## Future Enhancements

1. Add automated alerts for validation failures
2. Create dashboard views for benchmark drift analysis  
3. Add recovery tools to fix discrepancies
4. Historical backtesting capabilities