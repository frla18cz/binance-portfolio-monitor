# 📡 API Reference - Binance Portfolio Monitor

**Complete technical documentation for the Binance Portfolio Monitor API and functions.**

## 🌐 HTTP API Endpoints

### Main Monitoring Endpoint

**`GET /api/`**

Processes all registered Binance accounts and updates monitoring data.

#### Request
```http
GET /api/ HTTP/1.1
Host: your-app.vercel.app
```

#### Response

**Success (200)**
```http
HTTP/1.1 200 OK
Content-Type: text/plain

Monitoring process completed successfully.
```

**Error (500)**
```http
HTTP/1.1 500 Internal Server Error
Content-Type: text/plain

Error: [specific error message]
```

### Dashboard API Endpoints

#### System Status
**`GET /api/dashboard/status`**

Returns system status, mode information, and performance metrics.

```json
{
  "mode": {
    "mode": "DEMO",
    "safe_testing": true,
    "real_money": false,
    "warning": "All data is simulated"
  },
  "system": {
    "monitoring_active": true,
    "database_connected": true,
    "api_connected": true
  },
  "performance": {
    "total_operations": 45,
    "success_rate": 95.6,
    "avg_duration_ms": 1250
  }
}
```

#### Logs API
**`GET /api/dashboard/logs?limit=100&category=api_call&level=ERROR`**

Returns structured logs with optional filtering.

**Query Parameters:**
- `limit` (int): Maximum number of logs to return (default: 100)
- `category` (string): Filter by log category (system, account_processing, api_call, etc.)
- `account_id` (int): Filter by specific account ID
- `level` (string): Filter by log level (INFO, WARNING, ERROR, DEBUG)

```json
{
  "logs": [
    {
      "timestamp": "2025-07-04T13:21:55.736280+00:00",
      "level": "INFO",
      "category": "account_processing",
      "operation": "process_account",
      "message": "Successfully processed account: Demo Trading Account",
      "account_id": 1,
      "success": true,
      "duration_ms": 4.46
    }
  ],
  "total_count": 1,
  "filters": {
    "limit": 100,
    "category": "account_processing"
  }
}
```

#### Metrics API
**`GET /api/dashboard/metrics`**

Returns comprehensive performance and portfolio metrics.

```json
{
  "portfolio": {
    "current_nav": 13500.00,
    "benchmark_value": 12800.00,
    "vs_benchmark": 700.00,
    "return_percentage": 35.00
  },
  "prices": {
    "btc": 65420.50,
    "eth": 3245.75
  },
  "performance": {
    "total_operations": 45,
    "success_rate": 95.6,
    "operations_by_category": {
      "account_processing": 12,
      "api_call": 18,
      "database": 15
    }
  }
}
```

#### Manual Trigger
**`POST /api/dashboard/run-monitoring`**

Manually triggers the monitoring process.

```json
{
  "success": true,
  "message": "Monitoring process completed successfully",
  "timestamp": "2025-07-04T13:21:55.736280+00:00"
}
```

#### Transaction Simulation (Demo Mode)
**`POST /api/dashboard/simulate-transaction`**

```json
{
  "type": "DEPOSIT",
  "amount": 5000.0,
  "account_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "transaction_id": "MOCK_DEPOSIT_5",
  "new_balance": 21000.00,
  "new_nav": 21000.00,
  "performance_summary": {
    "current_nav": 21000.00,
    "total_return": 11000.00,
    "return_percentage": 110.00
  }
}
```

#### Market Scenario Simulation (Demo Mode)
**`POST /api/dashboard/simulate-scenario`**

```json
{
  "scenario": "bull_run"
}
```

**Available scenarios:** `bull_run`, `bear_market`, `btc_dominance`, `eth_surge`, `crash`, `sideways`

#### Web Dashboard
**`GET /dashboard`**

Serves the web dashboard interface with real-time monitoring capabilities.

#### Usage Examples

**cURL**
```bash
# Main monitoring
curl https://your-app.vercel.app/api/

# Dashboard status
curl https://your-app.vercel.app/api/dashboard/status

# Recent logs
curl "https://your-app.vercel.app/api/dashboard/logs?limit=50&level=ERROR"

# Trigger monitoring
curl -X POST https://your-app.vercel.app/api/dashboard/run-monitoring
```

