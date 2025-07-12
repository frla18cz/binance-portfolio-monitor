# Claude Context - Binance Portfolio Monitor

This file contains important context and notes for Claude to understand the project better.

## Project Overview
Binance Portfolio Monitor tracks cryptocurrency trading performance against a 50/50 BTC/ETH benchmark portfolio.

## Recent Updates

### Binance Data API Integration (2025-07-12)
- **Geographic Restriction Solution**: Switched to `data-api.binance.vision` for public endpoints
- **Problem Solved**: Vercel functions in Frankfurt region were still blocked by Binance
- **Root Cause**: Cloud provider IP ranges (AWS, GCP, Vercel) are geo-blocked by Binance
- **Implementation**: 
  - Added `data_api_url` configuration pointing to `https://data-api.binance.vision/api`
  - Modified `get_prices()` function to automatically use data API for price fetching
  - Updated BinanceConfig dataclass to include data_api_url field
- **Scope**: Only affects public read-only endpoints (prices, tickers)
- **Account APIs**: Private account endpoints (NAV, balances) still use regular Binance API with API keys
- **Result**: ✅ Fully functional monitoring on Vercel with hourly cron execution
- **Files Modified**: `config/settings.json`, `config/__init__.py`, `api/index.py`, `api/dashboard.py`
- **Testing**: Added data API test to debug endpoint for verification

### Frankfurt Region Configuration (2025-07-12)
- **Vercel Region**: Configured functions to run in Frankfurt (fra1) instead of US (iad1)
- **Purpose**: Attempt to bypass Binance geographic restrictions for EU region
- **Implementation**: Added `"functions": {"api/*.py": {"regions": ["fra1"]}}` to vercel.json
- **Pro Plan**: Requires Vercel Pro plan for region selection functionality
- **Result**: Successfully deployed to Frankfurt but Binance still blocked cloud provider IPs
- **Follow-up**: Led to data API solution which completely resolved the issue
- **Files Modified**: `vercel.json`

### Vercel Production Deployment Fixes (2025-07-12)
- **Read-only Filesystem**: Added fallback for logger when file creation fails in Vercel
- **Config Validation**: Added environment variable fallback for missing Supabase credentials
- **Handler Export**: Added proper `handler = DashboardHandler` export for Vercel compatibility
- **Error Handling**: Comprehensive error handling for serverless environment constraints
- **Environment Detection**: Added logic to detect Vercel environment and adjust behavior
- **Robustness**: System now gracefully handles serverless limitations and missing dependencies
- **Files Modified**: `api/logger.py`, `api/index.py`, `api/dashboard.py`

### Dashboard Timestamp Enhancement (2025-07-12)
- **Price Timestamps**: Added timestamp display showing when prices were last fetched
- **Portfolio Timestamps**: Show last monitoring run time for each account
- **User Experience**: Users can see data freshness with relative time ("2 hours ago", "just now")
- **Implementation**:
  - Added `getTimeAgo()` JavaScript function for relative time calculation
  - Enhanced API responses to include timestamp metadata
  - Added CSS styling for timestamp display elements
- **Data Source**: Timestamps reflect actual database data age, not API call time
- **Hybrid Solution**: Combines cached database values with freshness indicators
- **Files Modified**: `dashboard.html`, `api/dashboard.py`

### Vercel Empty Functions Fix (2025-07-11)
- **Build Error**: Fixed "Function must contain at least one property" error
- **Problem**: Empty function objects `{}` in vercel.json functions section
- **Solution**: Removed entire functions section - Vercel auto-detects functions
- **Cron Impact**: No impact on cron jobs - they continue to work normally
- **Auto-Detection**: Vercel automatically detects Python functions in /api/ directory
- **Files Modified**: `vercel.json` - removed functions section entirely

### Vercel Python Runtime Fix (2025-07-11)
- **Issue Fixed**: Vercel deployment error "Function Runtimes must have a valid version"
- **Problem**: `"runtime": "python3.9"` specification in vercel.json was invalid
- **Solution**: Removed runtime specifications to use Python 3.12 default
- **Deployment**: Now compatible with Vercel's latest Python runtime requirements
- **Cron Schedule**: Maintained hourly execution (`0 * * * *`) for Pro plan
- **Files Modified**: `vercel.json` (removed runtime specifications)

