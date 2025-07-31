-- Migration: Create clarity views for better data separation
-- Purpose: Provide clear interfaces to RAW vs CALCULATED data
-- Date: 2025-07-29

-- ============================================
-- RAW DATA VIEWS
-- ============================================

-- View for raw Binance portfolio data
CREATE OR REPLACE VIEW binance_raw_nav AS
SELECT 
    account_id,
    account_name,
    timestamp,
    nav as portfolio_nav,
    btc_price,
    eth_price,
    created_at
FROM nav_history;

COMMENT ON VIEW binance_raw_nav IS 'RAW: Portfolio NAV and prices directly from Binance API';

-- View for raw transaction data
CREATE OR REPLACE VIEW binance_raw_transactions AS
SELECT 
    account_id,
    transaction_id,
    type as transaction_type,
    amount,
    timestamp as transaction_timestamp,
    status,
    metadata,
    created_at
FROM processed_transactions;

COMMENT ON VIEW binance_raw_transactions IS 'RAW: Transaction history from Binance account API';

-- View for raw price data
CREATE OR REPLACE VIEW binance_raw_prices AS
SELECT 
    timestamp as price_timestamp,
    btc_price,
    eth_price,
    created_at
FROM price_history;

COMMENT ON VIEW binance_raw_prices IS 'RAW: Market prices from Binance public API';

-- ============================================
-- CALCULATED DATA VIEWS
-- ============================================

-- View for calculated benchmark values
CREATE OR REPLACE VIEW calculated_benchmark_values AS
SELECT 
    nh.account_id,
    nh.account_name,
    nh.timestamp,
    nh.benchmark_value,
    bc.btc_units,
    bc.eth_units,
    nh.benchmark_value / NULLIF(nh.nav, 0) as benchmark_to_nav_ratio,
    (nh.nav - nh.benchmark_value) as absolute_difference,
    ((nh.nav / NULLIF(nh.benchmark_value, 0)) - 1) * 100 as performance_pct
FROM nav_history nh
LEFT JOIN benchmark_configs bc ON nh.account_id = bc.account_id;

COMMENT ON VIEW calculated_benchmark_values IS 'CALCULATED: Benchmark values and performance metrics';

-- View for calculated performance metrics
CREATE OR REPLACE VIEW calculated_performance_metrics AS
SELECT 
    ft.account_id,
    ba.account_name,
    ft.period_start,
    ft.period_end,
    ft.portfolio_twr,
    ft.benchmark_twr,
    ft.alpha_pct,
    ft.performance_fee,
    ft.status as fee_status
FROM fee_tracking ft
JOIN binance_accounts ba ON ft.account_id = ba.id;

COMMENT ON VIEW calculated_performance_metrics IS 'CALCULATED: TWR, alpha, and fee calculations';

-- ============================================
-- COMBINED VIEWS (for convenience)
-- ============================================

-- Complete portfolio snapshot combining RAW and CALCULATED
CREATE OR REPLACE VIEW portfolio_snapshot AS
SELECT 
    nh.account_id,
    nh.account_name,
    nh.timestamp,
    -- RAW data
    nh.nav as raw_portfolio_nav,
    nh.btc_price as raw_btc_price,
    nh.eth_price as raw_eth_price,
    -- CALCULATED data
    nh.benchmark_value as calc_benchmark_value,
    bc.btc_units as calc_btc_units,
    bc.eth_units as calc_eth_units,
    -- DERIVED metrics
    ((nh.nav / NULLIF(nh.benchmark_value, 0)) - 1) * 100 as alpha_pct,
    CASE 
        WHEN nh.nav > nh.benchmark_value THEN 'OUTPERFORMING'
        WHEN nh.nav < nh.benchmark_value THEN 'UNDERPERFORMING'
        ELSE 'MATCHING'
    END as performance_status
FROM nav_history nh
LEFT JOIN benchmark_configs bc ON nh.account_id = bc.account_id
ORDER BY nh.timestamp DESC;

COMMENT ON VIEW portfolio_snapshot IS 'MIXED: Complete portfolio view combining RAW and CALCULATED data';

-- ============================================
-- UTILITY VIEWS
-- ============================================

-- Data quality check view
CREATE OR REPLACE VIEW data_quality_check AS
SELECT 
    'nav_history' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN nav IS NULL THEN 1 END) as null_nav_count,
    COUNT(CASE WHEN benchmark_value IS NULL THEN 1 END) as null_benchmark_count,
    COUNT(CASE WHEN btc_price IS NULL OR eth_price IS NULL THEN 1 END) as null_price_count
FROM nav_history
UNION ALL
SELECT 
    'processed_transactions' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN amount IS NULL THEN 1 END) as null_amount_count,
    COUNT(CASE WHEN type IS NULL THEN 1 END) as null_type_count,
    0 as null_price_count
FROM processed_transactions;

COMMENT ON VIEW data_quality_check IS 'SYSTEM: Monitor data quality across tables';

-- ============================================
-- GRANTS (if needed for application access)
-- ============================================
-- Add any necessary grants here based on your security model