# Changelog

All notable changes to this project will be documented in this file.

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