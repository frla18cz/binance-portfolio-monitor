# Binance Portfolio Monitor

**Automated cryptocurrency trading performance monitoring system** that tracks Binance futures accounts against a 50/50 BTC/ETH benchmark portfolio.

## 🎯 What It Does

- **Tracks Performance**: Monitors your Binance futures account NAV vs a passive 50/50 BTC/ETH portfolio
- **Smart Benchmarking**: Automatically adjusts benchmark for deposits/withdrawals  
- **Historical Analysis**: Stores performance data for trend analysis
- **Multi-Account Support**: Monitor multiple Binance accounts simultaneously
- **Automated Rebalancing**: Periodic benchmark rebalancing to maintain 50/50 allocation

## 📊 Key Features

### Performance Monitoring
- Real-time NAV tracking from Binance futures API
- Benchmark calculation using live BTC/ETH prices
- Historical data storage for comparative analysis

### Intelligent Deposit/Withdrawal Handling
- **Deposits**: Automatically increases benchmark allocation (50% BTC, 50% ETH)
- **Withdrawals**: Proportionally reduces benchmark allocation
- **Idempotent Processing**: No duplicate transaction processing

### Robust Architecture
- Serverless design (Vercel-ready)
- Database-driven configuration
- Atomic operations for data consistency
- Error recovery and graceful degradation

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Binance account with futures trading enabled
- Supabase database instance

### 1. Clone & Install
```bash
git clone <your-repo>
cd binance_monitor_playground
pip install -r requirements.txt
```

### 2. Database Setup
Create the following tables in your Supabase instance:

```sql
-- Binance account credentials
CREATE TABLE binance_accounts (
    id SERIAL PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL,
    api_key TEXT NOT NULL,
    api_secret TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Benchmark configuration per account
CREATE TABLE benchmark_configs (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES binance_accounts(id),
    btc_units DECIMAL(20,8) DEFAULT 0,
    eth_units DECIMAL(20,8) DEFAULT 0,
    rebalance_day INTEGER DEFAULT 0, -- 0=Monday, 6=Sunday
    rebalance_hour INTEGER DEFAULT 12, -- Hour of day (0-23)
    next_rebalance_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Historical NAV and benchmark data
CREATE TABLE nav_history (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES binance_accounts(id),
    timestamp TIMESTAMPTZ NOT NULL,
    nav DECIMAL(20,2) NOT NULL,
    benchmark_value DECIMAL(20,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transaction processing tracking
CREATE TABLE processed_transactions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES binance_accounts(id),
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount DECIMAL(20,8) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Processing status per account
CREATE TABLE account_processing_status (
    account_id INTEGER PRIMARY KEY REFERENCES binance_accounts(id),
    last_processed_timestamp TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. Environment Configuration
Create `.env` file:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
# Optional: SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### 4. Add Your Binance Account
Insert your account credentials into the database:
```sql
-- Add your account
INSERT INTO binance_accounts (account_name, api_key, api_secret) 
VALUES ('My Trading Account', 'your-binance-api-key', 'your-binance-api-secret');

-- Add benchmark config
INSERT INTO benchmark_configs (account_id, rebalance_day, rebalance_hour)
VALUES (1, 0, 12); -- Rebalance Mondays at 12:00
```

### 5. Test Run
```bash
python api/index.py
```

Expected output:
```
Running script locally for testing...
Found 1 accounts to process.
--- Processing account: My Trading Account ---
Benchmark not initialized. Initializing now...
Initializing benchmark with NAV: 10000.00
Benchmark initialized. Next rebalance: 2025-07-07 12:00:00
2025-07-02T12:00:00+00:00 | NAV: 10000.00 | Benchmark: 10000.00
```

## 📈 How It Works

### Initial Setup
1. **First Run**: System detects uninitialized benchmark
2. **Allocation**: Splits current NAV 50/50 between BTC and ETH
3. **Storage**: Saves BTC/ETH units to track benchmark value

### Ongoing Monitoring
1. **Price Fetch**: Gets current BTC/ETH prices from Binance
2. **NAV Calculation**: `totalWalletBalance + totalUnrealizedProfit`
3. **Transaction Processing**: Checks for new deposits/withdrawals
4. **Benchmark Adjustment**: Updates allocation based on cashflow
5. **Data Storage**: Saves snapshot for historical analysis

### Benchmark Logic
```python
# Deposit: Add to benchmark proportionally
if deposit_amount > 0:
    btc_units += (deposit_amount / 2) / btc_price
    eth_units += (deposit_amount / 2) / eth_price

