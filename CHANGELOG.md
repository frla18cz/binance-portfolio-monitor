# Changelog

All notable changes to this project will be documented in this file.

## [2025-07-09] - Critical Bug Fixes

### 🐛 Fixed
- **Rebalancing NameError**: Fixed critical bug in `rebalance_benchmark` function where undefined variable `new_eth_units` was used instead of `eth_units` (api/index.py:473)
  - This error prevented "Simple" and "Ondra(test)" accounts from processing correctly
  - "Habitanti" account was unaffected as it hadn't triggered the rebalancing code path
- **Transaction ID Length**: Increased `transaction_id` column from VARCHAR(50) to VARCHAR(255) in `processed_transactions` table
  - Fixed PostgreSQL error "value too long for type character varying(50)"
  - Some Binance transaction IDs exceed 50 characters
  - Created migration script: `sql/fix_transaction_id_length.sql`

### 🚀 Impact
- All accounts now process successfully without rebalancing errors
- Transaction processing no longer fails due to ID length constraints
- Improved system reliability and error handling

## [2025-07-09] - Log Retention Optimization

### ✨ Added
- **Automatic Log Cleanup**: Implemented `LogCleanupManager` for daily automated cleanup of logs older than 30 days
- **System Metadata Table**: Created `system_metadata` table to track cleanup state and prevent redundant operations
- **Cleanup Integration**: Integrated log cleanup into main monitoring process (runs after processing all accounts)

### 🔄 Changed
- **Log Retention Period**: Reduced from 365 days to 30 days for significant bandwidth and storage savings
- **Configuration Updates**:
  - `retention_days`: 365 → 30 (in `config/settings.json`)
  - `log_retention_hours`: 876,000 → 720 (matching 30 days)
- **SQL Cleanup Function**: Updated to use 30-day retention period in database

### 🚀 Performance Improvements
- **Bandwidth Reduction**: ~90% reduction in log-related query bandwidth
- **Storage Optimization**: Automatic removal of old logs keeps database lean
- **Query Performance**: Faster log queries with smaller dataset

### 📊 Technical Details
- **Cleanup Frequency**: Runs once per day (tracked via `last_log_cleanup` in system_metadata)
- **Database Migration**: Applied new tables and functions directly to Supabase
- **Failsafe Design**: Cleanup failures don't affect main monitoring process

## [2025-07-07] - Enhanced Dashboard UX and Account Selector

### ✨ Added
- **Premium Account Selector**: Complete redesign with modern card-based UI featuring gradients, shadows, and animations
- **Loading States**: Enhanced loading indicators with skeleton animations and smooth transitions during account switching
- **Visual Feedback**: Toast notifications, status updates, and micro-interactions for better user experience
- **Responsive Design**: Mobile-optimized layout with auto-sizing select dropdown based on account name length

### 🐛 Fixed
- **Logs Loading**: Fixed logs not displaying by correcting table name from 'logs' to 'system_logs' in API calls
- **Account Selector Position**: Moved account selector to prominent position under control buttons for better visibility
- **UI Consistency**: Removed unnecessary status indicators and simplified account switching interface

### 🎨 Enhanced
- **Animations**: Added shimmer border effects, hover animations, and smooth scaling during account operations
- **Typography**: Improved font weights, spacing, and visual hierarchy throughout account selector
- **Loading Overlay**: Professional loading screen with centered content during account switching operations

## [2025-07-07] - UI Consistency and Bug Fixes

### 🐛 Fixed
- **Benchmark Display Discrepancy**: Fixed a bug where the main dashboard metric for "vs Benchmark" showed a different value than the chart. The metric now uses the same dynamic calculation as the chart, ensuring UI consistency.

### 🔄 Changed
- **Dashboard Port**: Changed the default dashboard port from `8001` to `8000` to align with common development standards.

## [2025-07-06] - Clean Benchmark System Implementation

### ✅ Added
- **Clean Start Benchmark System**: Implemented accurate historical price-based benchmark calculation
- **Price Columns**: Added `btc_price` and `eth_price` columns to `nav_history` table for historical price storage
- **Dynamic Benchmark Calculation**: Uses actual historical prices instead of current prices for realistic benchmark comparisons
- **Interactive NAV Chart**: Added period selector (Since Inception, 1 Week, 1 Month, 1 Year, YTD, Custom) with dual chart system
- **Weekly Rebalancing**: Proper 50/50 BTC/ETH allocation rebalancing every Monday at 17:00 UTC
- **Debug Tools**: 
  - `test_clean_benchmark.py` - Database structure validation
  - `debug_nav.py` - Detailed NAV calculation breakdown
- **SQL Migration**: `add_price_columns.sql` for database schema updates

### 🔄 Changed
- **save_history() Function**: Now requires BTC/ETH prices as mandatory parameters
- **calculate_dynamic_benchmark()**: Rewritten to use historical prices from database records
- **Dashboard Port**: Changed from 8000 to 8001 to avoid conflicts
- **Chart Data API**: Enhanced `/api/dashboard/chart-data` endpoint with period filtering
- **Database Schema**: Extended nav_history table to include historical price data

### 🗑️ Removed
- **Fallback Logic**: Removed compatibility code for old database structure without price columns
- **Current Price Benchmark**: Eliminated unrealistic benchmark using today's prices for historical periods
- **Old NAV History**: Deleted 461 existing records for clean start approach

### 🐛 Fixed
- **Benchmark Calculation Accuracy**: Fixed issue where benchmark used current BTC/ETH prices for entire historical period
- **Import Errors**: Fixed relative import issues in dashboard standalone execution
- **Chart Period Logic**: Improved period-based data filtering for accurate performance calculations

### ⚠️ Known Issues
- **NAV Calculation Discrepancy**: ~$20k difference between our calculated NAV and Binance UI values
  - Our system: `totalWalletBalance + totalUnrealizedProfit` = ~$399k
  - Binance UI may show: `totalWalletBalance` only = ~$402k
  - Investigation ongoing - see `debug_nav.py` for detailed breakdown

### 📊 Technical Details
- **Database Migration**: Added price columns to nav_history table
- **Clean Data Approach**: Started fresh data collection with proper historical price tracking
- **Benchmark Strategy**: 50/50 BTC/ETH allocation with weekly Monday rebalancing
- **Performance Tracking**: Accurate inception-to-date performance comparison

### 🚀 Usage Updates
- Dashboard now runs on port 8001: `http://localhost:8001/dashboard`
- Use `python -m api.dashboard` for proper module import
- Run `python debug_nav.py` to investigate NAV calculation details
- Run `python test_clean_benchmark.py` to verify database structure

---

## Previous Versions

### [2025-07-05] - Initial Benchmark Implementation
- Basic 50/50 BTC/ETH benchmark system
- Real-time data collection every 2 minutes
- Dashboard with basic NAV tracking
- Supabase database integration
- Binance API futures account monitoring