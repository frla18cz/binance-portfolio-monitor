# 🚀 Setup Guide - Binance Portfolio Monitor

**Complete step-by-step guide to get your portfolio monitoring system up and running.**

## 📋 Prerequisites Checklist

Before starting, make sure you have:

- [ ] **Binance Account** with futures trading enabled
- [ ] **Python 3.13+** installed on your system
- [ ] **Supabase Account** (free tier is sufficient)
- [ ] **Git** installed for version control
- [ ] **Code Editor** (VS Code, PyCharm, etc.)

## 🏗️ Step 1: Project Setup

### Clone the Repository
```bash
git clone https://github.com/your-username/binance_monitor_playground.git
cd binance_monitor_playground
```

### Create Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### Install Dependencies
```bash
pip install python-dotenv supabase python-binance
```

## 🔑 Step 2: Binance API Setup

### Create API Key
1. Log into your **Binance account**
2. Go to **API Management** in your profile
3. Click **Create API**
4. Name it `Portfolio Monitor`
5. **Complete verification** (SMS/Email)

### Configure API Permissions
⚠️ **IMPORTANT**: Set ONLY these permissions:
- ✅ **Enable Reading** - For account data
- ❌ **Enable Spot & Margin Trading** - Not needed
- ❌ **Enable Futures** - Not needed for monitoring
- ❌ **Enable Withdrawals** - NEVER enable for monitoring

### Save Your Keys
```bash
# Copy these immediately - you'll need them later
API Key: abcd1234...
Secret Key: xyz9876...
```

## 🗄️ Step 3: Supabase Database Setup

