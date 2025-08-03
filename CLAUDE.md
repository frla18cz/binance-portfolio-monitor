# Binance Portfolio Monitor

*This file serves as context for AI assistants. It contains only the most critical information needed to understand and work with the codebase. For detailed documentation, see the `docs/` directory.*

## Core Purpose
Tracks cryptocurrency trading performance by comparing actual portfolio NAV (Net Asset Value) against a passive 50/50 BTC/ETH benchmark strategy.

## How It Works

### 1. Portfolio Tracking
- **Fetches NAV** from Binance futures accounts every hour
- **NAV = spot + futures + funding + earn positions** (all wallets)
- **Tracks deposits/withdrawals** to adjust benchmark accordingly
- Stores everything in Supabase for historical analysis

### 2. Benchmark Logic
The benchmark simulates "what if I just held 50% BTC and 50% ETH":
- **Starts** with same value as initial portfolio NAV
- **Rebalances weekly** (Mondays) to maintain 50/50 allocation
- **Adjusts for cash flows**: When money deposited/withdrawn, benchmark buys/sells proportionally
- **Formula**: `benchmark_value = btc_units × current_btc_price + eth_units × current_eth_price`

### 3. Performance Calculation
```
Trading Alpha = (Current NAV / Benchmark Value - 1) × 100%
```
- **Positive %**: Your trading beats passive holding
- **Negative %**: You'd be better off just holding BTC/ETH

## Critical Implementation Details

### Transaction Processing
- **Problem**: Avoid double-counting historical deposits when restarting
- **Solution**: `initialized_at` timestamp - only process transactions after initialization
- **Unique constraint**: (account_id, transaction_id) prevents duplicates

### Deposit Processing & Multi-Coin Support
- **Supports all cryptocurrencies** - not limited to BTC/ETH
- **Automatic USD conversion** with fallback mechanism:
  1. Try direct USDT pair (e.g., SOLUSDT)
  2. Fall back to BTC routing (SOL→BTC→USD)
  3. Mark as `price_missing` if no price available
- **Metadata storage** for each deposit:
  ```json
  {
    "coin": "SOL",
    "network": "SOL",
    "usd_value": 500.00,
    "coin_price": 100.00,
    "price_source": "direct",  // or "via_btc"
    "price_missing": false
  }
  ```
- **Cashflow handling**: Deposits with missing prices are stored but excluded from NAV calculations
- **Retroactive updates**: Utility scripts can update historical deposits with missing prices

### Geographic Restrictions
- **Binance blocks cloud IPs** (AWS, Vercel, etc.)
- **Solution**: Use `data-api.binance.vision` for public data (prices)
- **Private data** (account NAV) works through Frankfurt region

### Process Safety
- **Lock file**: `/tmp/.binance_monitor.lock` prevents duplicate runs
- **Auto-recovery**: Stale locks (>1 hour) are cleared automatically

### Alpha Calculation & Fee Management
- **TWR (Time-Weighted Returns)**: Eliminates deposit/withdrawal bias
- **Alpha = Portfolio TWR - Benchmark TWR**
- **HWM (High Water Mark)**: Adjusted for all cashflows
- **Performance Fee**: Configurable per account (default 50%)
  - Only charged when NAV > HWM AND alpha > 0
  - No management fees
  - Monthly accruals, separate collection tracking

### Fee Configuration
```json
"fee_management": {
  "default_performance_fee_rate": 0.50,
  "calculation_schedule": "monthly",  // or "daily", "hourly"
  "calculation_day": 1,
  "calculation_hour": 0,
  "test_mode": { "enabled": false }
}
```
- Each account has `performance_fee_rate` in database
- Manual calculation: `python scripts/run_fee_calculation.py`

## Key Files
- `api/index.py` - Core monitoring logic
- `api/dashboard.py` - Web UI (port 8000) 
- `api/fee_calculator.py` - Fee calculations with flexible scheduling
- `api/calculate_fees.py` - Cron endpoint for fee calculations
- `scripts/run_fee_calculation.py` - Manual fee calculation tool
- `config/settings.json` - Configuration including fee management
- `deployment/aws/run_forever.py` - Production runner

## Database Schema
```
binance_accounts → API credentials + performance_fee_rate per account
benchmark_configs → tracks BTC/ETH units per account with rebalancing history + audit columns
nav_history → hourly NAV and benchmark values with account names
processed_transactions → deposit/withdrawal history (uses 'type' field)
fee_tracking → fee accruals and collections
system_logs → operation logs with retention
price_history → BTC/ETH price snapshots
account_processing_status → tracks last processed timestamp for each account
system_metadata → system-wide configuration and metadata
users → user authentication data
benchmark_rebalance_history → complete history of all rebalancing operations with calculations
benchmark_modifications → tracks all deposit/withdrawal impacts on benchmark

Views:
nav_with_cashflows → NAV data enriched with transactions
period_returns → TWR period returns calculation
hwm_history → High Water Mark tracking

Functions:
calculate_twr_period() → TWR for any date range
calculate_monthly_fees() → fee calculation with account-specific rates
```

### Transaction Processing
- **Field**: Use `type` field (NOT `transaction_type`) in processed_transactions
- **Valid Types**: DEPOSIT, WITHDRAWAL, PAY_DEPOSIT, PAY_WITHDRAWAL, FEE_WITHDRAWAL, SUB_DEPOSIT, SUB_WITHDRAWAL
- **Unique Key**: (account_id, transaction_id) prevents duplicates

