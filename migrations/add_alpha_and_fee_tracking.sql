-- Migration: Add Alpha Calculation and Fee Management
-- Date: 2025-07-25
-- Purpose: Add support for performance tracking, TWR calculation, and fee management

-- Step 1: Add FEE_WITHDRAWAL type to processed_transactions
ALTER TABLE processed_transactions 
DROP CONSTRAINT processed_transactions_type_check;

ALTER TABLE processed_transactions 
ADD CONSTRAINT processed_transactions_type_check 
CHECK (type IN ('DEPOSIT', 'WITHDRAWAL', 'PAY_DEPOSIT', 'PAY_WITHDRAWAL', 'FEE_WITHDRAWAL'));

-- Step 2: Create fee_tracking table
CREATE TABLE IF NOT EXISTS fee_tracking (
    id SERIAL PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES binance_accounts(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    -- NAV metrics
    avg_nav DECIMAL(20,8),
    starting_nav DECIMAL(20,8),
    ending_nav DECIMAL(20,8),
    -- HWM tracking
    starting_hwm DECIMAL(20,8),
    ending_hwm DECIMAL(20,8),
    -- Performance metrics
    portfolio_twr DECIMAL(10,6),
    benchmark_twr DECIMAL(10,6),
    alpha_pct DECIMAL(10,6),
    -- Fee calculations
    management_fee DECIMAL(20,8) NOT NULL DEFAULT 0,
    performance_fee DECIMAL(20,8) NOT NULL DEFAULT 0,
    total_fee DECIMAL(20,8) GENERATED ALWAYS AS (management_fee + performance_fee) STORED,
    -- Status tracking
    status VARCHAR(20) DEFAULT 'ACCRUED' CHECK (status IN ('ACCRUED', 'COLLECTED', 'WAIVED')),
    collected_at TIMESTAMPTZ,
    collection_tx_id VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, period_start)
);

-- Step 3: Create view for NAV with cashflows
CREATE OR REPLACE VIEW nav_with_cashflows AS
WITH hourly_cashflows AS (
    SELECT 
        account_id,
        date_trunc('hour', timestamp) as hour,
        SUM(CASE 
            WHEN type IN ('DEPOSIT', 'PAY_DEPOSIT') THEN amount
            WHEN type IN ('WITHDRAWAL', 'PAY_WITHDRAWAL', 'FEE_WITHDRAWAL') THEN -amount
            ELSE 0
        END) as net_cashflow,
        COUNT(*) as transaction_count,
        -- Breakdown by type for debugging
        SUM(CASE WHEN type IN ('DEPOSIT', 'PAY_DEPOSIT') THEN amount ELSE 0 END) as deposits,
        SUM(CASE WHEN type IN ('WITHDRAWAL', 'PAY_WITHDRAWAL') THEN amount ELSE 0 END) as withdrawals,
        SUM(CASE WHEN type = 'FEE_WITHDRAWAL' THEN amount ELSE 0 END) as fee_withdrawals
    FROM processed_transactions
    WHERE status = 'SUCCESS'
    GROUP BY account_id, date_trunc('hour', timestamp)
)
SELECT 
    n.id,
    n.account_id,
    n.timestamp,
    n.nav,
    n.benchmark_value,
    n.btc_price,
    n.eth_price,
    COALESCE(c.net_cashflow, 0) as cashflow_amount,
    COALESCE(c.transaction_count, 0) as cashflow_count,
    c.deposits,
    c.withdrawals,
    c.fee_withdrawals,
    LAG(n.nav) OVER (PARTITION BY n.account_id ORDER BY n.timestamp) as prev_nav,
    LAG(n.benchmark_value) OVER (PARTITION BY n.account_id ORDER BY n.timestamp) as prev_benchmark
FROM nav_history n
LEFT JOIN hourly_cashflows c 
    ON n.account_id = c.account_id 
    AND date_trunc('hour', n.timestamp) = c.hour
ORDER BY n.account_id, n.timestamp;

-- Step 4: Create view for period returns with TWR calculation
CREATE OR REPLACE VIEW period_returns AS
SELECT 
    *,
    -- NAV before cashflow (for TWR calculation)
    nav - cashflow_amount as nav_before_cashflow,
    -- Period return calculation
    CASE 
        WHEN prev_nav IS NULL OR prev_nav = 0 THEN NULL
        WHEN cashflow_amount != 0 THEN 
            -- With cashflow: use NAV before cashflow
            ((nav - cashflow_amount) / prev_nav) - 1
        ELSE 
            -- No cashflow: simple return
            (nav / prev_nav) - 1
    END as period_return,
    -- Benchmark period return (simple, no cashflow adjustment)
    CASE 
        WHEN prev_benchmark IS NULL OR prev_benchmark = 0 THEN NULL
        ELSE (benchmark_value / prev_benchmark) - 1
    END as benchmark_period_return,
    -- Simple alpha for this period (not TWR)
    CASE 
        WHEN benchmark_value > 0 THEN ((nav / benchmark_value) - 1) * 100
        ELSE 0
    END as simple_alpha_pct
