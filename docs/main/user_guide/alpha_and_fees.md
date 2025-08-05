# Alpha Calculation and Fee Management Guide

## Overview

This system tracks portfolio performance using Time-Weighted Returns (TWR) to calculate alpha (outperformance vs benchmark) and manages performance fees with High Water Mark tracking.

## Key Concepts

### Time-Weighted Return (TWR)
TWR eliminates the impact of deposits and withdrawals on performance measurement. It shows the true performance of your trading strategy by calculating returns for each period and then compounding them.

### Alpha
Alpha = Portfolio TWR - Benchmark TWR

- **Positive Alpha**: Your trading outperforms the 50/50 BTC/ETH benchmark
- **Negative Alpha**: You would have been better off just holding BTC/ETH

### High Water Mark (HWM)
The highest NAV achieved, adjusted for all deposits and withdrawals. Performance fees are only charged on new profits above the HWM.

## Database Components

### Tables
- `fee_tracking` - Stores monthly fee calculations
- `binance_accounts.performance_fee_rate` - Fee rate per account (default 50%)

### Views
- `nav_with_cashflows` - NAV data enriched with transaction information
- `period_returns` - Period-by-period returns for TWR calculation
- `hwm_history` - High Water Mark tracking with cashflow adjustments

### Functions
- `calculate_twr_period(account_id, start_date, end_date)` - Calculate TWR for any period
- `calculate_monthly_fees(account_id, month, fee_rate)` - Calculate fees for a month

## Usage Examples

### 1. Setting Fee Rates

```sql
-- Set 50% performance fee for an account
UPDATE binance_accounts 
SET performance_fee_rate = 0.50 
WHERE account_name = 'Habitanti';

-- Check current fee rates
SELECT account_name, performance_fee_rate 
FROM binance_accounts;
```

### 2. Calculating Performance

```sql
-- Calculate TWR and alpha for last 30 days
SELECT 
  ba.account_name,
  twr.portfolio_twr || '%' as portfolio_return,
  twr.benchmark_twr || '%' as benchmark_return,
  twr.alpha_twr || '%' as alpha,
  twr.total_deposits,
  twr.total_withdrawals
FROM binance_accounts ba
CROSS JOIN LATERAL calculate_twr_period(
  ba.id,
  NOW() - INTERVAL '30 days',
  NOW()
) twr
WHERE ba.account_name = 'Habitanti';
```

### 3. Monthly Fee Calculation

```sql
-- Calculate fees for July 2025
SELECT 
  ba.account_name,
  fees.period_start,
  fees.period_end,
  fees.ending_nav,
  fees.ending_hwm,
  fees.portfolio_twr || '%' as portfolio_return,
  fees.benchmark_twr || '%' as benchmark_return,
  fees.alpha_twr || '%' as alpha,
  fees.performance_fee
FROM binance_accounts ba
CROSS JOIN LATERAL calculate_monthly_fees(
  ba.id,
  '2025-07-01'::DATE
) fees
WHERE ba.account_name = 'Habitanti';
```

### 4. Manual Fee Calculation Script

```bash
# Show current configuration
python scripts/run_fee_calculation.py --show-config

# List all accounts with their fee rates
python scripts/run_fee_calculation.py --list-accounts

# Calculate fees for specific month
python scripts/run_fee_calculation.py --month 2025-07

# Calculate fees for specific account
python scripts/run_fee_calculation.py --account [UUID] --month 2025-07

# Calculate last 3 months
python scripts/run_fee_calculation.py --last-n-months 3
```

### 5. Automated Fee Calculation

Add to crontab for monthly calculation:
```bash
# Run on 1st of each month at midnight UTC
0 0 1 * * cd /path/to/project && python scripts/run_fee_calculation.py

# Or use the API endpoint
0 0 1 * * curl https://your-domain/api/calculate_fees
```

### 6. Fee Collection Process

When it's time to collect fees:

1. **Calculate fees** for the period
2. **Review the calculation** to ensure accuracy
3. **Withdraw the fee amount** from Binance
4. **Record the withdrawal** in the database:

```sql
-- Record fee withdrawal
INSERT INTO processed_transactions (
  account_id,
  transaction_id,
  type,
  amount,
  timestamp,
  status,
  metadata
) VALUES (
  'account-uuid',
  'WD_' || gen_random_uuid(),
  'FEE_WITHDRAWAL',
  1000.00,  -- Fee amount
  NOW(),
  'SUCCESS',
  '{"note": "Performance fee for July 2025", "period": "2025-07"}'::jsonb
);

-- Update fee tracking record
UPDATE fee_tracking 
SET status = 'COLLECTED',
    collected_at = NOW(),
    collection_tx_id = 'withdrawal-tx-id'
WHERE account_id = 'account-uuid' 
AND period_start = '2025-07-01';
```

