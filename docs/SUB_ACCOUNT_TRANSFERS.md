# Sub-Account Transfer Detection

This document provides technical details about how sub-account transfers are detected and processed in the Binance Portfolio Monitor.

## Overview

Sub-account transfers are internal movements of funds between a master account and its sub-accounts on Binance. These transfers are not visible through the standard deposit/withdrawal API endpoints and require special handling.

## Implementation Details

### API Method

We use the python-binance library's `get_sub_account_transfer_history()` method:

```python
# For incoming transfers to sub-account
to_transfers = client.get_sub_account_transfer_history(
    toEmail=account['email'],
    startTime=start_time,
    endTime=end_time
)

# For outgoing transfers from sub-account
from_transfers = client.get_sub_account_transfer_history(
    fromEmail=account['email'],
    startTime=start_time,
    endTime=end_time
)
```

### Credential Usage

The key aspect of our implementation is the proper use of API credentials:

1. **Sub-accounts use their own API keys** for all operations:
   - Fetching NAV (Net Asset Value)
   - Processing regular deposits/withdrawals
   - Getting account balances
   - All other API operations

2. **Sub-accounts use master account API keys** ONLY for:
   - Detecting sub-account transfers via `get_sub_account_transfer_history()`

This is handled in `process_account_transfers()` function:

```python
if account.get('is_sub_account') and account.get('master_api_key') and account.get('master_api_secret'):
    # Use master credentials for sub-account transfer detection
    transfer_client = BinanceClient(account['master_api_key'], account['master_api_secret'])
else:
    # Use own credentials (for master accounts)
    transfer_client = binance_client
```

### API Response Format

The Binance API returns transfers in this format:

```json
{
  "from": "master@email.com",
  "to": "subaccount@email.com",
  "asset": "USDC",
  "qty": "100.00000000",
  "time": 1754066466000,
  "status": "SUCCESS",
  "tranId": 281790493303
}
```

Note the field names:
- `qty` instead of `amount`
- `from`/`to` instead of `fromEmail`/`toEmail`
- `asset` for the cryptocurrency symbol
- `tranId` for the unique transaction ID

### Database Storage

Transfers are stored in the `processed_transactions` table with:
- `type`: `SUB_DEPOSIT` or `SUB_WITHDRAWAL`
- `transaction_id`: Prefixed with `SUB_` (e.g., `SUB_281790493303`)
- `amount`: USD value of the transfer
- `metadata`: Contains additional details:
  ```json
  {
    "coin": "USDC",
    "from_email": "master@email.com",
    "to_email": "subaccount@email.com",
    "direction": "incoming",
    "transfer_type": 1,
    "network": "INTERNAL",
    "usd_value": 100.0,
    "coin_price": 1.0,
    "price_source": "stablecoin"
  }
  ```

### USD Conversion

All transfers are automatically converted to USD using the `get_coin_usd_value()` function:
- Stablecoins (USDT, USDC, etc.) = 1:1 USD
- Other coins: Try direct USDT pair first, then via BTC if needed
- If price unavailable: Store with `price_missing: true`

## Configuration

### Database Fields

In the `binance_accounts` table:
- `email`: Required for identifying transfers
- `is_sub_account`: Boolean flag
- `master_api_key`: Master account's API key (for sub-accounts only)
- `master_api_secret`: Master account's API secret (for sub-accounts only)

### Setting Up Sub-Account Transfer Detection

1. **Via Web Admin** (recommended):
   - Navigate to Config Admin → Account Management
   - Edit the sub-account
   - Enter master API credentials in the designated fields

2. **Via SQL**:
   ```sql
   UPDATE binance_accounts 
   SET 
     master_api_key = 'master_key_here',
     master_api_secret = 'master_secret_here'
   WHERE account_name = 'your_sub_account';
   ```

## Testing

To test sub-account transfer detection:

```python
# Run a single monitoring cycle
python -m api.index

# Check the logs
SELECT * FROM system_logs 
WHERE category = 'transaction' 
AND event_type LIKE '%sub_%'
ORDER BY timestamp DESC;

# Check recorded transfers
SELECT * FROM processed_transactions 
WHERE type IN ('SUB_DEPOSIT', 'SUB_WITHDRAWAL')
ORDER BY timestamp DESC;
```

## Troubleshooting

### Common Issues

1. **No transfers detected**:
   - Verify email address matches exactly (case-sensitive)
   - Check master credentials are correct
   - Ensure the account is marked as `is_sub_account = true`

