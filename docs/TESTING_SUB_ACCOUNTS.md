# Sub-Account Transfer Testing Guide

This guide explains how to test the sub-account transfer detection and account management features.

## Prerequisites

1. Flask admin server running on port 8002
2. Master account and sub-account on Binance
3. Master account API credentials

## 1. Test Admin UI (Account Management)

### Create New Sub-Account
1. Navigate to http://localhost:8002/accounts
2. Click "Create New Account"
3. Fill in:
   - Account Name: descriptive name for the sub-account
   - API Key: sub-account's API key
   - API Secret: sub-account's API secret
   - Email: sub-account email (required for transfer detection)
   - Performance Fee Rate: default 0.5 (50%)
   - Check "This is a sub-account"
   - Master Account: select from dropdown (optional, for reference only)
   - Master API Key: enter master account's API key
   - Master API Secret: enter master account's API secret
4. Click "Create Account"

### Edit Existing Account
1. Click "Edit" button next to any account
2. Modify desired fields
3. Click "Update Account"
4. Verify changes are saved

### Delete Account
1. Click "Delete" button
2. Confirm deletion in popup
3. Type account name to double-confirm
4. Account and all related data will be permanently deleted

## 2. Test Sub-Account Transfer Detection

### Reset Account for Clean Test
```bash
# Reset sub-account data while preserving configuration
python scripts/reset_account_data.py --account "your_sub_account_name" --yes
```

### Run Manual Transfer Detection
```bash
# Run monitoring to detect transfers
python -m api.index
```

### Check Logs
Look for these log messages:
- `"using_master_credentials"` - confirms master API credentials are being used
- `"sub_transfers_recorded"` - confirms transfers were detected and saved

## 3. Test Transfer Between Accounts

### Perform Test Transfer
1. Log into Binance
2. Transfer small amount (e.g., 0.001 ETH) from master to sub-account
3. Wait 1-2 minutes for API to update
4. Run monitoring again: `python -m api.index`

### Verify in Database
```sql
-- Check for SUB_ transactions
SELECT 
    pt.transaction_id,
    pt.type,
    pt.amount,
    pt.timestamp,
    ba.account_name,
    pt.metadata
FROM processed_transactions pt
JOIN binance_accounts ba ON pt.account_id = ba.id
WHERE pt.type LIKE 'SUB_%'
ORDER BY pt.timestamp DESC
LIMIT 10;
```

Expected results:
- `SUB_WITHDRAWAL` from master account
- `SUB_DEPOSIT` to sub-account
- Metadata includes coin type, USD value, and price

## 4. Verify Benchmark Reaction

### Check NAV and Benchmark Values
```sql
-- Compare NAV and benchmark before/after transfer
SELECT 
    nh.timestamp,
    nh.nav,
    nh.benchmark_value,
    ba.account_name
FROM nav_history nh
JOIN binance_accounts ba ON nh.account_id = ba.id
WHERE ba.account_name IN ('YourMasterAccount', 'YourSubAccount')
ORDER BY nh.timestamp DESC
LIMIT 20;
```

Expected behavior:
- NAV changes reflect the transfer
- Benchmark value adjusts accordingly
- Both accounts show corresponding changes

## 5. Testing Checklist

### Admin UI
- [ ] Create new account (master and sub-account)
- [ ] Edit existing account
- [ ] Delete account with confirmation
- [ ] Master credentials save correctly
- [ ] Form validation works

### Transfer Detection
- [ ] Sub-account uses master credentials when provided
- [ ] Transfers appear as SUB_WITHDRAWAL/SUB_DEPOSIT
- [ ] USD values calculated correctly
- [ ] Metadata includes all required fields
- [ ] No duplicate transactions

### Benchmark Updates
- [ ] Benchmark value changes after transfers
- [ ] Changes proportional to transfer amount
- [ ] Both accounts affected correctly

## 6. Troubleshooting

### No Transfers Detected
1. Check master API credentials are correct
2. Verify sub-account email is set
3. Look for error messages in logs
4. Ensure transfer was completed on Binance

### Database Queries for Debugging
```sql
-- Check account configuration
SELECT account_name, is_sub_account, email, 
       master_account_id, master_api_key IS NOT NULL as has_master_key
FROM binance_accounts;

-- Check recent system logs
SELECT timestamp, category, operation, message, data
FROM system_logs
WHERE category IN ('transaction', 'api_call')
ORDER BY timestamp DESC
LIMIT 50;

-- Check benchmark modifications
SELECT * FROM benchmark_modifications
WHERE account_id IN (
    SELECT id FROM binance_accounts 
    WHERE account_name IN ('YourMasterAccount', 'YourSubAccount')
)
ORDER BY created_at DESC
LIMIT 10;
```

### Common Issues
1. **Empty response from sub-account API**: Master credentials incorrect or no permission
2. **Transfers not affecting benchmark**: Check if SUB_ transaction types are being processed
3. **Duplicate transactions**: Check unique constraint on (account_id, transaction_id)

## 7. Performance Considerations

- Transfer detection adds API calls, may slow down monitoring slightly
- First run after reset will process all historical transfers (up to 30 days)
- Subsequent runs only process new transfers

## Summary

The sub-account transfer system now:
1. Requires explicit master API credentials for each sub-account
2. Automatically detects transfers during regular monitoring
3. Properly updates NAV and benchmark values
4. Provides full CRUD operations through admin UI

This approach is simple, transparent, and flexible - no hidden magic or complex inheritance.