FROM nav_with_cashflows;

-- Step 5: Create view for HWM tracking
CREATE OR REPLACE VIEW hwm_history AS
WITH cumulative_cashflows AS (
    SELECT 
        account_id,
        timestamp,
        nav,
        -- Calculate cumulative cashflows from newest to oldest
        -- This adjusts historical NAVs to current terms
        SUM(cashflow_amount) OVER (
            PARTITION BY account_id 
            ORDER BY timestamp DESC
            ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING
        ) - cashflow_amount as future_net_cashflows
    FROM nav_with_cashflows
),
adjusted_nav AS (
    SELECT 
        account_id,
        timestamp,
        nav,
        -- Adjust historical NAV by removing future cashflows
        nav - future_net_cashflows as adjusted_nav
    FROM cumulative_cashflows
)
SELECT 
    account_id,
    timestamp,
    nav as actual_nav,
    adjusted_nav,
    -- Running maximum of adjusted NAV
    MAX(adjusted_nav) OVER (
        PARTITION BY account_id 
        ORDER BY timestamp
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) as hwm
FROM adjusted_nav
ORDER BY account_id, timestamp;

-- Step 6: Function to calculate TWR for any period
CREATE OR REPLACE FUNCTION calculate_twr_period(
    p_account_id UUID,
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ
) RETURNS TABLE (
    portfolio_twr DECIMAL,
    benchmark_twr DECIMAL,
    alpha_twr DECIMAL,
    period_count INT,
    total_deposits DECIMAL,
    total_withdrawals DECIMAL,
    total_fees DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    WITH period_data AS (
        SELECT 
            period_return,
            benchmark_period_return,
            deposits,
            withdrawals,
            fee_withdrawals
        FROM period_returns
        WHERE account_id = p_account_id
        AND timestamp > p_start_date
        AND timestamp <= p_end_date
        AND period_return IS NOT NULL
    ),
    twr_calc AS (
        SELECT 
            -- Calculate TWR using product of (1 + return)
            CASE 
                WHEN COUNT(*) = 0 THEN 0
                WHEN MIN(1 + period_return) <= 0 THEN -1  -- Handle -100% return
                ELSE EXP(SUM(LN(1 + period_return))) - 1
            END as portfolio_twr,
            CASE 
                WHEN COUNT(*) = 0 THEN 0
                WHEN MIN(1 + benchmark_period_return) <= 0 THEN -1
                ELSE EXP(SUM(LN(1 + benchmark_period_return))) - 1
            END as benchmark_twr,
            COUNT(*)::INT as period_count,
            COALESCE(SUM(deposits), 0) as total_deposits,
            COALESCE(SUM(withdrawals), 0) as total_withdrawals,
            COALESCE(SUM(fee_withdrawals), 0) as total_fees
        FROM period_data
        WHERE period_return > -1  -- Exclude -100% returns from product
        AND benchmark_period_return > -1
    )
    SELECT 
        portfolio_twr * 100,  -- Convert to percentage
        benchmark_twr * 100,
        (portfolio_twr - benchmark_twr) * 100 as alpha_twr,
        period_count,
        total_deposits,
        total_withdrawals,
        total_fees
    FROM twr_calc;
END;
$$ LANGUAGE plpgsql;

-- Step 7: Function to calculate fees for a given month
CREATE OR REPLACE FUNCTION calculate_monthly_fees(
    p_account_id UUID,
    p_month DATE  -- First day of the month
) RETURNS TABLE (
    period_start DATE,
    period_end DATE,
    avg_nav DECIMAL,
    starting_nav DECIMAL,
    ending_nav DECIMAL,
    starting_hwm DECIMAL,
    ending_hwm DECIMAL,
    portfolio_twr DECIMAL,
    benchmark_twr DECIMAL,
    alpha_twr DECIMAL,
    management_fee DECIMAL,
    performance_fee DECIMAL,
    total_deposits DECIMAL,
    total_withdrawals DECIMAL
) AS $$
DECLARE
    v_period_start TIMESTAMPTZ;
    v_period_end TIMESTAMPTZ;
    v_mgmt_fee_rate DECIMAL := 0.02 / 12;  -- 2% annually = 0.167% monthly
    v_perf_fee_rate DECIMAL := 0.20;        -- 20% of outperformance
BEGIN
    -- Define period boundaries
    v_period_start := p_month::TIMESTAMPTZ;
    v_period_end := (p_month + INTERVAL '1 month')::DATE::TIMESTAMPTZ;
    
    -- Get TWR and cashflow data for the period
    SELECT 
        t.portfolio_twr,
        t.benchmark_twr,
        t.alpha_twr,
        t.total_deposits,
        t.total_withdrawals
    INTO 
        portfolio_twr,
        benchmark_twr,
        alpha_twr,
        total_deposits,
        total_withdrawals
    FROM calculate_twr_period(p_account_id, v_period_start, v_period_end) t;
    
    -- Get NAV and HWM data
    WITH nav_data AS (
        SELECT 
            nav,
            hwm,
            timestamp
        FROM hwm_history
        WHERE account_id = p_account_id
        AND timestamp >= v_period_start
        AND timestamp < v_period_end
        ORDER BY timestamp
    ),
    nav_summary AS (
        SELECT 
            AVG(nav) as avg_nav,
            FIRST_VALUE(nav) OVER (ORDER BY timestamp) as starting_nav,
            LAST_VALUE(nav) OVER (ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as ending_nav,
            FIRST_VALUE(hwm) OVER (ORDER BY timestamp) as starting_hwm,
            LAST_VALUE(hwm) OVER (ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as ending_hwm
        FROM nav_data
        LIMIT 1
    )
    SELECT 
        avg_nav,
        starting_nav,
        ending_nav,
        starting_hwm,
        ending_hwm
    INTO 
        avg_nav,
        starting_nav,
        ending_nav,
        starting_hwm,
        ending_hwm
    FROM nav_summary;
    
    -- Calculate fees
    management_fee := COALESCE(avg_nav * v_mgmt_fee_rate, 0);
    
    -- Performance fee only if:
    -- 1. Ending NAV > Starting HWM (new high)
    -- 2. Alpha > 0 (beat benchmark)
    IF ending_nav > starting_hwm AND alpha_twr > 0 THEN
        performance_fee := (ending_nav - starting_hwm) * v_perf_fee_rate;
    ELSE
        performance_fee := 0;
    END IF;
    
    -- Return results
    period_start := p_month;
    period_end := (p_month + INTERVAL '1 month' - INTERVAL '1 day')::DATE;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Step 8: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_fee_tracking_account_period 
ON fee_tracking(account_id, period_start DESC);

CREATE INDEX IF NOT EXISTS idx_fee_tracking_status 
ON fee_tracking(status) WHERE status = 'ACCRUED';

-- Step 9: Add trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_fee_tracking_updated_at 
BEFORE UPDATE ON fee_tracking
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Step 10: Add helpful comments
COMMENT ON TABLE fee_tracking IS 'Tracks monthly fee accruals and collections for each account';
COMMENT ON COLUMN fee_tracking.status IS 'ACCRUED: calculated but not collected, COLLECTED: fee has been withdrawn, WAIVED: fee was waived';
COMMENT ON COLUMN fee_tracking.alpha_pct IS 'Time-weighted return alpha (portfolio TWR - benchmark TWR)';
COMMENT ON VIEW nav_with_cashflows IS 'NAV history enriched with cashflow data from transactions';
COMMENT ON VIEW period_returns IS 'Calculates period returns for TWR calculation';
COMMENT ON VIEW hwm_history IS 'Tracks High Water Mark adjusted for deposits/withdrawals';
COMMENT ON FUNCTION calculate_twr_period IS 'Calculates Time-Weighted Returns for any period';
COMMENT ON FUNCTION calculate_monthly_fees IS 'Calculates management and performance fees for a given month';

-- Verify the migration
DO $$
BEGIN
    -- Check if FEE_WITHDRAWAL type is accepted
    BEGIN
        INSERT INTO processed_transactions (account_id, transaction_id, type, amount, timestamp, status)
        VALUES (
            (SELECT id FROM binance_accounts LIMIT 1),
            'TEST_FEE_WITHDRAWAL',
            'FEE_WITHDRAWAL',
            100,
            NOW(),
            'SUCCESS'
        );
        -- Rollback test insert
        DELETE FROM processed_transactions WHERE transaction_id = 'TEST_FEE_WITHDRAWAL';
        RAISE NOTICE 'FEE_WITHDRAWAL type successfully added';
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to add FEE_WITHDRAWAL type: %', SQLERRM;
    END;
    
    -- Check if fee_tracking table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'fee_tracking') THEN
        RAISE NOTICE 'fee_tracking table created successfully';
    ELSE
        RAISE EXCEPTION 'fee_tracking table not created';
    END IF;
    
    -- Check if views exist
    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'nav_with_cashflows') AND
       EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'period_returns') AND
       EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'hwm_history') THEN
        RAISE NOTICE 'All views created successfully';
    ELSE
        RAISE EXCEPTION 'Some views were not created';
    END IF;
    
    RAISE NOTICE 'Migration completed successfully!';
END $$;