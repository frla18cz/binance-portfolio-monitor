# Runtime Configuration System Guide

## Overview

The Binance Portfolio Monitor now supports a hybrid configuration system that combines:
- **Static configuration** from `config/settings.json` (requires restart)
- **Dynamic runtime configuration** from database (changeable without restart)

This allows you to modify business logic, schedules, and thresholds in real-time while keeping system constants in the JSON file.

## Quick Start

### 1. Apply Database Migrations
```bash
# Create configuration tables
psql $DATABASE_URL < migrations/add_runtime_configuration_tables.sql

# Populate with initial values
psql $DATABASE_URL < migrations/populate_runtime_config.sql
```

### 2. Start Web Admin
```bash
python -m api.config_admin_web
# Open http://localhost:8002
```

### 3. Or Use CLI
```bash
python scripts/manage_config.py --list
python scripts/manage_config.py --set scheduling.cron_interval_minutes 30
```

## Architecture

### Components

1. **Static Configuration** (`config/settings.json`)
   - System constants (database URLs, file paths)
   - Default values for all settings
   - Fallback when database is unavailable

2. **Runtime Configuration** (database tables)
   - `runtime_config` - Global dynamic settings
   - `runtime_config_history` - Audit trail of changes
   - `account_config_overrides` - Account-specific settings

3. **Configuration Service** (`config/runtime_config.py`)
   - In-memory cache with 5-minute TTL
   - Automatic fallback to static config
   - Thread-safe operations

4. **Management Tools**
   - **Web Admin** (`api/config_admin_web.py`) - Visual interface on port 8002
   - **CLI Script** (`scripts/manage_config.py`) - Command line management
   - Full history and audit trail in both

## Usage

### Reading Configuration

#### In Python Code

```python
from config import settings

# Traditional static access (backward compatible)
interval = settings.scheduling.cron_interval_minutes

# Dynamic configuration access
interval = settings.get_dynamic('scheduling.cron_interval_minutes')

# With account-specific override
fee_rate = settings.get_dynamic(
    'fee_management.default_performance_fee_rate',
    account_id='account-uuid',
    default=0.5
)

# Force fresh read (bypass cache)
current_value = settings.get_dynamic('key', use_cache=False)
```

#### Best Practice Pattern

```python
class MyService:
    def __init__(self):
        from config import settings
        self.settings = settings
        # Keep static config for fallback
        self.static_config = settings.financial
    
    def get_threshold(self):
        # Try dynamic first, fall back to static
        return self.settings.get_dynamic(
            'financial.minimum_balance_threshold',
            default=self.static_config.minimum_balance_threshold
        )
```

### Setting Configuration

#### Via Web Admin (Recommended)

1. **Start Web Admin:**
   ```bash
   python -m api.config_admin_web
   ```

2. **Open Browser:**
   Navigate to http://localhost:8002

3. **Features:**
   - **Visual Interface**: See all configs in organized categories
   - **Click to Edit**: Click any value to modify it
   - **Validation**: Built-in validation for common config types
   - **History Tab**: View all changes with timestamps
   - **Cache Control**: "Refresh Cache" button for immediate updates
   - **Auto-refresh**: Page updates every 30 seconds

#### Via CLI Script

```bash
# List all configurations
python scripts/manage_config.py --list

# List by category
python scripts/manage_config.py --list --category scheduling

# Get specific value
python scripts/manage_config.py --get scheduling.cron_interval_minutes

# Update configuration
python scripts/manage_config.py --set scheduling.cron_interval_minutes 30 \
  --description "Reduce monitoring frequency"

# Set account-specific override
python scripts/manage_config.py --set fee_management.default_performance_fee_rate 0.25 \
  --account-id "account-uuid" \
  --description "Special rate for premium account"

# View configuration history
python scripts/manage_config.py --history

# View history for specific key
python scripts/manage_config.py --history --limit 20
```

#### Programmatically

```python
from config import settings

# Set global configuration
success = settings.set_dynamic(
    'scheduling.cron_interval_minutes',
    value=30,
    description='Reduce monitoring frequency',
    updated_by='admin@example.com'
)

# Set account-specific override
success = settings.set_dynamic(
    'fee_management.default_performance_fee_rate',
    value=0.25,
    account_id='account-uuid',
    description='Special rate for premium account'
)
```

## Configuration Categories

### Dynamic (Database) Configurations

These settings can be changed without restart:

#### Scheduling
- `scheduling.cron_interval_minutes` - Monitoring frequency
- `scheduling.daemon_interval_seconds` - Daemon loop interval
- `scheduling.log_retention_hours` - Log retention period
- `scheduling.historical_period_days` - Default history window

#### Financial
- `financial.minimum_balance_threshold` - Min balance for calculations
- `financial.minimum_usd_value_threshold` - Min USD value
- `financial.benchmark_allocation` - BTC/ETH allocation
- `financial.rebalance_frequency` - Rebalancing schedule
- `financial.performance_alert_thresholds` - Alert levels

#### Fee Management
- `fee_management.default_performance_fee_rate` - Default fee rate
- `fee_management.calculation_schedule` - monthly/daily/hourly
- `fee_management.calculation_day` - Day of month (1-28)
- `fee_management.calculation_hour` - Hour of day (0-23)
- `fee_management.test_mode` - Test mode settings

