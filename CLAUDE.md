# Claude Context - Binance Portfolio Monitor

This file contains important context and notes for Claude to understand the project better.

## Project Overview
Binance Portfolio Monitor tracks cryptocurrency trading performance against a 50/50 BTC/ETH benchmark portfolio.

## Recent Updates

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
- `nav_history` - Historical NAV and benchmark values
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

### Test Wallet Endpoints
The debug script now tests all wallet types:
- Funding wallet: `client.funding_wallet()`
- Simple Earn: `client._request('GET', 'sapi/v1/simple-earn/flexible/position', True, {})`
- Staking: `client.get_staking_position(product='STAKING')`

## Known Issues
- Transaction processing may fail with "value too long" error - needs investigation
- Rebalancing has undefined variable error (new_eth_units) - needs fix
- Some wallet types (Funding, Simple Earn) may return errors if not activated on the account

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