### Automatic Benchmark Configs Creation (2025-07-11)
- **New Feature**: System now automatically creates missing benchmark_configs
- **Problem Solved**: No manual intervention needed when benchmark_configs are missing
- **Implementation**: Added `ensure_benchmark_configs()` function that runs before monitoring
- **Behavior**: Checks for missing configs and creates them with default values (btc_units=0, eth_units=0)
- **Result**: System is now self-healing - if configs are deleted, they're recreated automatically
- **Testing Completed**:
  - ✅ Test 1: Deleted all benchmark_configs - system recreated them automatically
  - ✅ Test 2: Added new user account - config was created on next monitoring run
  - ✅ Test 3: Monitoring runs correctly with auto-created configs
- **Fresh Start**: All data cleared for clean testing environment
- **Files Modified**: `api/index.py` (added ensure_benchmark_configs function)

### Missing Benchmark Configs Fix (2025-07-11)
- **Critical Issue**: Dashboard not collecting data due to missing benchmark_configs in database
- **Root Cause**: All 3 Binance accounts existed but had no corresponding benchmark_configs records
- **Impact**: Monitoring code skipped processing accounts without benchmark configs (api/index.py:125-129)
- **Solution**: Created benchmark_configs for all accounts with proper initialization
- **Database Changes**: Added 3 benchmark_configs records with btc_units=0, eth_units=0 (triggers initialization)
- **Enhanced Tracking**: Added rebalancing history fields for better monitoring
- **Result**: System now collects NAV data hourly and displays real-time dashboard data
- **Files Modified**: `api/index.py` (enhanced rebalancing tracking)

### Benchmark Independence Fix (2025-07-11)
- **Critical Fix**: Rebalancing now uses benchmark value instead of NAV
- **Problem Fixed**: Benchmark was being "reset" to NAV value during rebalancing, breaking independence
- **Solution**: Changed `rebalance_benchmark()` to use `current_benchmark_value` instead of `nav`
- **Validation Added**: 1% tolerance check ensures rebalancing preserves value
- **Frontend Simplified**: Removed dynamic calculation, now uses DB values
- **Result**: Benchmark evolves independently based on market prices only
- **Files Modified**: `api/index.py`, `api/dashboard.py`

### Dashboard UI Cleanup (2025-07-10)
- **Button Cleanup**: Removed non-functional buttons from dashboard interface
- **Removed Buttons**:
  - "▶️ Run Monitoring" - JavaScript function `runMonitoring()` was not implemented
  - "⏰ Auto Refresh: OFF" - JavaScript function `toggleAutoRefresh()` was not implemented
- **Remaining Functional**: Only "🔄 Refresh Data" button remains (fully functional)
- **Auto Refresh**: Continues to work automatically every 60 seconds in background
- **UI Improvement**: Cleaner interface with only working controls
- **File Modified**: `dashboard.html` - removed unused CSS and HTML elements

### Database Table Restructure (2025-07-10)
- **Table Data Reset**: Cleared all data from `system_metadata`, `system_logs`, `processed_transactions`, `price_history`, `nav_history`
- **NAV History Enhancement**: Added `account_name` column as second column in `nav_history` table
- **Auto-Population**: Created trigger to automatically populate `account_name` from `binance_accounts` table
- **Column Order**: Restructured `nav_history` with optimal column ordering: id, account_name, account_id, timestamp, nav, benchmark_value, btc_price, eth_price, created_at
- **Data Integrity**: All existing data preserved during table restructure
- **Migration Files**: `migrations/clear_tables_add_account_name.sql` and `migrations/reorder_nav_history_columns.sql`

### Local Development Cron Fix (2025-07-10)
- Fixed hardcoded 2-minute default intervals in `config/__init__.py`
- Changed fallback values from 2 minutes to 60 minutes (hourly)
- Ensures local development uses same schedule as production
- All scheduling now consistently uses `config/settings.json` values
- Prevents confusion between local (2min) and production (60min) intervals

