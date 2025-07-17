# 📊 Binance Portfolio Monitor

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-30%20passed-green.svg)](./tests/)
[![Coverage](https://img.shields.io/badge/coverage-71%25-green.svg)](./tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**Automated cryptocurrency trading performance monitoring system** that tracks Binance futures accounts against a 50/50 BTC/ETH benchmark portfolio.

> **Note**: For Vercel deployment with proxy support, see the [`vercel-deployment-backup`](https://github.com/frla18cz/binance-portfolio-monitor/tree/vercel-deployment-backup) branch.

> ⚠️ **Educational Project**: This is a learning and research project. Use with caution in production environments.

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
- **📈 Enhanced Web Dashboard** with premium UI, real-time charts, and seamless account switching

### Intelligent Deposit/Withdrawal Handling
- **Deposits**: Automatically increases benchmark allocation (50% BTC, 50% ETH)
- **Withdrawals**: Proportionally reduces benchmark allocation
- **Idempotent Processing**: No duplicate transaction processing

### Advanced Logging & Monitoring
- **📋 Structured Logging** with JSON format and performance timing
- **🎯 Premium Dashboard** with enhanced account selector, live log streaming, and modern UI animations
- **⚡ Operation Timing** for performance optimization
- **🔍 Account-specific Tracking** with detailed audit trails
- **🧹 Automatic Log Cleanup** with 30-day retention and daily cleanup cycles
- **💾 Optimized Storage** reducing bandwidth usage by ~90%

### Safe Testing Environment
- **🎮 Demo Mode** for risk-free testing with mock data
- **💰 Transaction Simulation** (deposits, withdrawals)
- **📈 Market Scenario Testing** (bull run, bear market, etc.)
- **🔄 Complete System Testing** without real money

### Robust Architecture
- Serverless design (Vercel-ready)
- Database-driven configuration
- Atomic operations for data consistency
- Error recovery and graceful degradation

## 🏗️ Architecture

The system consists of three main components working together:
- **Orchestrator** (`run_forever.py`) - Manages scheduling and process lifecycle
- **Data Collector** (`api/index.py`) - Fetches data from Binance and calculates metrics
- **Web Dashboard** (`api/dashboard.py`) - Provides real-time visualization

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

## 🚀 Deployment Options

### Local Deployment
Best for development and testing. Run on your local machine with direct Binance API access.

### AWS EC2 Deployment (Recommended)
Complete deployment solution for production. See **[AWS_DEPLOYMENT_COMPLETE.md](AWS_DEPLOYMENT_COMPLETE.md)** for detailed instructions.

**Quick Start:**
```bash
# 1. Deploy code to EC2
./deployment/aws/deploy_simple.sh your-server-ip your-key.pem

# 2. SSH to server and setup
ssh -i your-key.pem ec2-user@your-server-ip
cd /home/ec2-user/binance-monitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp deployment/aws/.env.example .env
nano .env  # Add your API keys

# 4. Run
./deployment/aws/start_monitor.sh
```

**Features:**
- Simple Python + screen deployment
- Hourly automatic monitoring
- Dashboard on port 8000
- PyCharm integration support
- Easy management and troubleshooting

For systemd service (advanced users), see deployment documentation.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
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

#### Safe Demo Mode Testing
```bash
# Enable demo mode for safe testing
export DEMO_MODE=true
python demo_test.py
```

#### Production Testing
```bash
python api/index.py
```

#### Web Dashboard

```bash
python -m api.dashboard
# Open browser to: http://localhost:8000/dashboard
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
2. **NAV Calculation**: Comprehensive spot + futures account value calculation
3. **Transaction Processing**: Checks for new deposits/withdrawals
4. **Benchmark Adjustment**: Updates allocation based on cashflow
5. **Data Storage**: Saves snapshot for historical analysis

### NAV Calculation - Accurate Dashboard Matching
The system now uses a **comprehensive NAV calculation** that matches Binance dashboard values with **99.76% accuracy**:

#### Calculation Method:
1. **Spot Account**: All assets converted to USD at live prices
2. **Futures Account**: `marginBalance` per asset (wallet + unrealized P&L) converted to USD
3. **Total NAV**: Sum of spot + futures values

#### Formula:
```
NAV = Spot_Assets_USD + Futures_marginBalance_USD
```

Where:
- `Spot_Assets_USD` = All spot balances × live USD prices
- `Futures_marginBalance_USD` = Sum of (walletBalance + unrealizedProfit) × USD prices per asset

#### Why This Is Accurate:
- **Live Price Conversion**: Uses real-time BTC/USDT and other asset prices
- **Margin Balance**: Includes unrealized P&L in asset calculations
- **Dashboard Parity**: Matches exactly what Binance dashboard shows
- **Multi-Asset Support**: Handles BTC, BNFCR, USDT, and other assets correctly

#### Previous vs Current:
- **Old Method**: `totalWalletBalance + totalUnrealizedProfit` (~$400k, 5% error)
- **New Method**: Asset-by-asset conversion with margin balances (~$422k, 0.24% error)

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

### Log Retention
Configure log retention and cleanup settings:
```json
{
  "logging": {
    "database_logging": {
      "retention_days": 30,  // Keep logs for 30 days
      "max_entries": 1000000 // Maximum log entries
    }
  }
}
```
- Automatic daily cleanup removes logs older than retention period
- Reduces Supabase bandwidth usage by ~90%
- Cleanup runs after each monitoring cycle (once per day)

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

#### Available Environment Variables
```bash
# Database Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Demo Mode (for safe testing)
DEMO_MODE=true  # Enables mock data and safe testing

# Logging Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
MAX_LOG_ENTRIES=10000  # Maximum logs in memory
```

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

**"NameError: name 'new_eth_units' is not defined"**
- Fixed in v2025-07-09: Variable name bug in rebalancing function
- Update to latest version if encountering this error
- Affects accounts when rebalancing is triggered

**"value too long for type character varying(50)"**
- Fixed in v2025-07-09: Transaction ID column too small
- Run migration: `sql/fix_transaction_id_length.sql`
- Some Binance transaction IDs exceed 50 characters

### Debug Mode
Add debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Logging & Dashboard Troubleshooting

**"Dashboard not loading"**
```bash
# Check if dashboard server is running
python -m api.dashboard

# Check log files
ls -la logs/
tail -f logs/monitor.log
```

**"No logs showing"**
```bash
# Check if logging is enabled
python -c "from api.logger import get_logger; print(get_logger().get_performance_metrics())"

# Check log files exist
cat logs/monitor_logs.jsonl | jq '.'
```

**"Demo mode not working"**
```bash
# Ensure demo mode is enabled
export DEMO_MODE=true
python demo_test.py

# Check demo controller
python -c "from api.demo_mode import get_demo_controller; print(get_demo_controller().is_demo_mode())"
```

## 📚 Documentation

- **[📖 Setup Guide](./docs/SETUP_GUIDE.md)** - Complete installation and configuration
- **[📊 Dashboard & Logging Guide](./docs/DASHBOARD_GUIDE.md)** - Web dashboard, logging system, and demo mode
- **[🔧 API Reference](./docs/API_REFERENCE.md)** - Technical documentation  
- **[🚀 Deployment Guide](./docs/DEPLOYMENT_GUIDE.md)** - Production deployment
- **[📋 Project Roadmap](./PROJECT_ROADMAP.md)** - Development progress

## ⚡ Quick Links

- **[Live Demo](https://your-demo.vercel.app)** *(Coming Soon)*
- **[Issues](https://github.com/your-username/binance-portfolio-monitor/issues)** - Bug reports & feature requests
- **[Discussions](https://github.com/your-username/binance-portfolio-monitor/discussions)** - Community chat

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](./CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## ⚠️ Disclaimer

This project is for educational and research purposes. 
- Not financial advice
- Use at your own risk
- Ensure compliance with Binance API terms
- Always test with small amounts first

## 🆘 Support & Community

- **[📖 Documentation](./docs/)** - Comprehensive guides
- **[❓ Issues](https://github.com/your-username/binance-portfolio-monitor/issues)** - Bug reports
- **[💬 Discussions](https://github.com/your-username/binance-portfolio-monitor/discussions)** - Questions & ideas
- **[📧 Email](mailto:your-email@domain.com)** - Direct contact

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=your-username/binance-portfolio-monitor&type=Date)](https://star-history.com/#your-username/binance-portfolio-monitor&Date)

---

**Made with ❤️ for the crypto community | Happy Trading! 📈**