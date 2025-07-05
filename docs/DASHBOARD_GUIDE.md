# 📊 Dashboard & Logging Guide

**Complete guide to the web dashboard and advanced logging system for the Binance Portfolio Monitor.**

## 🎯 Overview

The dashboard provides real-time monitoring capabilities with comprehensive logging:

- **📈 Real-time Portfolio Monitoring** - Live NAV vs benchmark tracking
- **📋 Structured Logging System** - Detailed operation logs with performance metrics  
- **⚡ Performance Analytics** - Success rates, timing, and error tracking
- **🔍 Advanced Filtering** - Search logs by category, account, or level

## 🌐 Web Dashboard

### Starting the Dashboard

```bash
python -m api.dashboard
# Open browser to: http://localhost:8000/dashboard
```

### Dashboard Features

#### 📊 Portfolio Overview
- **Current NAV** - Real-time account value from live Binance API
- **Benchmark Value** - 50/50 BTC/ETH portfolio value
- **Performance vs Benchmark** - Outperformance tracking
- **Total Return** - Absolute and percentage returns

#### 📈 Performance Metrics
- **Operation Success Rate** - System reliability metrics
- **Average Duration** - Performance timing statistics
- **Failed Operations** - Error tracking and alerts
- **Session Statistics** - Current monitoring session data

#### 💰 Current Market Data
- **BTC/ETH Prices** - Real-time cryptocurrency prices from Binance API
- **Last Updated** - Data freshness indicators
- **Price Change Indicators** - Market movement tracking

#### ⚙️ System Status
- **Monitoring Status** - Active/inactive system state
- **Database Connection** - Connection health monitoring
- **API Connection** - Binance API connectivity status
- **Last Run Time** - Most recent processing timestamp

#### 📋 Real-time Logs
- **Live Log Stream** - Real-time operation logging
- **Category Filtering** - Filter by operation type
- **Level Filtering** - Focus on errors, warnings, or info
- **Account Filtering** - View logs for specific accounts
- **Export Functionality** - Download logs for analysis

#### 📊 Performance Charts
- **NAV vs Benchmark Chart** - Historical performance comparison
- **Interactive Timeline** - Zoom and pan through history
- **Multiple Data Series** - Portfolio and benchmark overlay

### Dashboard Controls

#### Manual Operations
```javascript
// Refresh all dashboard data
refreshData()

// Toggle auto-refresh (30-second intervals)
toggleAutoRefresh()

// Manually trigger monitoring process
runMonitoring()

// Export logs to file
exportLogs()
```

#### Filter Controls
```javascript
// Filter logs by category
filterLogs('account_processing')  // or 'api_call', 'database', etc.
filterLogs('ERROR')              // Show only errors
filterLogs('all')                // Show all logs

// Clear log display
clearLogs()
```

## 🎮 Demo Mode

Demo mode provides a safe and isolated environment for testing the monitoring system without interacting with real funds or live API endpoints. All data in demo mode is simulated.

### Enabling Demo Mode

To enable demo mode, use the `--mode demo` argument when starting the dashboard:

```bash
python -m api.dashboard --mode demo
```

Alternatively, you can still use the `DEMO_MODE` environment variable:

```bash
# Environment variable
export DEMO_MODE=true

# Or in .env file
DEMO_MODE=true
```

To switch back to live mode, use `--mode live` or ensure `DEMO_MODE` is not set to `true`.

### Demo Mode Features

#### Safe Testing Environment
- **No Real Money Risk** - All operations use mock data
- **Complete System Testing** - Full monitoring workflow simulation
- **Real-time Feedback** - Immediate results from simulated operations

#### Transaction Simulation
```bash
# Via dashboard buttons or API calls
POST /api/dashboard/simulate-transaction
{
  "type": "DEPOSIT",
  "amount": 5000.0,
  "account_id": 1
}
```

**Available Transaction Types:**
- `DEPOSIT` - Add funds to account simulation
- `WITHDRAWAL` - Remove funds from account simulation

#### Market Scenario Testing
```bash
# Simulate different market conditions
POST /api/dashboard/simulate-scenario
{
  "scenario": "bull_run"
}
```

**Available Scenarios:**
- **`bull_run`** - +15% BTC, +20% ETH
- **`bear_market`** - -20% BTC, -25% ETH  
- **`btc_dominance`** - +10% BTC, -5% ETH
- **`eth_surge`** - +2% BTC, +25% ETH
- **`crash`** - -30% BTC, -35% ETH
- **`sideways`** - ±2% random movement