# Withdrawal: Reduce benchmark proportionally  
if withdrawal_amount > 0:
    reduction_ratio = withdrawal_amount / current_benchmark_value
    btc_units *= (1 - reduction_ratio)
    eth_units *= (1 - reduction_ratio)
```

## 🔧 Configuration Options

### Rebalancing Schedule
Configure when benchmark rebalances back to 50/50:
```sql
UPDATE benchmark_configs SET 
    rebalance_day = 0,  -- Monday
    rebalance_hour = 12 -- 12:00 PM
WHERE account_id = 1;
```

### Multiple Accounts
Add multiple accounts for comparison:
```sql
INSERT INTO binance_accounts (account_name, api_key, api_secret) 
VALUES 
    ('Conservative Account', 'api-key-1', 'api-secret-1'),
    ('Aggressive Account', 'api-key-2', 'api-secret-2');
```

## 🚀 Deployment

### Vercel Deployment
1. Connect your GitHub repository to Vercel
2. Set environment variables in Vercel dashboard
3. Deploy - the `/api/index.py` becomes your API endpoint

### Cron Job Setup
Set up automated monitoring:
```bash
# Run every hour
0 * * * * curl https://your-app.vercel.app/api
```

Or use Vercel Cron:
```json
{
  "crons": [
    {
      "path": "/api",
      "schedule": "0 * * * *"
    }
  ]
}
```

## 📊 Data Analysis

### Performance Queries
```sql
-- Latest performance comparison
SELECT 
    ba.account_name,
    nh.nav,
    nh.benchmark_value,
    (nh.nav - nh.benchmark_value) AS difference,
    ((nh.nav - nh.benchmark_value) / nh.benchmark_value * 100) AS outperformance_pct
FROM nav_history nh
JOIN binance_accounts ba ON nh.account_id = ba.id
WHERE nh.timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY nh.timestamp DESC;

-- Historical performance trend
SELECT 
    DATE(timestamp) as date,
    AVG(nav) as avg_nav,
    AVG(benchmark_value) as avg_benchmark
FROM nav_history 
WHERE account_id = 1
GROUP BY DATE(timestamp)
ORDER BY date DESC
LIMIT 30;
```

## 🔒 Security Best Practices

### API Key Permissions
Set Binance API key permissions to:
- ✅ **Read** - For account data
- ❌ **Trade** - Not needed for monitoring
- ❌ **Withdraw** - Never enable for monitoring

### Database Security
```sql
-- Enable Row Level Security
ALTER TABLE binance_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE benchmark_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE nav_history ENABLE ROW LEVEL SECURITY;

-- Create policies as needed
```

### Environment Variables
- Never commit `.env` files
- Use different keys for different environments
- Consider using service role key for backend operations

## 🐛 Troubleshooting

### Common Issues

**"No accounts found"**
```sql
-- Check if accounts exist
SELECT * FROM binance_accounts;
```

**"Benchmark config not found"**
```sql
-- Add missing benchmark config
INSERT INTO benchmark_configs (account_id, rebalance_day, rebalance_hour)
VALUES (1, 0, 12);
```

**"Error getting NAV"**
- Verify Binance API credentials
- Check API key permissions
- Ensure futures trading is enabled on account

**"Database connection error"**
- Verify Supabase URL and key
- Check network connectivity
- Confirm database tables exist

### Debug Mode
Add debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 API Reference

### Main Endpoint
```
GET /api
```
Processes all accounts and returns status.

### Response Format
```
HTTP 200: "Monitoring process completed successfully."
HTTP 500: "Error: [error message]"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is for educational and personal use. Please ensure compliance with Binance API terms of service.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review Binance API documentation
3. Check Supabase connection and permissions
4. Open an issue with detailed error logs

---

**Happy Trading! 📈**