### Cron Job Synchronization (2025-07-10)
- Updated both local cron and Vercel cron to run hourly (`0 * * * *`)
- Removed local cron job to prevent duplicate runs when deploying to Vercel
- Vercel will handle all scheduled executions in production
- Both systems now synchronized with `config/settings.json` hourly interval

### Hourly Data Collection (2025-01-10)
- Changed monitoring interval from 2 minutes to 60 minutes
- Reduces data volume by 97% (from 720 to 24 records per day)
- Dropped historical data tables for fresh start
- Improved dashboard performance with fewer data points
- Maintained log retention and cleanup functionality

### Price History Table Optimization (2025-01-10)
- Changed `price_history` table to store BTC and ETH prices on the same row
- Benefits: Better performance, simpler queries, atomic timestamps
- Migration SQL: `migrations/update_price_history_combined.sql`
- Updated `save_price_history()` to save both prices together

### Comprehensive NAV Calculation (2025-07-09)
- Extended `get_comprehensive_nav()` to include all wallet types:
  - Spot wallet
  - Futures wallet (USDT-M)
  - Funding wallet (Earn/Savings)
  - Simple Earn positions
  - Staking positions
- Removed `get_universal_nav()` function - requires dangerous "Universal Transfer" permissions
- All endpoints are read-only, no special permissions required
- Added error handling for each wallet type
- Updated debug_nav.py with wallet endpoint testing

### Log Retention Optimization (2025-07-09)
- Reduced log retention from 365 to 30 days
- Implemented automatic daily cleanup via `LogCleanupManager`
- Created `system_metadata` table for tracking cleanup state
- Integrated cleanup into main monitoring process
- Significantly reduces Supabase bandwidth usage (~90% reduction)

## Key Components

### Database Tables
- `binance_accounts` - Trading accounts configuration
- `benchmark_configs` - Benchmark portfolio settings
- `nav_history` - Historical NAV and benchmark values (with auto-populated account_name as 2nd column)
- `system_logs` - Application logs (30-day retention)
- `system_metadata` - System state tracking (e.g., last cleanup time)
- `processed_transactions` - Deposit/withdrawal tracking
- `price_history` - Historical BTC/ETH prices (combined row format)

### Configuration
- Main config: `config/settings.json`
- Log retention: 30 days (database_logging.retention_days)
- Monitoring interval: 60 minutes (hourly data collection)
- Rebalancing: Weekly on Mondays

### Performance Considerations
- Dashboard auto-refreshes every 60 seconds (consider increasing to 5 minutes)
- Chart queries should limit data points (max 500 recommended)
- Database queries should select only needed columns
- Log cleanup runs once daily to minimize overhead

## Benchmark System

### How Benchmark Works
- **Independent Evolution**: Benchmark operates independently from portfolio NAV
- **50/50 Allocation**: Maintains equal-weighted BTC/ETH through weekly rebalancing
- **Initialization**: Starts with same value as initial NAV, then evolves independently
- **Rebalancing**: Uses benchmark's own value (not NAV) to maintain 50/50 split
- **Performance Tracking**: Difference between NAV and benchmark shows trading alpha

### Benchmark Calculation
- Every hour: `benchmark_value = btc_units × BTC_price + eth_units × ETH_price`
- Weekly rebalancing: Recalculates units to restore 50/50 allocation
- Validation: 1% tolerance ensures rebalancing preserves value
- Storage: Values saved in `nav_history.benchmark_value`

## Common Tasks

### Check Supabase Bandwidth Usage
```python
# Bandwidth is visible in Supabase dashboard
# Current usage: ~2.5 GB/month (50% of free tier limit)
```

### Manual Log Cleanup
```python
from utils.log_cleanup import run_log_cleanup
run_log_cleanup()
```

### Debug NAV Calculation
```bash
python debug_nav.py
```

### Apply Database Migrations
```bash
# Apply table clearing and account_name addition
python apply_migration.py

# Verify nav_history table structure
python verify_nav_history.py
```