**Python**
```python
import requests

# Get system status
response = requests.get("https://your-app.vercel.app/api/dashboard/status")
status = response.json()

# Get recent logs
response = requests.get("https://your-app.vercel.app/api/dashboard/logs", 
                       params={"limit": 100, "category": "account_processing"})
logs = response.json()

# Simulate transaction (demo mode)
response = requests.post("https://your-app.vercel.app/api/dashboard/simulate-transaction",
                        json={"type": "DEPOSIT", "amount": 5000.0})
result = response.json()
```

**JavaScript**
```javascript
// Get metrics
fetch('/api/dashboard/metrics')
  .then(response => response.json())
  .then(data => console.log(data));

// Trigger monitoring
fetch('/api/dashboard/run-monitoring', {method: 'POST'})
  .then(response => response.json())
  .then(data => console.log(data));
```

## 🔧 Core Functions Reference

### Account Processing Functions

#### `process_all_accounts()`
Main orchestration function that processes all registered accounts with comprehensive logging.

```python
def process_all_accounts() -> None
```

**Behavior:**
- Fetches all accounts from `binance_accounts` table
- Processes each account individually with error isolation
- **Comprehensive logging** of all operations with timing
- **Demo mode support** for safe testing

**Logging Features:**
- System-level operation timing
- Account-specific progress tracking
- Error details with full context
- Performance metrics collection

**Database Dependencies:**
- `binance_accounts` table with valid API credentials
- `benchmark_configs` table for each account

---

#### `process_single_account(account)`
Processes monitoring logic for a single Binance account.

```python
def process_single_account(account: dict) -> None
```

**Parameters:**
- `account` (dict): Account record from database containing:
  - `id`: Account ID
  - `account_name`: Display name
  - `api_key`: Binance API key
  - `api_secret`: Binance API secret
  - `benchmark_configs`: Related benchmark configuration

**Process Flow:**
1. Initialize Binance client
2. Fetch current market prices
3. Calculate account NAV
4. Process deposits/withdrawals
5. Handle benchmark rebalancing
6. Save historical snapshot

**Error Handling:**
- Individual account failures don't affect other accounts
- Returns gracefully on API errors
- Logs detailed error information

---

### Market Data Functions

#### `get_prices(client)`
Fetches current BTC and ETH prices from Binance.

```python
def get_prices(client: BinanceClient) -> dict | None
```

**Parameters:**
- `client`: Authenticated Binance client

**Returns:**
```python
{
    "BTCUSDT": 65000.50,
    "ETHUSDT": 3500.25
}
```

**Error Handling:**
- Returns `None` on API errors
- Logs error details for debugging

---

#### `get_futures_account_nav(client)`
Calculates current Net Asset Value of futures account.

```python
def get_futures_account_nav(client: BinanceClient) -> float | None
```

**Parameters:**
- `client`: Authenticated Binance client

**Returns:**
- `float`: Total NAV (wallet balance + unrealized PnL)
- `None`: On API errors

**Calculation:**
```python
nav = float(account_info['totalWalletBalance']) + float(account_info['totalUnrealizedProfit'])
```

---

### Benchmark Management Functions

#### `initialize_benchmark(db_client, config, account_id, initial_nav, prices)`
Sets up initial 50/50 BTC/ETH benchmark allocation.

```python
def initialize_benchmark(
    db_client: Client,
    config: dict,
    account_id: int,
    initial_nav: float,
    prices: dict
) -> dict
```

**Parameters:**
- `db_client`: Supabase client
- `config`: Current benchmark configuration
- `account_id`: Database account ID
- `initial_nav`: Current account NAV for initial allocation
- `prices`: Current BTC/ETH prices

**Logic:**
```python
investment = initial_nav / 2  # Split 50/50
btc_units = investment / prices['BTCUSDT']
eth_units = investment / prices['ETHUSDT']
```

**Returns:**
- Updated benchmark configuration with BTC/ETH units

---

