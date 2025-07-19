# Binance Pay Transaction Detection Fix

## Problem Summary

The Binance Portfolio Monitor was not detecting withdrawals and deposits made through Binance Pay (email/phone transfers). This included:
- Transfers to phone numbers
- Transfers to email addresses
- All Binance Pay transactions

### Root Cause

The main issue was a bug in the `python-binance` library when calling the Binance Pay API endpoint `/sapi/v1/pay/transactions`. The library was incorrectly parsing the API response, resulting in a `KeyError: 'data'` error.

### Investigation Timeline

1. **Initial Discovery**: User made a 5 USDC test withdrawal to a phone number that wasn't detected
2. **Code Analysis**: Found that `fetch_new_transactions()` only handled regular deposits/withdrawals, not Pay transactions
3. **Implementation Attempt**: Added Pay API call using python-binance library
4. **Error Encountered**: `Failed to fetch pay transactions: 'data'`
5. **Root Cause Analysis**: Created multiple test scripts and discovered python-binance bug

## Technical Details

### Python-Binance Bug

The library's internal handling of the Pay API endpoint was flawed:
```python
# What python-binance was doing (simplified):
response = self._request('GET', 'sapi/v1/pay/transactions', True, data)
# The library expected a different response structure than what the API returns
```

### Actual API Response Structure
```json
{
    "code": "000000",
    "message": "success",
    "data": [
        {
            "orderType": "C2C",
            "transactionId": "123456789",
            "transactionTime": 1234567890000,
            "amount": "5.00000000",
            "currency": "USDC",
            "openUserId": "abc123",
            "walletType": 1,
            "payerInfo": {
                "name": "Test User",
                "type": "MOBILE",
                "accountId": "+420123456789"
            }
        }
    ],
    "success": true
}
```

## Solution

### 1. Created Helper Module

Since updating python-binance didn't fix the issue, we created `api/binance_pay_helper.py` that directly calls the Binance API using the `requests` library:

```python
def get_pay_transactions(api_key: str, api_secret: str, logger=None, account_id=None) -> List[Dict[str, Any]]:
    """
    Get Binance Pay transactions using direct API call.
    
    This is a workaround for python-binance bug with /sapi/v1/pay/transactions endpoint.
    """
    # Direct API call implementation
    # Creates HMAC signature and makes authenticated request
    # Properly handles the response structure
```

### 2. Updated Transaction Processing

Modified `api/index.py` to:
- Import and use the helper module instead of python-binance for Pay transactions
- Add new transaction types: `PAY_DEPOSIT` and `PAY_WITHDRAWAL`
- Process Pay transactions with metadata (contact info)

```python
# In fetch_new_transactions():
pay_txns = get_pay_transactions(
    account.api_key, 
    account.api_secret, 
    logger, 
    account.id
)

for pay_txn in pay_txns:
    # Determine if it's a deposit or withdrawal
    txn_type = 'PAY_DEPOSIT' if amount > 0 else 'PAY_WITHDRAWAL'
    
    # Extract metadata including contact info
    metadata = {
        'contact_name': payer_info.get('name'),
        'contact_type': payer_info.get('type'),  # EMAIL or MOBILE
        'contact_id': payer_info.get('accountId')  # email or phone
    }
```

### 3. Database Migration

Created migration to support new transaction types:
```sql
-- migrations/add_pay_transaction_types.sql
ALTER TABLE processed_transactions 
DROP CONSTRAINT IF EXISTS processed_transactions_transaction_type_check;

ALTER TABLE processed_transactions 
ADD CONSTRAINT processed_transactions_transaction_type_check 
CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL'));
```

## Implementation Results

After implementing the fix:
- ✅ Successfully detected all Pay transactions
- ✅ Found the 5 USDC test withdrawal to phone number
- ✅ Properly captured metadata (phone numbers, emails, names)
- ✅ Transactions saved to database with correct types

### Example Detected Transaction
```
📱 PAY_WITHDRAWAL: -5.00000000 USDC
   Contact: Test User (MOBILE: +420123456789)
   Transaction ID: TN_P6R3J3P6EBD3
   Time: 2025-01-18 12:30:45
```

## Files Modified

1. **api/index.py** - Updated transaction fetching and processing
2. **api/binance_pay_helper.py** - New helper module for Pay API calls
3. **migrations/add_pay_transaction_types.sql** - Database schema update
4. **deployment/aws/run_forever.py** - Fixed to use settings.json interval
5. **config/settings.json** - Changed cron interval for testing

## Testing

Created comprehensive test suite:
- `test_pay_transactions.py` - Unit tests for Pay transaction processing
- `test_mixed_transactions.py` - Integration tests for all transaction types
- `test_pay_api_structure.py` - API response structure analysis

## Deployment Steps

1. Apply database migration in Supabase SQL editor
2. Deploy updated code with helper module
3. Monitor logs for successful Pay transaction detection

## Future Improvements

1. Consider contributing fix to python-binance library
2. Add more detailed transaction categorization
3. Implement webhook support for real-time detection

## Conclusion

The issue was successfully resolved by bypassing the python-binance library bug and implementing direct API calls. The system now properly detects and processes all Binance Pay transactions, including email and phone transfers, with full metadata preservation.