# Database Overview - Quick Reference

## 🗂️ Table Categories

### 📊 Core Trading Data
1. **binance_accounts** - API credentials & account settings
2. **nav_history** - Hourly NAV snapshots  
3. **processed_transactions** - All deposits/withdrawals
4. **price_history** - BTC/ETH price records

### 🎯 Benchmark System
5. **benchmark_configs** - Current benchmark state & settings
6. **benchmark_rebalance_history** - Complete rebalancing audit trail (NEW)
7. **benchmark_modifications** - Deposit/withdrawal impacts (NEW)

### 💰 Fee Management
8. **fee_tracking** - Monthly performance fee calculations

### 🔧 System & Metadata
9. **users** - User authentication
10. **system_logs** - Application logs (auto-cleanup after 30 days)
11. **system_metadata** - System configuration
12. **account_processing_status** - Tracks last processed time

## 🔗 Key Relationships

```
users (1) ─── (N) binance_accounts
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
    ↓                   ↓                   ↓
nav_history    benchmark_configs    processed_transactions
                        │
            ┌───────────┴───────────┐
            │                       │
            ↓                       ↓
benchmark_rebalance_history  benchmark_modifications
```

## 📈 Views for Analysis
- **nav_with_cashflows** - Combines NAV + transactions for TWR
- **period_returns** - Calculates period-by-period returns
- **hwm_history** - High Water Mark tracking

## 🧮 Key Functions
- **calculate_twr_period()** - Time-Weighted Returns
- **calculate_monthly_fees()** - Performance fee calculation
- **cleanup_old_system_logs()** - Automatic log retention

## 🎯 Quick Queries

### Check Account Performance
```sql
SELECT account_name, nav, benchmark_value, 
       (nav / benchmark_value - 1) * 100 as alpha_pct
FROM nav_history
WHERE account_id = ? 
ORDER BY timestamp DESC LIMIT 1;
```

### Recent Rebalancing
```sql
SELECT * FROM benchmark_rebalance_history
WHERE rebalance_timestamp > NOW() - INTERVAL '7 days'
ORDER BY rebalance_timestamp DESC;
```

### Deposit/Withdrawal Impact
```sql
SELECT * FROM benchmark_modifications
WHERE account_name = ?
ORDER BY modification_timestamp DESC
LIMIT 10;
```

### Fee Status
```sql
SELECT * FROM fee_tracking
WHERE status = 'ACCRUED'
ORDER BY period_end DESC;
```

## 📚 Detailed Documentation
- Full schema details: `DATABASE_SCHEMA.md`
- Benchmark system: `BENCHMARK_METADATA_IMPROVEMENTS.md`
- Fee system: See CLAUDE.md "Alpha & Fee Usage Guide"