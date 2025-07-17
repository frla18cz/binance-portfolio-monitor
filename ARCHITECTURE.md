# Binance Portfolio Monitor - Architecture

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

### 1. **run_forever.py** (Orchestrator)
- **Purpose**: Manages the lifecycle of monitoring and dashboard processes
- **Responsibilities**:
  - Starts dashboard on launch
  - Runs monitoring every hour on the hour
  - Handles graceful shutdown (SIGINT/SIGTERM)
  - Logs all activities to `logs/continuous_runner.log`
- **Key Features**:
  - Calculates next run time to align with clock hours
  - 5-minute timeout for monitoring runs
  - Continues running even if individual monitoring fails

### 2. **api/index.py** (Data Collection Worker)
- **Purpose**: Core business logic for portfolio monitoring
- **Execution Modes**:
  - **Module mode**: `python -m api.index` runs `process_all_accounts()`
  - **HTTP mode**: Provides `APIHandler` for web endpoints (used by Vercel)
- **Key Functions**:
  - `ensure_benchmark_configs()`: Creates missing benchmark configurations
  - `process_all_accounts()`: Main orchestration function
  - `process_single_account()`: Processes one trading account
  - `get_comprehensive_nav()`: Calculates total portfolio value
  - `initialize_benchmark()`: Sets up 50/50 BTC/ETH benchmark
  - `process_deposits_withdrawals()`: Handles cashflow events

### 3. **api/dashboard.py** (Web Interface)
- **Purpose**: Provides real-time view of portfolio performance
- **Features**:
  - HTTP server on port 8000
  - Serves `dashboard.html` with embedded JavaScript
  - Auto-refreshes every 60 seconds
  - Shows NAV vs Benchmark performance charts
- **Data Flow**:
  - Reads from Supabase (never writes)
  - Transforms data for visualization
  - Returns JSON for AJAX requests

## Data Flow

1. **Hourly Monitoring Cycle**:
   ```
   run_forever.py → subprocess → api.index.py → Binance API
                                      ↓
                                  Calculate NAV
                                      ↓
                                  Update Benchmark
                                      ↓
                                  Save to Supabase
   ```

2. **Dashboard Data Flow**:
   ```
   Browser → api/dashboard.py → Read from Supabase → JSON Response
      ↑                                                    ↓
      └──────── Auto-refresh every 60s ←─────────────────┘
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