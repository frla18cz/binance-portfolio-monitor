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