#### `calculate_benchmark_value(config, prices)`
Calculates current value of benchmark portfolio.

```python
def calculate_benchmark_value(config: dict, prices: dict) -> float
```

**Parameters:**
- `config`: Benchmark configuration with BTC/ETH units
- `prices`: Current market prices

**Calculation:**
```python
btc_value = btc_units * prices['BTCUSDT']
eth_value = eth_units * prices['ETHUSDT']
return btc_value + eth_value
```

---

#### `rebalance_benchmark(db_client, config, account_id, current_value, prices)`
Rebalances benchmark back to 50/50 allocation.

```python
def rebalance_benchmark(
    db_client: Client,
    config: dict,
    account_id: int,
    current_value: float,
    prices: dict
) -> dict
```

**Trigger Conditions:**
- Current time >= `next_rebalance_timestamp`
- Configured rebalance day and hour reached

**Logic:**
```python
investment = current_value / 2  # Reset to 50/50
new_btc_units = investment / prices['BTCUSDT']
new_eth_units = investment / prices['ETHUSDT']
```

---

### Transaction Processing Functions

#### `process_deposits_withdrawals(db_client, binance_client, account_id, config, prices)`
Main function for handling deposit/withdrawal processing with idempotency.

```python
def process_deposits_withdrawals(
    db_client: Client,
    binance_client: BinanceClient,
    account_id: int,
    config: dict,
    prices: dict
) -> dict
```

**Features:**
- **Idempotent**: Never processes same transaction twice
- **Atomic**: All updates happen in single database transaction
- **Batch Processing**: Handles multiple transactions efficiently
- **Error Recovery**: Graceful handling of API failures

**Returns:**
- Updated benchmark configuration reflecting cashflow changes

---

#### `fetch_new_transactions(binance_client, start_time)`
Fetches new deposits and withdrawals from Binance API.

```python
def fetch_new_transactions(
    binance_client: BinanceClient, 
    start_time: str
) -> list[dict]
```

**Parameters:**
- `binance_client`: Authenticated Binance client
- `start_time`: ISO timestamp to fetch transactions from

**API Calls:**
- `client.get_deposit_history(startTime=timestamp)`
- `client.get_withdraw_history(startTime=timestamp)`

**Returns:**
```python
[
    {
        "id": "DEP_12345",
        "type": "DEPOSIT",
        "amount": 1000.0,
        "timestamp": "2025-07-02T12:00:00Z",
        "status": "SUCCESS"
    },
    {
        "id": "WD_67890", 
        "type": "WITHDRAWAL",
        "amount": 500.0,
        "timestamp": "2025-07-02T15:00:00Z",
        "status": "SUCCESS"
    }
]
```

---

#### `adjust_benchmark_for_cashflow(db_client, config, account_id, net_flow, prices, processed_txns)`
Adjusts benchmark allocation based on deposits/withdrawals.

```python
def adjust_benchmark_for_cashflow(
    db_client: Client,
    config: dict,
    account_id: int,
    net_flow: float,
    prices: dict,
    processed_txns: list[dict]
) -> dict
```

**Parameters:**
- `net_flow`: Net cashflow (positive = deposit, negative = withdrawal)

**Deposit Logic:**
```python
if net_flow > 0:
    btc_investment = net_flow / 2
    eth_investment = net_flow / 2
    new_btc_units = current_btc_units + (btc_investment / btc_price)
    new_eth_units = current_eth_units + (eth_investment / eth_price)
```

**Withdrawal Logic:**
```python
if net_flow < 0:
    withdrawal_amount = abs(net_flow)
    reduction_ratio = withdrawal_amount / current_benchmark_value
    new_btc_units = current_btc_units * (1 - reduction_ratio)
    new_eth_units = current_eth_units * (1 - reduction_ratio)
```

---

### Utility Functions

#### `calculate_next_rebalance_time(now, rebalance_day, rebalance_hour)`
Calculates next scheduled rebalance timestamp.

```python
def calculate_next_rebalance_time(
    now: datetime,
    rebalance_day: int,
    rebalance_hour: int
) -> datetime
```

**Parameters:**
- `rebalance_day`: Day of week (0=Monday, 6=Sunday)
- `rebalance_hour`: Hour of day (0-23)