#### Data Processing
- `data_processing.batch_size` - Bulk operation size
- `data_processing.transaction_lookback_days` - Transaction window
- `data_processing.price_cache_seconds` - Price cache TTL

### Static (JSON) Configurations

These require restart to change:

- Database connection settings
- API endpoints and URLs
- File system paths
- Security settings
- CORS origins

## Migration Guide

### 1. Apply Database Migrations

```bash
# Create tables
psql $DATABASE_URL < migrations/add_runtime_configuration_tables.sql

# Populate initial values
psql $DATABASE_URL < migrations/populate_runtime_config.sql
```

### 2. Update Code

Replace static config access with dynamic where appropriate:

```python
# Before
if settings.scheduling.cron_interval_minutes:
    interval = settings.scheduling.cron_interval_minutes

# After
interval = settings.get_dynamic(
    'scheduling.cron_interval_minutes',
    default=60
)
```

### 3. Start Using

That's it! No additional services to run. Just use the management script when needed:

```bash
# View current dynamic configurations
python scripts/manage_config.py --list

# Change a setting
python scripts/manage_config.py --set scheduling.cron_interval_minutes 30
```

## Security Considerations

1. **Direct Database Access**: Management script requires database credentials
2. **Audit Trail**: All changes are logged in `runtime_config_history`
3. **Row Level Security**: Database tables have RLS policies
4. **Change Tracking**: Every modification is recorded with timestamp and user

## Cache Management

The configuration service uses a 5-minute cache by default:

```python
# Clear entire cache
settings.runtime_config.cache.invalidate()

# Clear specific key
settings.runtime_config.cache.invalidate('scheduling.cron_interval_minutes')

# Clear by pattern
settings.runtime_config.cache.invalidate_pattern('scheduling.')
```

## Monitoring

### View Configuration History

```sql
-- Recent changes
SELECT * FROM runtime_config_history 
ORDER BY changed_at DESC 
LIMIT 20;

-- Changes to specific key
SELECT * FROM runtime_config_history 
WHERE key = 'fee_management.calculation_schedule'
ORDER BY changed_at DESC;
```

### Check Active Configurations

```sql
-- All active runtime configs
SELECT key, value, updated_at, updated_by 
FROM runtime_config 
WHERE is_active = true
ORDER BY category, key;

-- Account overrides
SELECT a.account_name, aco.config_key, aco.value
FROM account_config_overrides aco
JOIN binance_accounts a ON a.id = aco.account_id
WHERE aco.is_active = true;
```

## Troubleshooting

### Configuration Not Updating

1. Check cache TTL hasn't expired
2. Verify database connectivity
3. Check for account-specific overrides
4. Review configuration history for recent changes

### Fallback Behavior

If database is unavailable:
1. System falls back to `settings.json`
2. Warning logged but operation continues
3. Changes cannot be saved until database recovers

### Performance

- Cache reduces database queries
- Batch configuration reads when possible
- Use `get_all()` for multiple configs
- Disable cache for real-time requirements

## Example: Changing Fee Calculation Schedule

```bash
# Check current schedule
python scripts/manage_config.py --get fee_management.calculation_schedule

# Change from monthly to daily calculations
python scripts/manage_config.py --set fee_management.calculation_schedule daily \
  --description "Switch to daily fee calculations for testing"

# Verify the change worked
python scripts/manage_config.py --get fee_management.calculation_schedule

# View change history
python scripts/manage_config.py --history --limit 10
```

## Web Admin Screenshots

The web admin provides a clean, easy-to-use interface:

### Configuration List
- Organized by categories (Scheduling, Financial, Fee Management, etc.)
- Click any value to edit
- Shows last update time
- Cache info with refresh button at the top

### Edit Page
- Type-aware input fields (boolean = radio buttons, JSON = textarea)
- Real-time validation
- Description field for change tracking
- Shows current value and source (database/static)

### History Page
- Complete audit trail of all changes
- Shows old value → new value
- Timestamp and user tracking
- Expandable JSON values

## Troubleshooting

### Web Admin Not Starting
```bash
# Check if port 8002 is already in use
lsof -i :8002

# Use different port
CONFIG_ADMIN_PORT=8003 python -m api.config_admin_web
```

### Changes Not Taking Effect
1. **Check cache TTL** - changes take up to 5 minutes
2. **Use "Refresh Cache"** button in web admin
3. **Verify in database**:
   ```sql
   SELECT key, value FROM runtime_config WHERE key = 'your.config.key';
   ```

### Direct Database Changes
Yes, you can change values directly in the database! The application will pick them up within 5 minutes (cache TTL).

```sql
-- Example: Change update interval
UPDATE runtime_config 
SET value = '30'::jsonb 
WHERE key = 'scheduling.cron_interval_minutes';
```

## Future Enhancements

1. **Configuration Groups**: Bundle related configs
2. **Import/Export**: Backup and restore configurations
3. **Validation Rules**: Stricter validation per config key
4. **Environment Sync**: Copy configs between dev/prod
5. **WebSocket Updates**: Real-time config changes without cache delay