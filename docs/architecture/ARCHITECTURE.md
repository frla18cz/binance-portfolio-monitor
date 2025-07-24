# Binance Portfolio Monitor - Architecture

## 🎯 Component Roles - What Does What?

### Quick Summary:
- **`run_forever.py`** = ⏰ **SCHEDULER** (Timer/Cron) - Says WHEN to run
- **`api/index.py`** = 👷 **WORKER** (Data Collector) - Does the ACTUAL WORK
- **`api/dashboard.py`** = 📊 **PRESENTER** (Web UI) - Shows the RESULTS

### Analogy:
```
run_forever.py = ALARM CLOCK (rings every hour)
api/index.py   = EMPLOYEE (does the job when alarm rings)
dashboard.py   = DISPLAY WINDOW (shows what employee produced)
```

## System Overview

The Binance Portfolio Monitor consists of three main components that work together to track cryptocurrency portfolio performance:

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS EC2 Instance                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Screen Session (monitor)                │    │
│  │                                                      │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │         deployment/aws/run_forever.py         │  │    │
│  │  │         (Orchestrator - runs 24/7)            │  │    │
│  │  │                                               │  │    │
│  │  │  - Runs monitoring every hour                 │  │    │
│  │  │  - Manages process lifecycle                  │  │    │
│  │  │  - Handles logging and errors                 │  │    │
│  │  └───────────────┬───────────────┬──────────────┘  │    │
│  │                  │               │                  │    │
│  │          Every hour      Once at startup           │    │
│  │                  │               │                  │    │
│  │    ┌─────────────▼───────┐ ┌────▼──────────────┐  │    │
│  │    │    api/index.py     │ │ api/dashboard.py  │  │    │
│  │    │ (Data Collection)   │ │  (Web Server)     │  │    │
│  │    │                     │ │                   │  │    │
│  │    │ - Fetch from Binance│ │ - Port 8000      │  │    │
│  │    │ - Calculate NAV     │ │ - Auto-refresh   │  │    │
│  │    │ - Update benchmark  │ │ - Read-only view │  │    │
│  │    │ - Save to DB       │ │                   │  │    │
│  │    └─────────────────────┘ └───────────────────┘  │    │
│  │                  │               │                  │    │
│  └──────────────────┼───────────────┼──────────────────┘    │
│                     │               │                        │
│                     ▼               ▼                        │
│         ┌───────────────────────────────────┐               │
│         │        Supabase Database          │               │
│         │                                   │               │
│         │  Tables:                          │               │
│         │  - binance_accounts               │               │
│         │  - benchmark_configs              │               │
│         │  - nav_history                    │               │
│         │  - price_history                  │               │
│         │  - system_logs                    │               │
│         └───────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. **run_forever.py** (⏰ SCHEDULER - Just a Timer)
- **What it is**: A simple infinite loop with a timer
- **What it does**: 
  - Waits for the clock to hit the hour (e.g., 14:00, 15:00)
  - Runs `python -m api.index` when it's time
  - That's it! Just scheduling, no data processing
- **What it DOESN'T do**:
  - ❌ Doesn't connect to Binance
  - ❌ Doesn't calculate anything
  - ❌ Doesn't know what NAV or benchmark is
- **Real-world analogy**: Like a cron job or Windows Task Scheduler

### 2. **api/index.py** (👷 WORKER - Does ALL the Work)
- **What it is**: The brain of the operation - contains all business logic
- **What it does**:
  - ✅ Connects to Binance API
  - ✅ Fetches account balances and prices
  - ✅ Calculates NAV (Net Asset Value)
  - ✅ Updates benchmark portfolio
  - ✅ Saves everything to database
  - ✅ All the actual monitoring work!
- **How it's called**:
  - By `run_forever.py` every hour: `python -m api.index`
  - Can also run manually for testing
- **Real-world analogy**: Like an employee who comes in, does their job, then leaves

### 3. **api/dashboard.py** (📊 PRESENTER - Just Shows Data)
- **What it is**: A web server that displays results
- **What it does**:
  - ✅ Reads data from database
  - ✅ Shows pretty charts and numbers
  - ✅ Auto-refreshes every 60 seconds
  - ✅ That's it - just displays, never modifies
- **What it DOESN'T do**:
  - ❌ Doesn't collect data from Binance
  - ❌ Doesn't calculate anything
  - ❌ Doesn't save anything
- **Real-world analogy**: Like a TV screen showing stock prices - displays but doesn't trade

## Data Flow - Step by Step

### What Happens Every Hour:
```
1. run_forever.py: "It's 14:00! Time to work!"
                            ↓
2. Starts: python -m api.index
                            ↓
3. api/index.py: "OK boss, I'll do the monitoring"
   - Connects to Binance
   - Gets prices & balances
   - Calculates everything
   - Saves to database
   - "Done! See you next hour"
                            ↓
4. run_forever.py: "Great, I'll wake you at 15:00"
```

### What Dashboard Does (Always):
```
Browser: "Show me the data"
           ↓
dashboard.py: "Let me check the database"
           ↓
Database: "Here's the latest data"
           ↓
dashboard.py: "Here's a pretty chart"
           ↓
(wait 60 seconds and repeat)
```

## Database Schema

### Core Tables:
- **binance_accounts**: Trading account credentials and configuration
- **benchmark_configs**: BTC/ETH units for benchmark calculation
- **nav_history**: Time series of NAV and benchmark values
- **price_history**: Historical BTC/ETH prices
- **processed_transactions**: Deposits/withdrawals tracking
- **system_logs**: Application logs and debugging

### Data Relationships:
```
binance_accounts (1) ←→ (1) benchmark_configs
       ↓
       └→ (many) nav_history
       └→ (many) processed_transactions
```

## Key Design Decisions

1. **Process Separation**: Dashboard and monitoring run as independent processes
   - Dashboard crash doesn't affect monitoring
   - Can restart dashboard without losing monitoring

2. **Hourly Schedule**: Reduces data volume while maintaining useful granularity
   - 24 data points per day instead of 720 (every 2 minutes)
   - Aligns with typical trading analysis timeframes

3. **Database-Centric Communication**: All components communicate via database
   - No direct process communication needed
   - State persists across restarts
   - Multiple instances could theoretically run

4. **Benchmark Independence**: Benchmark evolves separately from portfolio
   - Represents "what if" scenario of holding 50/50 BTC/ETH
   - Adjusts for deposits/withdrawals to maintain fair comparison

## Error Handling

- **Monitoring Failures**: Logged but don't stop the orchestrator
- **Dashboard Crashes**: Automatically restarted on next monitoring run
- **API Timeouts**: 5-minute limit prevents hanging
- **Database Errors**: Retried with exponential backoff

## Security Considerations

- API keys stored in database (encrypted at rest by Supabase)
- Dashboard is read-only (no write operations)
- No authentication on dashboard (use SSH tunnel for remote access)
- Binance API keys should be read-only