## API Endpoints

### Get Alpha Metrics
```bash
curl https://your-domain/api/dashboard/alpha-metrics?account_id=xxx
```

Response:
```json
{
  "current_month": {
    "portfolio_twr": -11.06,
    "benchmark_twr": 5.32,
    "alpha": -16.38,
    "nav": 364527.11,
    "hwm": 410943.84
  },
  "ytd": {
    "portfolio_twr": -15.23,
    "benchmark_twr": 12.45,
    "alpha": -27.68
  }
}
```

### Get Fee Summary
```bash
curl https://your-domain/api/dashboard/fees?account_id=xxx
```

Response:
```json
{
  "pending_fees": [
    {
      "period": "2025-06",
      "amount": 5000.00,
      "status": "ACCRUED"
    }
  ],
  "total_pending": 5000.00,
  "collected_ytd": 15000.00
}
```

## Performance Fee Rules

Performance fees are charged only when **BOTH** conditions are met:
1. **NAV > HWM**: Portfolio reaches new highs
2. **Alpha > 0**: Portfolio outperforms the benchmark

Formula:
```
Performance Fee = (Ending NAV - Starting HWM) × Fee Rate
```

Example:
- Starting HWM: $100,000
- Ending NAV: $110,000
- Alpha: +5%
- Fee Rate: 50%
- Performance Fee: ($110,000 - $100,000) × 0.50 = $5,000

## Monthly Reporting

Generate monthly investor reports:

```sql
-- Comprehensive monthly report
WITH monthly_performance AS (
  SELECT 
    ba.account_name,
    f.period_start,
    f.starting_nav,
    f.ending_nav,
    f.ending_nav - f.starting_nav as nav_change,
    f.portfolio_twr,
    f.benchmark_twr,
    f.alpha_twr as alpha,
    f.performance_fee,
    f.total_deposits,
    f.total_withdrawals
  FROM binance_accounts ba
  CROSS JOIN LATERAL calculate_monthly_fees(ba.id, '2025-07-01'::DATE) f
)
SELECT 
  account_name,
  TO_CHAR(period_start, 'Month YYYY') as period,
  TO_CHAR(starting_nav, '$999,999,999.99') as starting_nav,
  TO_CHAR(ending_nav, '$999,999,999.99') as ending_nav,
  TO_CHAR(nav_change, '$999,999,999.99') as nav_change,
  portfolio_twr || '%' as portfolio_return,
  benchmark_twr || '%' as benchmark_return,
  alpha || '%' as alpha,
  TO_CHAR(performance_fee, '$999,999,999.99') as performance_fee
FROM monthly_performance
ORDER BY account_name;
```

## Troubleshooting

### No HWM Data
If HWM shows as NULL, ensure you have NAV history:
```sql
SELECT COUNT(*) FROM nav_history WHERE account_id = 'your-account-id';
```

### TWR Calculation Issues
Check for period returns:
```sql
SELECT * FROM period_returns 
WHERE account_id = 'your-account-id' 
ORDER BY timestamp DESC 
LIMIT 10;
```

### Fee Not Calculating
Verify both conditions:
```sql
SELECT 
  actual_nav as current_nav,
  hwm,
  actual_nav > hwm as above_hwm
FROM hwm_history 
WHERE account_id = 'your-account-id'
ORDER BY timestamp DESC 
LIMIT 1;
```

## Best Practices

1. **Regular Monitoring**: Check alpha weekly to understand performance
2. **Fee Review**: Always review fee calculations before collection
3. **Transaction Recording**: Immediately record fee withdrawals
4. **Monthly Reports**: Generate reports on the 1st of each month
5. **Backup Calculations**: Keep spreadsheet backup of fee calculations

## Configuration Reference

### Settings.json
```json
{
  "fee_management": {
    "default_performance_fee_rate": 0.50,  // 50% default
    "calculation_schedule": "monthly",     // When to calculate
    "calculation_day": 1,                  // Day of month
    "calculation_hour": 0,                 // Hour (UTC)
    "test_mode": {
      "enabled": false,                    // Enable for testing
      "interval_minutes": 60               // Test interval
    }
  }
}
```

### Per-Account Fee Rates
```sql
-- View all fee rates
SELECT 
  account_name,
  performance_fee_rate,
  performance_fee_rate * 100 || '%' as fee_percentage
FROM binance_accounts
ORDER BY account_name;
```