### Sub-Account Transfers
- **Problem**: Binance API doesn't return internal transfers via standard withdrawal/deposit endpoints
- **Solution**: Use `client.get_sub_account_transfer_history()` from python-binance
- **Detection**: Master account credentials required - stored in `master_api_key` and `master_api_secret`
- **Implementation**: Sub-accounts use their own API keys for everything EXCEPT transfer detection
- **Recording**: Creates SUB_DEPOSIT/SUB_WITHDRAWAL transactions with USD conversion

### Account Reset
- **Purpose**: Clear all historical data for an account while preserving configuration
- **CLI Script**: `scripts/reset_account_data.py` - interactive or command-line reset
- **Web Admin**: Available in Config Admin under "Account Management" tab
- **Clears**: processed_transactions, nav_history, benchmark data, processing status
- **Preserves**: Account configuration, API keys, account name
- **Use Case**: Testing, fresh start, or fixing data issues

## MCP Server
- **Supabase MCP** (`mcp__supabase__*`) available for direct database operations
- Project ID: `axvqumsxlncbqzecjlxy` (binance_strategy_monitoring)
- Useful for debugging, running migrations, checking logs

## Common Commands
```bash
python scripts/run_once.py             # Run monitoring once (no dashboard/runtime setup)
python -m api.index                    # Run monitoring manually
python -m api.dashboard                # Start dashboard (port 8000)
python -m api.config_admin_web         # Start config admin (port 8002)
python debug_nav.py                    # Debug NAV calculation
python scripts/run_fee_calculation.py  # Manual fee calculation

# Deposit utilities
python scripts/test_coin_pricing.py    # Test coin pricing for various cryptocurrencies
python scripts/simulate_deposit_flow.py # Simulate deposit processing without DB changes
python scripts/fix_deposit_metadata.py  # Fix metadata for existing BTC deposits
python scripts/update_missing_prices.py # Update deposits with missing prices

# Benchmark validation
python scripts/validate_benchmark_consistency.py  # Validate benchmark calculations
python scripts/validate_benchmark_consistency.py --account "Simple"  # Validate specific account

# Sub-account transfers
python scripts/detect_sub_transfers.py        # Detect and record sub-account transfers
python scripts/process_sub_account_transfers.py # Process transfers for all master accounts

# Account management
python scripts/reset_account_data.py  # Reset account data for fresh start
python scripts/reset_account_data.py --list  # List all accounts
python scripts/reset_account_data.py --account "ondra_osobni_sub_acc1"  # Reset specific account
python scripts/reset_account_data.py --account "ondra_osobni_sub_acc1" --yes  # Skip confirmation
```

## Testing
For detailed testing instructions, see:
- `docs/TESTING_SUB_ACCOUNTS.md` - Complete guide for testing sub-account transfers and admin UI

## API Endpoints
- `/api/dashboard/metrics` - Current NAV and benchmark
- `/api/dashboard/alpha-metrics` - TWR and alpha calculations
- `/api/dashboard/fees` - Fee tracking and pending fees
- `/api/calculate_fees` - Trigger fee calculation (respects schedule)

## Alpha & Fee Usage Guide

### 1. Set Performance Fee Rate
```sql
-- Set fee rate for specific account (50% = 0.50)
UPDATE binance_accounts 
SET performance_fee_rate = 0.50 
WHERE account_name = 'YourAccountName';
```

### 2. Calculate Performance Metrics
```sql
-- Get TWR and alpha for last 30 days
SELECT * FROM calculate_twr_period(
  (SELECT id FROM binance_accounts WHERE account_name = 'YourAccount'),
  NOW() - INTERVAL '30 days',
  NOW()
);

-- Calculate fees for specific month
SELECT * FROM calculate_monthly_fees(
  (SELECT id FROM binance_accounts WHERE account_name = 'YourAccount'),
  '2025-07-01'::DATE
);
```

### 3. Manual Fee Calculation
```bash
# Show configuration
python scripts/run_fee_calculation.py --show-config

# List accounts with fee rates
python scripts/run_fee_calculation.py --list-accounts

# Calculate for specific month
python scripts/run_fee_calculation.py --month 2025-07

# Calculate last 3 months
python scripts/run_fee_calculation.py --last-n-months 3
```

### 4. Automated Fee Calculation
```bash
# Add to crontab for monthly calculation
0 0 1 * * curl https://your-domain/api/calculate_fees

# Or for testing (hourly)
0 * * * * curl https://your-domain/api/calculate_fees
```

### 5. Fee Collection Process
When collecting fees:
1. Withdraw the fee amount from Binance
2. Record in database as FEE_WITHDRAWAL:
```sql
INSERT INTO processed_transactions 
(account_id, transaction_id, type, amount, timestamp, status)
VALUES 
('account-uuid', 'unique-tx-id', 'FEE_WITHDRAWAL', 1000.00, NOW(), 'SUCCESS');
```

### 6. Dashboard Integration
- Alpha metrics available at: `/api/dashboard/alpha-metrics`
- Fee tracking available at: `/api/dashboard/fees`
- Historical TWR analysis in dashboard charts

## Benchmark Metadata Tracking
- **New tables**: `benchmark_rebalance_history` and `benchmark_modifications` track all benchmark changes with full audit trail
- **Validation script**: `scripts/validate_benchmark_consistency.py` verifies calculation accuracy
- **Details**: See `docs/BENCHMARK_METADATA_IMPROVEMENTS.md` for complete documentation

## Data Architecture Guidelines
- **RAW data**: Data from external APIs (Binance) - never modify, store as-is
- **CALCULATED data**: Our computations - keep separate from raw data
- **Mixed tables**: Use database comments to mark each column (RAW/CALCULATED/SYSTEM)
- **New features**: Create separate tables/views for raw vs calculated data
- **Details**: See `docs/DATA_FLOW_ARCHITECTURE.md` for patterns and examples