#### Demo Data Management
```python
# Reset to initial state
from api.demo_mode import reset_demo_data
result = reset_demo_data()

# Get comprehensive demo data
from api.demo_mode import get_demo_dashboard_data
data = get_demo_dashboard_data()
```

### Demo Mode Testing Workflow

1. **Start Dashboard in Demo Mode**
   ```bash
   python -m api.dashboard --mode demo
   # Open: http://localhost:8000/dashboard
   ```

2. **Test Transactions**
   - Use dashboard buttons to simulate deposits/withdrawals
   - Observe portfolio impact in real-time
   - Check logs for operation details

3. **Test Market Scenarios**
   - Apply different market conditions
   - Monitor benchmark adjustments
   - Analyze performance impact

4. **Test Full Monitoring**
   ```bash
   # Run complete monitoring cycle (will use demo mode if dashboard is in demo mode)
   python api/index.py
   ```

## 📋 Advanced Logging System

### Logging Architecture

#### Structured JSON Logging
Every operation creates a structured log entry:

```json
{
  "timestamp": "2025-07-04T13:21:55.736280+00:00",
  "level": "INFO",
  "category": "account_processing",
  "account_id": 1,
  "account_name": "Demo Trading Account",
  "operation": "process_account",
  "message": "Successfully processed account",
  "data": {"nav": 19000.00, "benchmark": 14603.09},
  "duration_ms": 4.46,
  "success": true,
  "error": null
}
```

#### Log Categories
- **`system`** - System-level operations and startup
- **`account_processing`** - Account processing workflows
- **`api_call`** - Binance API interactions and responses
- **`database`** - Database operations and queries
- **`benchmark`** - Benchmark calculations and updates
- **`transaction`** - Deposit/withdrawal processing
- **`price_update`** - Market price fetching
- **`rebalancing`** - Portfolio rebalancing operations
- **`demo_mode`** - Demo mode testing operations

#### Log Levels
- **`DEBUG`** - Detailed diagnostic information
- **`INFO`** - General operational information
- **`WARNING`** - Warning conditions that don't prevent operation
- **`ERROR`** - Error conditions that may affect operation
- **`CRITICAL`** - Critical errors that may stop operation

### Using the Logging System

#### Basic Logging
```python
from api.logger import get_logger, LogCategory

logger = get_logger()

# Info logging with context
logger.info(LogCategory.ACCOUNT_PROCESSING, "start_processing", 
           "Starting account processing",
           account_id=1, account_name="Demo Account",
           data={"initial_nav": 10000.0})

# Error logging with details
logger.error(LogCategory.API_CALL, "binance_error", 
            "Failed to fetch account NAV",
            account_id=1, error="Connection timeout")
```

#### Performance Timing
```python
from api.logger import OperationTimer

# Automatic timing with context manager
with OperationTimer(logger, LogCategory.API_CALL, "fetch_prices", account_id, account_name):
    prices = get_prices(binance_client)
    # Automatically logs duration and success/failure
```

#### Retrieving Logs
```python
# Get recent logs with filtering
recent_logs = logger.get_recent_logs(
    limit=100, 
    category="account_processing", 
    account_id=1
)

# Get error logs from last 24 hours
error_logs = logger.get_error_logs(hours=24)

# Get performance metrics
metrics = logger.get_performance_metrics()
print(f"Success rate: {metrics['success_rate']:.1f}%")

# Get account-specific summary
summary = logger.get_account_summary(account_id=1)
```

### Log File Management

#### File Locations
```
logs/
├── monitor.log          # Standard log format
└── monitor_logs.jsonl   # Structured JSON logs
```

#### Log Rotation
- **Memory Management** - Keeps last 10,000 entries in memory
- **File Persistence** - All logs saved to disk
- **JSON Format** - Structured data for analysis

#### Accessing Log Files
```bash
# View recent structured logs
tail -f logs/monitor_logs.jsonl

# View standard logs
tail -f logs/monitor.log

# Parse JSON logs with jq
cat logs/monitor_logs.jsonl | jq '.message'

# Filter errors
cat logs/monitor_logs.jsonl | jq 'select(.level=="ERROR")'

# Get performance data
cat logs/monitor_logs.jsonl | jq 'select(.duration_ms != null) | .duration_ms'
```

## 📊 Performance Monitoring

### Key Metrics

#### System Performance
- **Total Operations** - Count of all logged operations
- **Success Rate** - Percentage of successful operations
- **Average Duration** - Mean operation execution time
- **Failed Operations** - Count and details of failures

#### Operation Categories
- **Account Processing** - Account workflow performance
- **API Calls** - Binance API interaction metrics
- **Database Operations** - Database query performance
- **Price Updates** - Market data fetch timing