### Test Wallet Endpoints
The debug script now tests all wallet types:
- Funding wallet: `client.funding_wallet()`
- Simple Earn: `client._request('GET', 'sapi/v1/simple-earn/flexible/position', True, {})`
- Staking: `client.get_staking_position(product='STAKING')`

## Known Issues
- Transaction processing may fail with "value too long" error - needs investigation
- Some wallet types (Funding, Simple Earn) may return errors if not activated on the account

## Troubleshooting Guide

### Dashboard Shows No Data / "No NAV history"
1. **Check benchmark_configs**: Ensure all accounts have benchmark_configs records
   ```python
   # Check if configs exist
   from utils.database_manager import get_supabase_client
   supabase = get_supabase_client()
   accounts = supabase.table('binance_accounts').select('*, benchmark_configs(*)').execute()
   for account in accounts.data:
       print(f"{account['account_name']}: {'✅' if account.get('benchmark_configs') else '❌'}")
   ```

2. **Test manual monitoring**: Run `python -m api.index` to test data collection
3. **Check nav_history**: Verify data is being saved to database
4. **Verify cron job**: Check Vercel cron configuration in `vercel.json`
5. **Check Binance API access**: Verify geographic restrictions are not blocking data fetching

### Creating Missing Benchmark Configs
If benchmark_configs are missing, create them with:
```python
from utils.database_manager import get_supabase_client
supabase = get_supabase_client()

# Get accounts without configs
accounts = supabase.table('binance_accounts').select('*').execute()
for account in accounts.data:
    config = {
        'account_id': account['id'],
        'btc_units': 0.0,  # Will initialize on first run
        'eth_units': 0.0   # Will initialize on first run
    }
    supabase.table('benchmark_configs').insert(config).execute()
```

### Geographic Restrictions / "Service unavailable from restricted location"
If you see `APIError(code=0): Service unavailable from a restricted location` errors:

1. **Verify Data API Configuration**: Check that system is using data-api.binance.vision for prices
   ```python
   # Check current configuration
   from config import settings
   print(f"Data API URL: {settings.api.binance.data_api_url}")
   
   # Test data API access
   from binance.client import Client
   client = Client('', '')
   client.API_URL = 'https://data-api.binance.vision/api'
   ticker = client.get_symbol_ticker(symbol='BTCUSDT')
   print(f"Success: {ticker}")
   ```

2. **Check Vercel Region**: Ensure functions run in Frankfurt region (fra1)
   ```bash
   # Check deployment logs for region indicator
   curl -s https://your-app.vercel.app/api/health
   # Look for "fra1::" in response indicating Frankfurt deployment
   ```

3. **Monitor Logs**: Check system_logs table for price_fetch_error vs prices_fetched events

**Note**: Geographic restrictions only affect cloud provider IPs. The data API solution bypasses this for public endpoints while private account APIs work through Frankfurt region.

## Dashboard UI Notes
- **Current Status**: Dashboard has only functional "🔄 Refresh Data" button
- **Auto Refresh**: Runs automatically every 60 seconds (cannot be toggled)
- **Removed Features**: Manual monitoring trigger and auto-refresh toggle buttons were removed due to missing JavaScript implementations
- **Future Enhancements**: Consider implementing toggle functionality or manual monitoring trigger if needed

## Development Notes
- Always test with `python -m api.index` for proper imports
- Dashboard runs on port 8001
- Use demo mode for testing without real API calls

## Database Connection Management (2025-01-10)
- Implemented centralized database connection manager with singleton pattern
- All database connections now use `utils.database_manager.get_supabase_client()`
- Features:
  - Single shared connection instance across all modules
  - Automatic health checks every 60 seconds
  - Retry logic with exponential backoff (3 attempts)
  - Thread-safe access with locking
- Updated modules:
  - `api/index.py` - Uses shared connection
  - `api/logger.py` - Uses shared connection for log writes
  - `utils/log_cleanup.py` - Uses shared connection
- Benefits:
  - Reduced connection overhead (was creating 16+ separate connections)
  - Better error handling and recovery
  - Improved performance for high-frequency operations
# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.