### Create Supabase Project
1. Go to [supabase.com](https://supabase.com)
2. Click **Start your project**
3. Create new project: `binance-monitor`
4. Choose region closest to you
5. Set strong database password

### Create Database Tables
Open **SQL Editor** in Supabase and run this script:

```sql
-- 1. Binance account credentials
CREATE TABLE binance_accounts (
    id SERIAL PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL,
    api_key TEXT NOT NULL,
    api_secret TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Benchmark configuration per account
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

-- 3. Historical NAV and benchmark data
CREATE TABLE nav_history (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES binance_accounts(id),
    timestamp TIMESTAMPTZ NOT NULL,
    nav DECIMAL(20,2) NOT NULL,
    benchmark_value DECIMAL(20,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Transaction processing tracking (prevents duplicates)
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

-- 5. Processing status per account
CREATE TABLE account_processing_status (
    account_id INTEGER PRIMARY KEY REFERENCES binance_accounts(id),
    last_processed_timestamp TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Get Supabase Credentials
1. Go to **Settings** → **API**
2. Copy these values:
   - **Project URL**: `https://xyz.supabase.co`
   - **Anon public key**: `eyJ0...`
   - **Service role key**: `eyJ0...` (optional, for enhanced security)

## ⚙️ Step 4: Environment Configuration

### Create .env File
In your project root, create `.env`:
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# Optional: For enhanced security
# SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# Demo Mode (for safe testing)
DEMO_MODE=false  # Set to 'true' for risk-free testing with mock data

# Logging Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
MAX_LOG_ENTRIES=10000  # Maximum logs kept in memory
```

### Add to .gitignore
Make sure `.env` is in your `.gitignore`:
```bash
echo ".env" >> .gitignore
```

## 📊 Step 5: Add Your Trading Account

### Insert Account Data
Run this SQL in Supabase **SQL Editor**:
```sql
-- Replace with your actual API credentials
INSERT INTO binance_accounts (account_name, api_key, api_secret) 
VALUES ('My Main Account', 'your-binance-api-key', 'your-binance-api-secret');

-- Create benchmark configuration
INSERT INTO benchmark_configs (account_id, rebalance_day, rebalance_hour)
VALUES (1, 0, 12); -- Rebalance Mondays at 12:00 PM
```

### Verify Data
```sql
-- Check if account was added
SELECT * FROM binance_accounts;

-- Check benchmark config
SELECT * FROM benchmark_configs;
```

## 🧪 Step 6: Test Your Setup

### Safe Demo Mode Testing (Recommended First)
```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Run safe demo mode test
export DEMO_MODE=true  # or set DEMO_MODE=true on Windows
python demo_test.py
```

### Web Dashboard Testing
```bash
# Start the dashboard server
python -m api.dashboard

# Open browser to: http://localhost:8000/dashboard
# Use the dashboard interface to monitor and test the system
```

### Production Test
```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Run the monitor with real data (ensure DEMO_MODE=false in .env)
python api/index.py
```

### Expected Output
```
Running script locally for testing...
Found 1 accounts to process.
--- Processing account: My Main Account ---
Benchmark not initialized. Initializing now...
Initializing benchmark with NAV: 15000.00
Benchmark initialized. Next rebalance: 2025-07-07 12:00:00
Processing 0 new transactions...
2025-07-02T12:00:00+00:00 | NAV: 15000.00 | Benchmark: 15000.00
```

### If You See Errors

**"No accounts found"**
```sql
-- Check if your account exists
SELECT COUNT(*) FROM binance_accounts;
```

**"API Error"**
- Verify API key/secret are correct
- Check API permissions (reading enabled)
- Ensure futures account has balance

**"Database Error"**
- Verify Supabase URL and key
- Check if all tables were created
- Test connection in Supabase dashboard

## 📈 Step 7: Verify Data Collection

### Check Historical Data
After successful run, verify data was saved:
```sql
-- Check NAV history
SELECT 
    ba.account_name,
    nh.timestamp,
    nh.nav,
    nh.benchmark_value,
    (nh.nav - nh.benchmark_value) as difference
FROM nav_history nh
JOIN binance_accounts ba ON nh.account_id = ba.id
ORDER BY nh.timestamp DESC
LIMIT 5;
```

### Check Benchmark Initialization
```sql
-- Verify benchmark was set up
SELECT 
    ba.account_name,
    bc.btc_units,
    bc.eth_units,
    bc.next_rebalance_timestamp
FROM benchmark_configs bc
JOIN binance_accounts ba ON bc.account_id = ba.id;
```

## 🔄 Step 8: Automated Monitoring

### Local Cron Job (macOS/Linux)
```bash
# Edit crontab
crontab -e

# Add this line to run every hour:
0 * * * * cd /path/to/binance_monitor_playground && source .venv/bin/activate && python api/index.py >> monitor.log 2>&1
```

### Windows Task Scheduler
1. Open **Task Scheduler**
2. Create **Basic Task**
3. Trigger: **Daily**, repeat every **1 hour**
4. Action: **Start a program**
   - Program: `python`
   - Arguments: `api/index.py`
   - Start in: `C:\path\to\binance_monitor_playground`

### Cloud Deployment (Optional)
See `DEPLOYMENT_GUIDE.md` for Vercel deployment instructions.

## 🎯 Step 9: Customization

### Multiple Accounts
Add more trading accounts:
```sql
INSERT INTO binance_accounts (account_name, api_key, api_secret) 
VALUES 
    ('Conservative Strategy', 'api-key-2', 'secret-2'),
    ('High Risk Strategy', 'api-key-3', 'secret-3');

-- Add benchmark configs for each
INSERT INTO benchmark_configs (account_id, rebalance_day, rebalance_hour)
VALUES 
    (2, 1, 9),  -- Tuesday at 9 AM
    (3, 5, 15); -- Friday at 3 PM
```

### Rebalancing Schedule
Change when benchmark rebalances:
```sql
UPDATE benchmark_configs SET 
    rebalance_day = 6,  -- Sunday
    rebalance_hour = 18 -- 6 PM
WHERE account_id = 1;
```

Days: 0=Monday, 1=Tuesday, ..., 6=Sunday

## 🔐 Security Checklist

- [ ] **API keys** have minimal permissions (read-only)
- [ ] **Environment variables** are not committed to git
- [ ] **Database credentials** are secure
- [ ] **API keys** are different for each environment
- [ ] **Regular monitoring** of API key usage

## 📊 Data Analysis

### Performance Dashboard Query
```sql
-- 30-day performance comparison
WITH daily_performance AS (
    SELECT 
        DATE(timestamp) as date,
        AVG(nav) as nav,
        AVG(benchmark_value) as benchmark
    FROM nav_history 
    WHERE account_id = 1 
      AND timestamp >= NOW() - INTERVAL '30 days'
    GROUP BY DATE(timestamp)
)
SELECT 
    date,
    nav,
    benchmark,
    nav - benchmark as difference,
    ROUND(((nav - benchmark) / benchmark * 100), 2) as outperformance_pct
FROM daily_performance
ORDER BY date DESC;
```

## 🆘 Troubleshooting

### Common Issues and Solutions

**Issue**: "Error getting NAV: Signature for this request is not valid"
**Solution**: 
- Check API key and secret are correct
- Verify system time is synchronized
- Ensure API key has required permissions

**Issue**: "Error processing deposits/withdrawals"
**Solution**:
- Check if processed_transactions table exists
- Verify Binance deposit/withdrawal history API access
- Check for rate limiting

**Issue**: Benchmark not updating after deposits
**Solution**:
- Verify processed_transactions table is working
- Check if deposits are showing in Binance API
- Review transaction processing logs

### Advanced Logging & Debugging

The system includes comprehensive logging capabilities:

#### Check Log Files
```bash
# View recent structured logs
tail -f logs/monitor_logs.jsonl

# View standard logs
tail -f logs/monitor.log

# Check log directory
ls -la logs/
```

#### Dashboard Debugging
```bash
# Start dashboard with debugging
python -m api.dashboard

# Check dashboard API endpoints
curl http://localhost:8000/api/dashboard/status
curl http://localhost:8000/api/dashboard/logs
curl http://localhost:8000/api/dashboard/metrics
```

#### Demo Mode Debugging
```bash
# Test demo mode controller
python -c "from api.demo_mode import get_demo_controller; print(get_demo_controller().get_mode_status())"

# Test mock data
python -c "from api.mock_mode import get_mock_manager; print(get_mock_manager().get_performance_summary(1))"

# Reset demo data
python -c "from api.demo_mode import reset_demo_data; print(reset_demo_data())"
```

#### Enable Debug Level Logging
Set in `.env` file:
```bash
LOG_LEVEL=DEBUG
```

Or enable programmatically:
```python
# Add to top of api/index.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Get Help
1. **Check logs** for specific error messages
2. **Review API documentation** at [binance-docs.github.io](https://binance-docs.github.io/)
3. **Verify database** tables and data
4. **Test API keys** manually with simple requests

## ✅ Success Checklist

After setup, you should have:
- [ ] Monitor running without errors
- [ ] NAV data being collected hourly
- [ ] Benchmark properly initialized
- [ ] Historical data accumulating
- [ ] Deposit/withdrawal tracking working
- [ ] Rebalancing scheduled correctly
- [ ] **Web dashboard accessible** at `http://localhost:8000/dashboard`
- [ ] **Structured logging working** (check `logs/` directory)
- [ ] **Demo mode functioning** for safe testing
- [ ] **Performance metrics** showing in dashboard

**Congratulations! Your portfolio monitoring system is now active! 🎉**

## 📚 Next Steps

1. **Monitor for a week** to ensure stability
2. **Review historical data** for insights
3. **Consider deployment** to cloud for 24/7 monitoring
4. **Add alerts** for significant performance deviations
5. **Create dashboards** for visualization

---

**Happy Monitoring! 📈**