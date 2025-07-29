# Deposit Processing Utilities

This document describes the utility scripts for managing cryptocurrency deposits in the Binance Portfolio Monitor.

## Overview

The system now supports deposits in any cryptocurrency (not just BTC/ETH) with automatic USD conversion and comprehensive metadata storage. Several utility scripts help test, debug, and fix deposit processing issues.

## Utility Scripts

### 1. test_coin_pricing.py
Tests the coin pricing functionality for various cryptocurrencies.

**Usage:**
```bash
python scripts/test_coin_pricing.py
```

**What it does:**
- Tests pricing for common coins (BTC, ETH, BNB, SOL, etc.)
- Verifies both direct USDT pricing and BTC routing fallback
- Shows which coins can be priced and which cannot
- Validates the pricing mechanism works correctly

**Example output:**
```
Testing coin pricing functionality...
BTC: ✅ $116,500.00 (direct)
ETH: ✅ $3,850.00 (direct)
SOL: ✅ $185.50 (direct)
UNKNOWN: ❌ Price not available
```

### 2. simulate_deposit_flow.py
Simulates how different cryptocurrency deposits would be processed without modifying the database.

**Usage:**
```bash
python scripts/simulate_deposit_flow.py
```

**What it does:**
- Simulates processing of various coin deposits
- Shows metadata that would be stored
- Demonstrates cashflow handling for missing prices
- Calculates success rate for price determination

**Example scenarios tested:**
- BTC deposit: 0.01 BTC
- ETH deposit: 0.1 ETH
- USDC deposit: 1000 USDC
- SOL deposit: 5 SOL
- Unknown coin: Tests price_missing flag

### 3. fix_deposit_metadata.py
Fixes metadata for specific historical deposits that were processed before multi-coin support.

**Usage:**
```bash
python scripts/fix_deposit_metadata.py
```

**What it does:**
- Targets specific transaction IDs
- Adds proper metadata structure
- Uses historical prices for accuracy
- Validates updates after completion

**When to use:**
- After upgrading to multi-coin support
- When specific deposits lack metadata
- For historical data cleanup

### 4. update_missing_prices.py
Updates all deposits that have missing price information.

**Usage:**
```bash
python scripts/update_missing_prices.py
```

**What it does:**
- Finds all deposits with `price_missing: true`
- Attempts to fetch current prices
- Updates metadata with new price information
- Tracks which deposits were successfully updated

**Features:**
- Processes all deposits with missing prices
- Uses current market prices
- Adds audit trail (price_updated_at, price_updated_by)
- Shows summary of updates

## Deposit Processing Flow

### 1. New Deposit Detection
When a new deposit is detected from Binance API:
```python
# api/index.py
def process_deposits():
    deposits = client.get_deposit_history()
    for deposit in deposits:
        # Check if already processed
        if not is_processed(deposit):
            process_new_deposit(deposit)
```

### 2. USD Value Calculation
The system uses a fallback mechanism for price determination:
```python
def get_coin_usd_value(client, coin, amount, btc_price=None):
    # Try 1: Direct USDT pair
    price = get_price(f"{coin}USDT")
    if price:
        return amount * price, price, "direct"
    
    # Try 2: Via BTC routing
    coin_btc_price = get_price(f"{coin}BTC")
    if coin_btc_price and btc_price:
        coin_usd = coin_btc_price * btc_price
        return amount * coin_usd, coin_usd, "via_btc"
    
    # Try 3: Mark as missing
    return None, None, None
```

### 3. Metadata Storage
Each deposit stores comprehensive metadata:
```json
{
  "coin": "SOL",
  "network": "SOL",
  "usd_value": 925.50,
  "coin_price": 185.10,
  "price_source": "direct",
  "price_missing": false,
  "tx_id": "abc123..."
}
```

### 4. Cashflow Impact
- Deposits with USD values: Added to NAV calculations
- Deposits without prices: Stored but excluded from cashflow
- Can be retroactively updated when prices become available

## Common Operations

### Debug a specific deposit
```sql
-- Find deposit details
SELECT * FROM processed_transactions 
WHERE transaction_id = 'DEP_xxx' 
AND type = 'DEPOSIT';

-- Check metadata
SELECT 
  transaction_id,
  amount,
  metadata->>'coin' as coin,
  metadata->>'usd_value' as usd_value,
  metadata->>'price_missing' as price_missing
FROM processed_transactions
WHERE type = 'DEPOSIT'
AND account_id = 'xxx';
```

### Find deposits with missing prices
```sql
SELECT COUNT(*) FROM processed_transactions
WHERE type = 'DEPOSIT'
AND metadata->>'price_missing' = 'true';
```

### Update a single deposit manually
```python
# Use update_missing_prices.py or:
from utils.database_manager import get_supabase_client
from api.index import get_coin_usd_value

supabase = get_supabase_client()
# ... fetch price and update metadata
```

## Troubleshooting

### Issue: Deposit shows no USD value
**Solution:** Run `update_missing_prices.py` to attempt price fetch

### Issue: Unknown coin deposit
**Expected behavior:** Stored with `price_missing: true`, excluded from NAV

### Issue: Wrong price used
**Solution:** Check `price_source` in metadata, verify market prices at deposit time

### Issue: Duplicate deposits
**Prevention:** Unique constraint on (account_id, transaction_id)

## Best Practices

1. **Regular Updates**: Run `update_missing_prices.py` periodically for new coin support
2. **Testing**: Use `simulate_deposit_flow.py` before processing new coin types
3. **Monitoring**: Check for deposits with `price_missing: true` regularly
4. **Historical Data**: Use `fix_deposit_metadata.py` for specific historical fixes

## Adding Support for New Coins

The system automatically supports any coin that:
1. Has a USDT trading pair on Binance, OR
2. Has a BTC trading pair (for BTC routing)

No code changes needed - the fallback mechanism handles new coins automatically.