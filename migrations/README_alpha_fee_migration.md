# Alpha Calculation and Fee Management Migration

## Overview

This migration adds support for:
- Time-Weighted Return (TWR) calculation
- Alpha tracking (portfolio performance vs benchmark)
- High Water Mark (HWM) tracking
- Fee management (management and performance fees)
- Monthly fee accruals and collections

## Migration Files

1. `add_alpha_and_fee_tracking.sql` - Main migration file

## How to Apply

### Option 1: Using Supabase Dashboard

1. Open your Supabase project dashboard
2. Go to SQL Editor
3. Copy the entire contents of `add_alpha_and_fee_tracking.sql`
4. Paste and run the migration
5. Check for any errors in the output

### Option 2: Using psql

```bash
psql -h [your-supabase-host] -U postgres -d postgres -f migrations/add_alpha_and_fee_tracking.sql
```

### Option 3: Using Supabase CLI

```bash
supabase db push --file migrations/add_alpha_and_fee_tracking.sql
```

## What Gets Created

### New Tables
- `fee_tracking` - Stores monthly fee calculations and collection status

### New Views
- `nav_with_cashflows` - NAV history enriched with transaction data
- `period_returns` - Calculates period returns for TWR
- `hwm_history` - Tracks High Water Mark adjusted for deposits/withdrawals

### New Functions
- `calculate_twr_period()` - Calculates Time-Weighted Returns for any period
- `calculate_monthly_fees()` - Calculates management and performance fees

### Modified Tables
- `processed_transactions` - Added `FEE_WITHDRAWAL` type

## Post-Migration Steps

1. **Run Additional Migrations**
   ```sql
   -- Add performance_fee_rate to accounts
   \i migrations/add_performance_fee_rate_to_accounts.sql
   ```

2. **Verify Migration Success**
   ```sql
   -- Check if fee_tracking table exists
   SELECT * FROM fee_tracking LIMIT 1;
   
   -- Check if views were created
   SELECT * FROM nav_with_cashflows LIMIT 1;
   
   -- Test TWR calculation
   SELECT * FROM calculate_twr_period(
     (SELECT id FROM binance_accounts LIMIT 1),
     NOW() - INTERVAL '30 days',
     NOW()
   );
   ```

3. **Configure Fee Rates per Account**
   ```sql
   -- Update fee rate for specific account (e.g., 50%)
   UPDATE binance_accounts 
   SET performance_fee_rate = 0.50 
   WHERE account_name = 'YourAccountName';
   ```

4. **Set Up Fee Calculation Schedule**
   
   Edit `config/settings.json`:
   ```json
   "fee_management": {
     "default_performance_fee_rate": 0.50,    // Default 50%
     "calculation_schedule": "monthly",       // or "daily", "hourly" for testing
     "calculation_day": 1,                    // 1st of month
     "calculation_hour": 0,                   // Midnight UTC
     "test_mode": {
       "enabled": false,                      // Set true for testing
       "interval_minutes": 60
     }
   }
   ```

5. **Set Up Cron Job**
   - For production: Run on schedule based on config
   - Endpoint: `/api/calculate_fees`
   - Manual run: `python scripts/run_fee_calculation.py`
   
   Example cron entries:
   ```bash
   # Monthly (1st of month at midnight UTC)
   0 0 1 * * curl https://your-domain/api/calculate_fees
   
   # Hourly (for testing)
   0 * * * * curl https://your-domain/api/calculate_fees
   ```

6. **Manual Fee Calculation Options**
   ```bash
   # Show configuration
   python scripts/run_fee_calculation.py --show-config
   
   # List all accounts with fee rates
   python scripts/run_fee_calculation.py --list-accounts
   
   # Calculate for specific month
   python scripts/run_fee_calculation.py --month 2025-06
   
   # Calculate for specific account
   python scripts/run_fee_calculation.py --account [UUID]
   
   # Calculate last 3 months
   python scripts/run_fee_calculation.py --last-n-months 3
   ```

7. **Update Dashboard**
   - New endpoints available:
     - `/api/dashboard/fees` - Fee tracking data
     - `/api/dashboard/alpha-metrics` - TWR and alpha metrics

## Fee Structure

- **Performance Fee**: Configurable per account (default 50%)
- **No Management Fee**
- **Calculation**: Only when NAV > HWM AND alpha > 0

## How It Works

1. **TWR Calculation**: Returns are calculated using Time-Weighted methodology to eliminate the impact of deposits/withdrawals
2. **HWM Tracking**: Historical NAVs are adjusted for cashflows to maintain consistent High Water Mark
3. **Fee Accrual**: Fees are calculated monthly but not automatically collected
4. **Fee Collection**: When fees are withdrawn, mark them as `FEE_WITHDRAWAL` type

## Rollback

If needed, you can rollback with:

```sql
-- Drop new objects
DROP VIEW IF EXISTS hwm_history CASCADE;
DROP VIEW IF EXISTS period_returns CASCADE;
DROP VIEW IF EXISTS nav_with_cashflows CASCADE;
DROP FUNCTION IF EXISTS calculate_monthly_fees CASCADE;
DROP FUNCTION IF EXISTS calculate_twr_period CASCADE;
DROP TABLE IF EXISTS fee_tracking CASCADE;

-- Revert transaction type constraint
ALTER TABLE processed_transactions 
DROP CONSTRAINT processed_transactions_type_check;

ALTER TABLE processed_transactions 
ADD CONSTRAINT processed_transactions_type_check 
CHECK (type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL'));
```