#### Account-Specific Metrics
- **Processing Success Rate** - Per-account reliability
- **Operation Count** - Activity level per account
- **Recent Activities** - Latest operations timeline
- **Error History** - Account-specific error tracking

### Dashboard Analytics

#### Real-time Metrics Display
The dashboard automatically calculates and displays:

```javascript
// Performance overview
{
  "total_operations": 45,
  "successful_operations": 43,
  "failed_operations": 2,
  "success_rate": 95.6,
  "avg_duration_ms": 1250,
  "operations_by_category": {
    "account_processing": 12,
    "api_call": 18,
    "database": 15
  }
}
```

#### Historical Analysis
- **Success Rate Trends** - Track reliability over time
- **Performance Trends** - Monitor operation speed
- **Error Pattern Analysis** - Identify recurring issues
- **Category Performance** - Compare different operation types

## 🔧 Configuration

### Environment Variables

```bash
# Demo Mode
DEMO_MODE=false          # true = safe testing, false = live mode

# Logging Configuration
LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR, CRITICAL
MAX_LOG_ENTRIES=10000    # Maximum logs kept in memory

# Dashboard Configuration
DASHBOARD_PORT=8000      # Dashboard server port
AUTO_REFRESH=true        # Enable auto-refresh in dashboard
```

### Dashboard Customization

#### Refresh Intervals
```javascript
// Default auto-refresh: 30 seconds
const AUTO_REFRESH_INTERVAL = 30000;

// Manual refresh
refreshData();

// Toggle auto-refresh
toggleAutoRefresh();
```

#### Chart Configuration
```javascript
// Performance chart settings
const chartConfig = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: {
      beginAtZero: false,
      ticks: {
        callback: function(value) {
          return '$' + value.toLocaleString();
        }
      }
    }
  }
};
```

## 🐛 Troubleshooting

### Common Issues

#### Dashboard Not Loading
```bash
# Check if server is running
python -m api.dashboard

# Check port availability
netstat -an | grep 8000

# Check logs for errors
tail -f logs/monitor.log
```

#### No Logs Appearing
```bash
# Verify logging system
python -c "from api.logger import get_logger; print(get_logger().get_performance_metrics())"

# Check log files exist
ls -la logs/

# Test log creation
python -c "from api.logger import get_logger, LogCategory; get_logger().info(LogCategory.SYSTEM, 'test', 'Test message')"
```

#### Demo Mode Not Working
```bash
# Verify demo mode setting
python -c "from api.demo_mode import get_demo_controller; print(get_demo_controller().is_demo_mode())"

# Check demo data
python -c "from api.demo_mode import get_demo_dashboard_data; print(get_demo_dashboard_data())"

# Reset demo data
python -c "from api.demo_mode import reset_demo_data; print(reset_demo_data())"
```

### Debug Mode

#### Enable Debug Logging
```bash
# In .env file
LOG_LEVEL=DEBUG

# Or programmatically
export LOG_LEVEL=DEBUG
python api/index.py
```

#### Dashboard Debugging
```bash
# Check API endpoints manually
curl http://localhost:8000/api/dashboard/status
curl http://localhost:8000/api/dashboard/logs
curl http://localhost:8000/api/dashboard/metrics

# Test demo mode endpoints
curl -X POST http://localhost:8000/api/dashboard/simulate-transaction \
  -H "Content-Type: application/json" \
  -d '{"type":"DEPOSIT","amount":1000}'
```

## 📈 Best Practices

### Monitoring Strategy
1. **Start with Demo Mode** - Test all functionality safely
2. **Monitor Dashboard Regularly** - Check system health
3. **Review Error Logs** - Address issues promptly
4. **Track Performance Trends** - Optimize over time
5. **Export Logs Periodically** - Archive for compliance

### Log Analysis
1. **Filter by Category** - Focus on specific operations
2. **Monitor Success Rates** - Track system reliability
3. **Analyze Performance** - Identify bottlenecks
4. **Review Error Patterns** - Prevent recurring issues
5. **Account-Specific Tracking** - Monitor individual accounts

### Dashboard Usage
1. **Use Auto-Refresh** - Stay updated automatically
2. **Filter Logs Strategically** - Find relevant information
3. **Export Data Regularly** - Maintain historical records
4. **Test in Demo Mode** - Validate changes safely
5. **Monitor Real-time Charts** - Track performance visually

---

**The dashboard and logging system provide comprehensive visibility into your portfolio monitoring operations, enabling confident operation and continuous improvement.**