**Logic:**
```python
days_ahead = (rebalance_day - now.weekday() + 7) % 7
if days_ahead == 0 and now.hour >= rebalance_hour:
    days_ahead = 7  # Next week
```

---

#### `save_history(db_client, account_id, nav, benchmark_value)`
Saves NAV and benchmark snapshot to historical data.

```python
def save_history(
    db_client: Client,
    account_id: int,
    nav: float,
    benchmark_value: float
) -> None
```

**Database Operation:**
```sql
INSERT INTO nav_history (account_id, timestamp, nav, benchmark_value)
VALUES (?, ?, ?, ?)
```

---

### Tracking Functions

#### `get_last_processed_time(db_client, account_id)`
Gets timestamp of last transaction processing for an account.

```python
def get_last_processed_time(db_client: Client, account_id: int) -> str
```

**Returns:**
- ISO timestamp string of last processing
- 30 days ago for first run

---

#### `update_last_processed_time(db_client, account_id)`
Updates the last processed timestamp for an account.

```python
def update_last_processed_time(db_client: Client, account_id: int) -> None
```

**Database Operation:**
```sql
INSERT INTO account_processing_status (account_id, last_processed_timestamp)
VALUES (?, ?) 
ON CONFLICT (account_id) 
DO UPDATE SET last_processed_timestamp = ?
```

## 🗄️ Database Schema Reference

### Required Tables

#### `binance_accounts`
```sql
id SERIAL PRIMARY KEY
account_name VARCHAR(100) NOT NULL
api_key TEXT NOT NULL
api_secret TEXT NOT NULL  
created_at TIMESTAMPTZ DEFAULT NOW()
```

#### `benchmark_configs`
```sql
id SERIAL PRIMARY KEY
account_id INTEGER REFERENCES binance_accounts(id)
btc_units DECIMAL(20,8) DEFAULT 0
eth_units DECIMAL(20,8) DEFAULT 0
rebalance_day INTEGER DEFAULT 0
rebalance_hour INTEGER DEFAULT 12
next_rebalance_timestamp TIMESTAMPTZ
created_at TIMESTAMPTZ DEFAULT NOW()
```

#### `nav_history`
```sql
id SERIAL PRIMARY KEY
account_id INTEGER REFERENCES binance_accounts(id)
timestamp TIMESTAMPTZ NOT NULL
nav DECIMAL(20,2) NOT NULL
benchmark_value DECIMAL(20,2) NOT NULL
created_at TIMESTAMPTZ DEFAULT NOW()
```

#### `processed_transactions`
```sql
id SERIAL PRIMARY KEY
account_id INTEGER REFERENCES binance_accounts(id)
transaction_id VARCHAR(50) UNIQUE NOT NULL
transaction_type VARCHAR(20) NOT NULL
amount DECIMAL(20,8) NOT NULL
timestamp TIMESTAMPTZ NOT NULL
status VARCHAR(20) NOT NULL
created_at TIMESTAMPTZ DEFAULT NOW()
```

#### `account_processing_status`
```sql
account_id INTEGER PRIMARY KEY REFERENCES binance_accounts(id)
last_processed_timestamp TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ DEFAULT NOW()
```

## 🚨 Error Handling

### Error Types and Responses

#### API Errors
```python
try:
    result = binance_client.futures_account()
except BinanceAPIException as e:
    print(f"Binance API Error: {e}")
    return None
```

#### Database Errors
```python
try:
    response = db_client.table('nav_history').insert(data).execute()
except Exception as e:
    print(f"Database Error: {e}")
    raise  # Re-raise for atomic operations
```

#### Network Errors
```python
try:
    prices = get_prices(client)
except requests.exceptions.RequestException as e:
    print(f"Network Error: {e}")
    return None
```

### Error Recovery Strategies

1. **Account Level**: Individual account failures don't affect others
2. **Transaction Level**: Failed transactions retry on next run
3. **API Level**: Graceful degradation with logging
4. **Database Level**: Atomic operations prevent partial updates

## 🔒 Security Considerations

