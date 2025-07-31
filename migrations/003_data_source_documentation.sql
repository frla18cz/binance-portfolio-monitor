-- Migration: Document data sources for all columns
-- Purpose: Clearly mark which data is RAW (from Binance) vs CALCULATED
-- Date: 2025-07-29

-- ============================================
-- NAV_HISTORY - Mixed RAW and CALCULATED data
-- ============================================
COMMENT ON COLUMN nav_history.nav IS 'RAW: Portfolio Net Asset Value fetched directly from Binance API';
COMMENT ON COLUMN nav_history.btc_price IS 'RAW: BTC price in USDT from Binance API at snapshot time';
COMMENT ON COLUMN nav_history.eth_price IS 'RAW: ETH price in USDT from Binance API at snapshot time';
COMMENT ON COLUMN nav_history.benchmark_value IS 'CALCULATED: Benchmark portfolio value = (btc_units * btc_price) + (eth_units * eth_price)';
COMMENT ON COLUMN nav_history.timestamp IS 'SYSTEM: When this snapshot was taken';
COMMENT ON COLUMN nav_history.account_id IS 'SYSTEM: Reference to binance_accounts';
COMMENT ON COLUMN nav_history.account_name IS 'SYSTEM: Cached account name for performance';

-- ============================================
-- PRICE_HISTORY - Pure RAW data
-- ============================================
COMMENT ON COLUMN price_history.btc_price IS 'RAW: BTC/USDT price from Binance public API';
COMMENT ON COLUMN price_history.eth_price IS 'RAW: ETH/USDT price from Binance public API';
COMMENT ON COLUMN price_history.timestamp IS 'SYSTEM: When prices were fetched';

-- ============================================
-- PROCESSED_TRANSACTIONS - Pure RAW data
-- ============================================
COMMENT ON COLUMN processed_transactions.amount IS 'RAW: Transaction amount from Binance API';
COMMENT ON COLUMN processed_transactions.type IS 'RAW: Transaction type from Binance (mapped from various fields)';
COMMENT ON COLUMN processed_transactions.transaction_id IS 'RAW: Unique identifier from Binance';
COMMENT ON COLUMN processed_transactions.timestamp IS 'RAW: Transaction timestamp from Binance';
COMMENT ON COLUMN processed_transactions.metadata IS 'RAW: Additional transaction data from Binance API';

-- ============================================
-- BENCHMARK_CONFIGS - Pure CALCULATED data
-- ============================================
COMMENT ON COLUMN benchmark_configs.btc_units IS 'CALCULATED: Current BTC holdings in benchmark portfolio';
COMMENT ON COLUMN benchmark_configs.eth_units IS 'CALCULATED: Current ETH holdings in benchmark portfolio';
COMMENT ON COLUMN benchmark_configs.next_rebalance_timestamp IS 'CALCULATED: Next scheduled rebalancing time';
COMMENT ON COLUMN benchmark_configs.last_rebalance_btc_units IS 'CALCULATED: BTC units before last rebalance';
COMMENT ON COLUMN benchmark_configs.last_rebalance_eth_units IS 'CALCULATED: ETH units before last rebalance';

-- ============================================
-- BENCHMARK_REBALANCE_HISTORY - Pure CALCULATED data
-- ============================================
COMMENT ON COLUMN benchmark_rebalance_history.btc_units_before IS 'CALCULATED: BTC units before rebalancing';
COMMENT ON COLUMN benchmark_rebalance_history.eth_units_before IS 'CALCULATED: ETH units before rebalancing';
COMMENT ON COLUMN benchmark_rebalance_history.btc_price IS 'RAW: BTC price at rebalance time (from price_history)';
COMMENT ON COLUMN benchmark_rebalance_history.eth_price IS 'RAW: ETH price at rebalance time (from price_history)';
COMMENT ON COLUMN benchmark_rebalance_history.btc_value_before IS 'CALCULATED: BTC value = btc_units_before * btc_price';
COMMENT ON COLUMN benchmark_rebalance_history.eth_value_before IS 'CALCULATED: ETH value = eth_units_before * eth_price';
COMMENT ON COLUMN benchmark_rebalance_history.total_value_before IS 'CALCULATED: Total benchmark value before rebalancing';
COMMENT ON COLUMN benchmark_rebalance_history.btc_units_after IS 'CALCULATED: BTC units after rebalancing (50% of total value)';
COMMENT ON COLUMN benchmark_rebalance_history.eth_units_after IS 'CALCULATED: ETH units after rebalancing (50% of total value)';

-- ============================================
-- BENCHMARK_MODIFICATIONS - Mixed RAW triggers with CALCULATED results
-- ============================================
COMMENT ON COLUMN benchmark_modifications.cashflow_amount IS 'RAW: Deposit/withdrawal amount from processed_transactions';
COMMENT ON COLUMN benchmark_modifications.btc_price IS 'RAW: BTC price at modification time';
COMMENT ON COLUMN benchmark_modifications.eth_price IS 'RAW: ETH price at modification time';
COMMENT ON COLUMN benchmark_modifications.btc_units_before IS 'CALCULATED: BTC units before modification';
COMMENT ON COLUMN benchmark_modifications.eth_units_before IS 'CALCULATED: ETH units before modification';
COMMENT ON COLUMN benchmark_modifications.btc_allocation IS 'CALCULATED: 50% of cashflow for deposits';
COMMENT ON COLUMN benchmark_modifications.eth_allocation IS 'CALCULATED: 50% of cashflow for deposits';
COMMENT ON COLUMN benchmark_modifications.btc_units_after IS 'CALCULATED: BTC units after applying modification';
COMMENT ON COLUMN benchmark_modifications.eth_units_after IS 'CALCULATED: ETH units after applying modification';

-- ============================================
-- FEE_TRACKING - Pure CALCULATED data
-- ============================================
COMMENT ON COLUMN fee_tracking.avg_nav IS 'CALCULATED: Average NAV for the period';
COMMENT ON COLUMN fee_tracking.portfolio_twr IS 'CALCULATED: Time-Weighted Return of portfolio';
COMMENT ON COLUMN fee_tracking.benchmark_twr IS 'CALCULATED: Time-Weighted Return of benchmark';
COMMENT ON COLUMN fee_tracking.alpha_pct IS 'CALCULATED: Alpha = portfolio_twr - benchmark_twr';
COMMENT ON COLUMN fee_tracking.performance_fee IS 'CALCULATED: Fee based on alpha and HWM';

-- ============================================
-- Table-level documentation
-- ============================================
COMMENT ON TABLE nav_history IS 'MIXED: Contains both RAW data from Binance API (nav, prices) and CALCULATED data (benchmark_value)';
COMMENT ON TABLE price_history IS 'RAW: Pure market data from Binance public API';
COMMENT ON TABLE processed_transactions IS 'RAW: Transaction history from Binance account API';
COMMENT ON TABLE benchmark_configs IS 'CALCULATED: Current state of benchmark portfolio';
COMMENT ON TABLE benchmark_rebalance_history IS 'CALCULATED: Complete audit trail of benchmark rebalancing';
COMMENT ON TABLE benchmark_modifications IS 'CALCULATED: Impact of deposits/withdrawals on benchmark';
COMMENT ON TABLE fee_tracking IS 'CALCULATED: Performance fee calculations';