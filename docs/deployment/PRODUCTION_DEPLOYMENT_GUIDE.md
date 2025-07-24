# Production Deployment Guide - Binance Pay Transaction Detection

## Overview
This guide covers the deployment of Binance Pay transaction detection feature that enables monitoring of email/phone transfers.

## Pre-Deployment Checklist

### 1. Database Migration (REQUIRED)
**You must apply this migration in Supabase SQL editor before deployment:**

```sql
-- Add PAY_DEPOSIT and PAY_WITHDRAWAL to transaction_type enum
ALTER TABLE processed_transactions 
DROP CONSTRAINT IF EXISTS processed_transactions_transaction_type_check;

ALTER TABLE processed_transactions 
ADD CONSTRAINT processed_transactions_transaction_type_check 
CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL'));

-- Verify the constraint was added
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'processed_transactions'::regclass 
AND contype = 'c';
```

### 2. Configuration Verified
- ✅ Cron interval: 60 minutes (production setting)
- ✅ Test files excluded from deployment (.gitignore updated)
- ✅ All dependencies in requirements.txt (no version pinning)

## What's New

### Features Added
1. **Binance Pay API Integration**
   - Detects transfers via email and phone number
   - Captures transaction metadata (contact name, type, ID)
   - New transaction types: `PAY_DEPOSIT` and `PAY_WITHDRAWAL`

2. **Python-Binance Bug Workaround**
   - Created `api/binance_pay_helper.py` for direct API calls
   - Bypasses library bug with Pay API endpoint

3. **Enhanced Transaction Processing**
   - Processes both regular and Pay transactions
   - Preserves all transaction metadata in JSONB column
   - Automatic benchmark adjustments for Pay transactions

### Files Modified
- `api/index.py` - Added Pay transaction fetching and processing
- `api/binance_pay_helper.py` - New helper module for Pay API
- `config/settings.json` - Restored 60-minute interval
- `deployment/aws/run_forever.py` - Uses dynamic interval from settings
- `.gitignore` - Excludes test files from deployment
- `requirements.txt` - Updated to latest versions

## Deployment Steps

### AWS EC2 Deployment

1. **Apply Database Migration**
   - Go to Supabase Dashboard → SQL Editor
   - Run the migration SQL above
   - Verify constraint was added successfully

2. **Deploy Code**
   ```bash
   # On your local machine
   cd /path/to/binance_monitor_playground
   ./deployment/aws/deploy_simple.sh
   ```

3. **Restart Monitoring**
   ```bash
   # SSH to EC2 instance
   ssh -i your-key.pem ubuntu@your-ec2-ip
   
   # Stop current monitoring
   screen -S monitor -X quit
   
   # Start with new code
   cd ~/binance_monitor
   ./deployment/aws/start_monitor.sh
   ```

4. **Verify Deployment**
   ```bash
   # Check logs for Pay transactions
   screen -r monitor
   # Look for "pay_transaction_detected" entries
   
   # Check dashboard
   curl http://localhost:8000
   ```

### Vercel Deployment

1. **Apply Database Migration** (same as above)

2. **Deploy to Vercel**
   ```bash
   vercel --prod
   ```

3. **Verify Cron Job**
   - Check Vercel dashboard → Functions → Logs
   - Look for hourly executions
   - Verify Pay transactions are being detected

## Testing Pay Transactions

### How to Test
1. Make a small transfer (e.g., 5 USDC) via phone/email in Binance app
2. Wait for next monitoring cycle (runs hourly)
3. Check logs for "pay_transaction_detected" entries
4. Verify transaction appears in `processed_transactions` table

### Expected Log Output
```
[transaction] pay_transaction_detected: Pay PAY_WITHDRAWAL: 5.0 USDC - User-Name
```

## Monitoring & Troubleshooting

### Check System Logs
```sql
-- In Supabase SQL Editor
SELECT * FROM system_logs 
WHERE operation = 'pay_transaction_detected' 
ORDER BY timestamp DESC 
LIMIT 10;
```

### Verify Pay Transactions
```sql
-- Check processed Pay transactions
SELECT * FROM processed_transactions 
WHERE transaction_type IN ('PAY_DEPOSIT', 'PAY_WITHDRAWAL')
ORDER BY timestamp DESC;
```

### Common Issues

1. **"violates check constraint" error**
   - Solution: Apply the database migration

2. **Pay transactions not detected**
   - Check if user has Pay transaction history
   - Verify API keys have correct permissions
   - Check system_logs for "pay_api_error" entries

3. **Metadata not saved**
   - Ensure metadata column exists (JSONB type)
   - Check transaction processing logs

## Rollback Plan

If issues occur, you can rollback:

1. **Revert Code**
   ```bash
   git checkout main
   git reset --hard HEAD~1
   ./deployment/aws/deploy_simple.sh
   ```

2. **Keep Database Migration**
   - The migration is backward compatible
   - Old code will continue to work

## Success Criteria

Deployment is successful when:
- ✅ No errors in monitoring logs
- ✅ Pay transactions are being detected
- ✅ Transaction metadata is saved correctly
- ✅ Dashboard shows updated NAV values
- ✅ Benchmark adjustments work for Pay transactions

## Support

For issues:
1. Check system_logs table for errors
2. Review pay_api_error and pay_transaction_detected logs
3. Verify database migration was applied
4. Check binance_pay_helper.py logs

---

**Last Updated**: 2025-01-19
**Feature Branch**: fix-transaction-detection
**Production Ready**: Yes (after database migration)