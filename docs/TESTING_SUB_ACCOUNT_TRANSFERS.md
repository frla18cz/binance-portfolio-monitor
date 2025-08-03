# Testing Guide for Sub-Account Transfers

This document provides a comprehensive testing strategy for the sub-account transfer functionality.

## Prerequisites

Before testing, ensure:
1. Master account has correct email in database
2. Sub-accounts have `is_sub_account = true`
3. Sub-accounts have `master_account_id` pointing to master
4. Sub-accounts have master API credentials stored (for transfer detection)

## Test Scenarios

### 1. Basic Transfer Test (Master → Sub-account)

**Setup**:
```bash
# Reset test accounts to clean state
python scripts/reset_account_data.py --account "Ondra(test)" --yes
python scripts/reset_account_data.py --account "ondra_osobni_sub_acc1" --yes
```

**Execute**:
1. Transfer 10 USDC from master to sub-account via Binance UI
2. Wait 1-2 minutes for transaction to confirm
3. Run monitoring: `python scripts/run_once.py`

**Verify**:
```sql
-- Check SUB_ transactions were created
SELECT 
    ba.account_name,
    pt.type,
    pt.amount,
    pt.timestamp,
    pt.metadata->>'coin' as coin
FROM processed_transactions pt
JOIN binance_accounts ba ON pt.account_id = ba.id
WHERE pt.type IN ('SUB_DEPOSIT', 'SUB_WITHDRAWAL')
AND pt.timestamp > NOW() - INTERVAL '1 hour'
ORDER BY pt.timestamp DESC;

-- Expected: 
-- 1. SUB_WITHDRAWAL for master account
-- 2. SUB_DEPOSIT for sub-account
```

### 2. Reverse Transfer Test (Sub-account → Master)

**Execute**:
1. Transfer 5 USDC from sub-account to master via Binance UI
2. Run monitoring: `python scripts/run_once.py`

**Verify**:
```sql
-- Check benchmark adjustments
SELECT 
    ba.account_name,
    bc.btc_units,
    bc.eth_units,
    bc.last_modification_type,
    bc.last_modification_amount
FROM binance_accounts ba
JOIN benchmark_configs bc ON bc.account_id = ba.id
WHERE ba.account_name IN ('Ondra(test)', 'ondra_osobni_sub_acc1');

-- Expected:
-- Master: last_modification_type = 'deposit', amount positive
-- Sub: last_modification_type = 'withdrawal', amount negative
```

### 3. Multiple Sub-accounts Test

**Setup**:
- Create additional sub-account
- Link to same master account
- Configure master API credentials

**Execute**:
1. Transfer from master to sub1: 10 USDC
2. Transfer from master to sub2: 15 USDC
3. Transfer from sub1 to sub2: 5 USDC
4. Run monitoring once

**Verify**:
```sql
-- All transfers should be recorded
SELECT COUNT(*) as transfer_count, 
       SUM(CASE WHEN type = 'SUB_DEPOSIT' THEN 1 ELSE 0 END) as deposits,
       SUM(CASE WHEN type = 'SUB_WITHDRAWAL' THEN 1 ELSE 0 END) as withdrawals
FROM processed_transactions
WHERE type LIKE 'SUB_%'
AND timestamp > NOW() - INTERVAL '1 hour';
```

### 4. Historical Transfer Test

**Purpose**: Verify that old transfers before initialization are not processed

**Setup**:
```sql
-- Set initialized_at to future time temporarily
UPDATE benchmark_configs 
SET initialized_at = NOW() + INTERVAL '1 hour'
WHERE account_id IN (
    SELECT id FROM binance_accounts 
    WHERE account_name IN ('Ondra(test)', 'ondra_osobni_sub_acc1')
);
```

**Execute**:
1. Run monitoring: `python scripts/run_once.py`

**Verify**:
- No new SUB_ transactions should be created
- Check logs for "Using initialized_at as start time"

**Cleanup**:
```sql
-- Reset initialized_at
UPDATE benchmark_configs 
SET initialized_at = NOW() - INTERVAL '1 day'
WHERE account_id IN (
    SELECT id FROM binance_accounts 
    WHERE account_name IN ('Ondra(test)', 'ondra_osobni_sub_acc1')
);
```

### 5. Duplicate Prevention Test

**Execute**:
1. Run monitoring twice in succession
2. `python scripts/run_once.py`
3. `python scripts/run_once.py`

**Verify**:
- No duplicate transactions created
- Check for "duplicate key" errors in logs

### 6. Benchmark Impact Test

**Execute**:
```python
# Test script to verify benchmark calculations
python scripts/validate_benchmark_consistency.py --account "Ondra(test)"
python scripts/validate_benchmark_consistency.py --account "ondra_osobni_sub_acc1"
```

**Verify**:
- No validation errors
- Benchmark values match expected calculations

## Automated Test Suite

Create and run this test script:

