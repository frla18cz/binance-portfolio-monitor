# Benchmark Metadata Migrations

This directory contains SQL migrations for improving benchmark metadata storage.

## Migrations

### 001_benchmark_rebalance_history.sql
Creates the `benchmark_rebalance_history` table to store complete history of all benchmark rebalancing operations with full audit trail.

Key features:
- Stores before/after state for each rebalance
- Includes prices at rebalance time
- Tracks validation errors
- Auto-populates account_name via trigger

### 002_benchmark_modifications.sql
Creates the `benchmark_modifications` table to track all benchmark adjustments due to deposits/withdrawals.

Key features:
- Records every deposit/withdrawal impact on benchmark
- Stores calculation details (50/50 split for deposits, proportional reduction for withdrawals)
- Links to original transactions
- Adds audit columns to benchmark_configs table

## How to Apply

### Option 1: Using MCP Supabase Tool
```python
# In Claude or through the API
mcp__supabase__apply_migration(
    project_id="axvqumsxlncbqzecjlxy",
    name="benchmark_rebalance_history",
    query=<contents of 001_benchmark_rebalance_history.sql>
)

mcp__supabase__apply_migration(
    project_id="axvqumsxlncbqzecjlxy", 
    name="benchmark_modifications",
    query=<contents of 002_benchmark_modifications.sql>
)
```

### Option 2: Direct SQL
1. Connect to your Supabase database
2. Run each SQL file in order
3. Verify tables were created successfully

### Option 3: Using the script
```bash
python scripts/apply_benchmark_migrations.py
```

## Post-Migration

After applying migrations:
1. New rebalances will automatically save history
2. New deposits/withdrawals will automatically save modification details
3. Use `scripts/validate_benchmark_consistency.py` to verify data integrity

## Benefits

- **Full Auditability**: Can reconstruct benchmark state at any point in time
- **Debugging**: See exact calculations for every change
- **Validation**: Can verify consistency between stored and calculated values
- **Analysis**: Track rebalancing patterns and effectiveness