### API Key Security
- Store API keys encrypted in database
- Use read-only permissions only
- Separate keys per environment
- Regular key rotation

### Database Security
- Use Row Level Security (RLS) policies
- Service role key for backend operations
- Parameterized queries only
- Connection encryption (SSL)

### Rate Limiting
- Respect Binance API rate limits
- Implement exponential backoff
- Cache frequently accessed data
- Batch operations when possible

## 📊 Performance Optimization

### Database Optimization
```sql
-- Indexes for performance
CREATE INDEX idx_nav_history_account_timestamp 
ON nav_history(account_id, timestamp DESC);

CREATE INDEX idx_processed_transactions_account 
ON processed_transactions(account_id, timestamp DESC);
```

### API Optimization
- Batch multiple symbol price requests
- Cache static configuration data
- Use connection pooling
- Minimize redundant API calls

### Memory Optimization
- Process accounts sequentially to limit memory usage
- Use generators for large data sets
- Clean up temporary variables
- Limit historical data queries

## 📋 Logging System Reference

### Logger Classes

#### `MonitorLogger`
Advanced logging system with structured JSON output and performance monitoring.

```python
from api.logger import get_logger, LogCategory, OperationTimer

logger = get_logger()
```

**Key Features:**
- **Structured JSON logging** with searchable fields
- **Performance timing** with millisecond precision
- **Account-specific tracking** with context
- **Category-based organization** of log entries
- **File persistence** with rotation and memory management

#### `LogCategory` Enum
Predefined categories for organizing log entries:

- `SYSTEM` - System-level operations
- `ACCOUNT_PROCESSING` - Account processing workflows  
- `API_CALL` - Binance API interactions
- `DATABASE` - Database operations
- `BENCHMARK` - Benchmark calculations
- `TRANSACTION` - Deposit/withdrawal processing
- `PRICE_UPDATE` - Price data fetching
- `REBALANCING` - Portfolio rebalancing
- `DEMO_MODE` - Demo mode operations

#### `OperationTimer`
Context manager for timing operations with automatic logging:

```python
with OperationTimer(logger, LogCategory.API_CALL, "fetch_nav", account_id, account_name):
    nav = get_futures_account_nav(client)
    # Automatically logs duration and success/failure
```

### Demo Mode System

#### `DemoModeController`
Controls switching between live and demo modes:

```python
from api.demo_mode import get_demo_controller

controller = get_demo_controller()
if controller.is_demo_mode():
    # Safe testing with mock data
    binance_client = controller.get_binance_client(api_key, api_secret)
    db_client = controller.get_supabase_client(real_supabase)
```

#### Demo Mode Functions

**`simulate_transaction(type, amount, account_id)`**
```python
result = simulate_transaction("DEPOSIT", 5000.0, 1)
# Returns: transaction details and updated portfolio state
```

**`simulate_market_scenario(scenario)`**
```python
result = simulate_market_scenario("bull_run")
# Returns: price changes and portfolio impact
```

**`get_demo_dashboard_data()`**
```python
data = get_demo_dashboard_data()
# Returns: comprehensive demo data for dashboard
```

### Logging Methods

#### Basic Logging
```python
logger.info(LogCategory.SYSTEM, "operation_name", "Message", 
           account_id=1, account_name="Demo Account", 
           data={"key": "value"})

logger.error(LogCategory.API_CALL, "binance_error", "API call failed",
            account_id=1, error="Connection timeout")
```

#### Performance Metrics
```python
# Get overall performance metrics
metrics = logger.get_performance_metrics()
# Returns: operation counts, success rates, timing stats

# Get recent logs with filtering
logs = logger.get_recent_logs(limit=100, category="api_call", account_id=1)

# Get error logs from last 24 hours
errors = logger.get_error_logs(hours=24)

# Get account-specific summary
summary = logger.get_account_summary(account_id=1)
```

### Environment Variables

#### Logging Configuration
```bash
# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Maximum log entries in memory
MAX_LOG_ENTRIES=10000

# Demo mode toggle
DEMO_MODE=true  # Enables safe testing mode
```

---

**This API reference provides complete technical documentation for integrating and extending the Binance Portfolio Monitor system.**