```python
#!/usr/bin/env python3
"""
Automated test suite for sub-account transfers
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
from utils.logger import get_logger

load_dotenv()

def test_sub_account_transfers():
    """Run comprehensive tests for sub-account transfers"""
    logger = get_logger()
    
    # Initialize Supabase client
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_ANON_KEY')
    )
    
    print("=== Sub-Account Transfer Test Suite ===\n")
    
    # Test 1: Check account configuration
    print("1. Testing account configuration...")
    accounts = supabase.table('binance_accounts').select('*').in_(
        'account_name', ['Ondra(test)', 'ondra_osobni_sub_acc1']
    ).execute()
    
    master = None
    sub = None
    
    for acc in accounts.data:
        if acc['is_sub_account']:
            sub = acc
        else:
            master = acc
    
    assert master is not None, "Master account not found"
    assert sub is not None, "Sub-account not found"
    assert master['email'], "Master account missing email"
    assert sub['email'], "Sub-account missing email"
    assert sub['master_account_id'] == master['id'], "Sub-account not linked to master"
    assert sub.get('master_api_key'), "Sub-account missing master API credentials"
    
    print("✓ Account configuration correct")
    
    # Test 2: Check recent transfers
    print("\n2. Testing recent transfers...")
    recent_transfers = supabase.table('processed_transactions').select('*').in_(
        'type', ['SUB_DEPOSIT', 'SUB_WITHDRAWAL']
    ).gte('timestamp', (datetime.now() - timedelta(hours=24)).isoformat()).execute()
    
    if recent_transfers.data:
        print(f"✓ Found {len(recent_transfers.data)} recent transfers")
        
        # Verify pairs
        deposits = [t for t in recent_transfers.data if t['type'] == 'SUB_DEPOSIT']
        withdrawals = [t for t in recent_transfers.data if t['type'] == 'SUB_WITHDRAWAL']
        
        print(f"  - Deposits: {len(deposits)}")
        print(f"  - Withdrawals: {len(withdrawals)}")
        
        # Each transfer should have a matching pair
        for deposit in deposits:
            # Find matching withdrawal
            matching = [w for w in withdrawals 
                       if abs((datetime.fromisoformat(w['timestamp'].replace('Z', '+00:00')) - 
                              datetime.fromisoformat(deposit['timestamp'].replace('Z', '+00:00'))).total_seconds()) < 60
                       and w['amount'] == deposit['amount']]
            if matching:
                print(f"  ✓ Matched pair: {deposit['amount']} {deposit['metadata'].get('coin', 'USD')}")
    else:
        print("⚠ No recent transfers found - create test transfer first")
    
    # Test 3: Check benchmark modifications
    print("\n3. Testing benchmark modifications...")
    mods = supabase.table('benchmark_modifications').select('*').gte(
        'modification_timestamp', (datetime.now() - timedelta(hours=24)).isoformat()
    ).execute()
    
    if mods.data:
        print(f"✓ Found {len(mods.data)} benchmark modifications")
        for mod in mods.data[-5:]:  # Show last 5
            print(f"  - {mod['modification_type']}: {mod['cashflow_amount']} at {mod['modification_timestamp']}")
    
    # Test 4: Verify benchmark consistency
    print("\n4. Testing benchmark consistency...")
    for acc in [master, sub]:
        config = supabase.table('benchmark_configs').select('*').eq(
            'account_id', acc['id']
        ).execute()
        
        if config.data:
            cfg = config.data[0]
            if cfg['btc_units'] and cfg['eth_units']:
                print(f"✓ {acc['account_name']}: BTC={float(cfg['btc_units']):.8f}, ETH={float(cfg['eth_units']):.8f}")
            else:
                print(f"⚠ {acc['account_name']}: Missing benchmark units")
    
    print("\n=== Test Suite Complete ===")

if __name__ == "__main__":
    test_sub_account_transfers()
```

Save as `scripts/test_sub_account_transfers.py`

## Performance Testing

### Load Test
```bash
# Monitor performance with multiple transfers
time python scripts/run_once.py

# Check processing time in logs
grep "Operation completed successfully" logs/monitor.log | tail -20
```

### Database Query Performance
```sql
-- Check index usage
EXPLAIN ANALYZE
SELECT * FROM processed_transactions
WHERE account_id = 'uuid-here'
AND transaction_id LIKE 'SUB_%'
ORDER BY timestamp DESC;
```

## Troubleshooting Common Issues

### 1. No Transfers Detected
- Verify email addresses match exactly (case-sensitive)
- Check master API permissions
- Ensure transfers are after initialized_at
- Run `test_master_transfers.py` to debug API

### 2. Only One Side Created
- Check both accounts are being processed
- Verify master account enters the else branch (not is_sub_account)
- Check debug logs for "master_account_detected"

### 3. Benchmark Not Updating
- Verify process_sub_transactions_for_benchmark is called
- Check for errors in adjust_benchmark_for_cashflow
- Validate prices are available

## Production Monitoring

Add these alerts:
1. **Missing Pairs**: SUB_DEPOSIT without matching SUB_WITHDRAWAL
2. **Processing Delays**: Transfers not detected within 5 minutes
3. **Benchmark Drift**: Large discrepancies in benchmark calculations

## Cleanup Scripts

```bash
# Remove test transfers
cat > scripts/cleanup_test_transfers.sql << 'EOF'
-- Delete test transfers (be careful!)
DELETE FROM processed_transactions
WHERE type IN ('SUB_DEPOSIT', 'SUB_WITHDRAWAL')
AND metadata->>'coin' = 'USDC'
AND amount IN ('5.0', '10.0', '15.0')
AND timestamp > NOW() - INTERVAL '1 day';

-- Reset benchmark to recalculate
UPDATE benchmark_configs
SET last_modification_type = NULL
WHERE account_id IN (
    SELECT id FROM binance_accounts 
    WHERE account_name IN ('Ondra(test)', 'ondra_osobni_sub_acc1')
);
EOF
```