2. **Authentication errors**:
   - Master API key must have "Enable Sub-Account" permission
   - API key must not be IP-restricted (or include your server IP)

3. **Missing USD values**:
   - Check if the coin has a trading pair on Binance
   - Verify price fetching is working (`test_coin_pricing.py`)

### Debug Queries

```sql
-- Check account configuration
SELECT account_name, email, is_sub_account, 
       master_api_key IS NOT NULL as has_master_key
FROM binance_accounts;

-- Recent transfer detection attempts
SELECT * FROM system_logs 
WHERE event_type IN ('using_master_credentials', 'sub_transfer_detection_failed')
ORDER BY timestamp DESC LIMIT 10;

-- Successful transfers
SELECT 
  pt.type,
  pt.amount,
  pt.timestamp,
  pt.metadata->>'coin' as coin,
  pt.metadata->>'from_email' as from_email,
  pt.metadata->>'to_email' as to_email
FROM processed_transactions pt
WHERE pt.type LIKE 'SUB_%'
ORDER BY pt.timestamp DESC;
```

## Important Notes

- Sub-account transfers are processed during each monitoring cycle
- Only transfers after the last processed timestamp are fetched
- The system prevents duplicate processing using unique constraints
- Transfer detection requires network access to Binance API
- All transfers affect the benchmark calculation automatically
- **Master accounts process ALL transfers but only save those involving them**
- **Both SUB_DEPOSIT and SUB_WITHDRAWAL are created for each transfer**

## Known Issues Fixed

### Master Account Not Creating SUB_DEPOSIT (Fixed)

**Problem**: Master accounts were not creating SUB_DEPOSIT transactions when receiving transfers from sub-accounts.

**Root Cause**: The code was adding ALL transfers from the API instead of filtering only those involving the master account.

**Fix Applied**: In `api/index.py`, the master account transfer processing now:
1. Fetches all transfers from the API
2. Filters only transfers where master account is sender OR receiver
3. Creates appropriate SUB_DEPOSIT/SUB_WITHDRAWAL based on direction

```python
# Fixed code in process_account_transfers()
if transfers:
    for transfer in transfers:
        from_email = transfer.get('from', '').lower()
        to_email = transfer.get('to', '').lower()
        master_email = account['email'].lower()
        
        # Only process transfers involving this master account
        if from_email == master_email or to_email == master_email:
            if from_email == master_email:
                transfer['direction'] = 'outgoing'
                transfer['type'] = 'WITHDRAWAL'
            else:
                transfer['direction'] = 'incoming'
                transfer['type'] = 'DEPOSIT'
            all_transfers.append(transfer)
```

## Known Issues Fixed (Update 2025-08-03)

### Benchmark Value Not Updating After SUB Transactions

**Problem**: After processing SUB_WITHDRAWAL/SUB_DEPOSIT transactions, the benchmark value in nav_history was not immediately reflecting the changes.

**Root Cause**: The order of operations in `process_single_account` was calculating and saving benchmark_value before processing SUB transactions.

**Fix Applied**: In `api/index.py`, we now re-fetch the latest benchmark_configs after all transactions are processed:

```python
# Re-fetch the latest config after all modifications to ensure we have the most up-to-date BTC/ETH units
config_result = db_client.table('benchmark_configs').select('*').eq('account_id', account_id).execute()
if config_result.data:
    config = config_result.data[0]
    logger.debug(LogCategory.BENCHMARK, "config_refreshed", 
                f"Refreshed config after all modifications - BTC: {config.get('btc_units')}, ETH: {config.get('eth_units')}",
                account_id=account_id, account_name=account_name)
```

This ensures the benchmark_value calculation always uses the most current BTC/ETH units after all cashflow adjustments.

## Known Issues Fixed (Update 2025-08-03 #2)

### SUB Transaction Detection After Account Reset

**Problem**: After account reset, SUB transfers were not detected because the system was using timestamps from deleted transactions.

**Root Cause**: The query for last processed SUB transaction returned timestamps from before the reset, causing new transfers to be skipped.

**Fix Applied**: In `api/index.py`, added verification that the last processed transaction actually exists:

```python
if last_result.data:
    # Verify the transaction actually exists (not deleted during reset)
    verify_result = db_client.table('processed_transactions').select('id').eq(
        'account_id', account_id
    ).eq('timestamp', last_result.data[0]['timestamp']).execute()
    
    if verify_result.data:
        # Transaction exists, use its timestamp
        last_timestamp = datetime.fromisoformat(last_result.data[0]['timestamp'].replace('Z', '+00:00'))
        start_time = int((last_timestamp + timedelta(minutes=1)).timestamp() * 1000)
    else:
        # Transaction doesn't exist (was deleted), fall back to initialized_at
        if config.get('initialized_at'):
            initialized_dt = datetime.fromisoformat(config['initialized_at'].replace('Z', '+00:00'))
            start_time = int(initialized_dt.timestamp() * 1000)
```

This ensures that after account reset, transfer detection starts from the initialization time rather than from non-existent transactions.

## AWS Deployment

### Production Setup

1. **Environment Variables**: Ensure master account API keys are set in production
   ```bash
   # Add to .env file on AWS instance
   MASTER_API_KEY=your_master_api_key
   MASTER_API_SECRET=your_master_api_secret
   ```

2. **Database Configuration**: Update sub-accounts with master credentials
   ```sql
   -- Run on production database
   UPDATE binance_accounts 
   SET 
     master_api_key = 'master_key_here',
     master_api_secret = 'master_secret_here'
   WHERE is_sub_account = true;
   ```

### Deployment Steps

```bash
# Deploy to AWS
cd deployment/aws
./deploy.sh

# SSH to instance
ssh ubuntu@your-instance-ip

# Monitor transfer processing
tail -f /home/ubuntu/logs/continuous_runner.log | grep -E "(SUB_|transfer)"

# Check for processed transfers
cd /home/ubuntu/binance_monitor_playground
python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
result = client.table('processed_transactions').select('*').in_('type', ['SUB_DEPOSIT', 'SUB_WITHDRAWAL']).order('timestamp', desc=True).limit(10).execute()
for t in result.data:
    print(f\"{t['timestamp']} | {t['type']} | {t['amount']} USD | {t['metadata'].get('coin', 'N/A')}\")
"
```

### Manual Testing on Production

```bash
# One-time execution for testing
cd /home/ubuntu/binance_monitor_playground
python scripts/run_once.py

# Check specific account transfers
python scripts/detect_sub_transfers.py
```

### Monitoring in Production

1. **Automatic Processing**: Sub-account transfers are detected during hourly monitoring runs
2. **Log Monitoring**: Check `/home/ubuntu/logs/continuous_runner.log` for:
   - "Using master credentials for sub-account"
   - "Found X sub-account transfers"
   - "Created SUB_DEPOSIT/SUB_WITHDRAWAL"

3. **Database Queries**:
   ```sql
   -- Recent sub-account transfers
   SELECT 
     ba.account_name,
     pt.type,
     pt.amount,
     pt.timestamp,
     pt.metadata->>'coin' as coin
   FROM processed_transactions pt
   JOIN binance_accounts ba ON pt.account_id = ba.id
   WHERE pt.type IN ('SUB_DEPOSIT', 'SUB_WITHDRAWAL')
   ORDER BY pt.timestamp DESC
   LIMIT 20;
   
   -- Check transfer processing status
   SELECT 
     account_name,
     last_transfer_check,
     initialized_at
   FROM binance_accounts
   WHERE is_sub_account = true
   OR id IN (SELECT DISTINCT master_account_id FROM binance_accounts WHERE master_account_id IS NOT NULL);
   ```

### Performance Considerations

- **API Calls**: Transfer detection adds 1-2 API calls per master account per monitoring cycle
- **Processing Time**: Minimal impact (~1-2 seconds per account with transfers)
- **Rate Limits**: Binance allows 1200 requests/minute, transfer detection uses <5 requests
- **Optimization**: Only accounts with sub-account relationships are checked

### Troubleshooting Production Issues

1. **No transfers detected**:
   ```bash
   # Check account configuration
   python -c "
   from utils import load_config
   config = load_config()
   print('Accounts with sub-account flags:')
   for acc in config['accounts']:
       if acc.get('is_sub_account') or acc.get('master_api_key'):
           print(f\"  {acc['account_name']}: sub={acc.get('is_sub_account')}, has_master={bool(acc.get('master_api_key'))}\")
   "
   ```

2. **API Authentication Errors**:
   - Check CloudWatch logs for API error messages
   - Verify master API key permissions in Binance
   - Ensure API keys are not IP-restricted

3. **Performance Issues**:
   - Monitor execution time in logs
   - Consider adjusting monitoring interval if needed
   - Check database query performance