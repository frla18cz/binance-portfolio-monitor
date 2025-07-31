# Configuration Admin - Quick Start

## Setup (One Time)

1. **Apply database migrations:**
   ```bash
   psql $DATABASE_URL < migrations/add_runtime_configuration_tables.sql
   psql $DATABASE_URL < migrations/populate_runtime_config.sql
   ```

2. **Verify setup:**
   ```bash
   python test_web_admin.py
   ```

## Usage

### Option 1: Web Admin (Visual Interface)
```bash
python -m api.config_admin_web
```
Then open: http://localhost:8002

**Features:**
- Click any value to edit
- See change history
- Refresh cache instantly
- Auto-validation

### Option 2: CLI
```bash
# List all configs
python scripts/manage_config.py --list

# Change a value
python scripts/manage_config.py --set scheduling.cron_interval_minutes 30

# View history
python scripts/manage_config.py --history
```

### Option 3: Direct Database
```sql
-- Change value directly
UPDATE runtime_config 
SET value = '30'::jsonb 
WHERE key = 'scheduling.cron_interval_minutes';
```

## Important Notes

1. **Cache**: Changes take up to 5 minutes to apply (or use "Refresh Cache" button)
2. **No Auth**: Web admin has no authentication - for local use only
3. **Audit Trail**: All changes are logged with timestamp and user

## Common Configurations

| Key | Description | Default |
|-----|-------------|---------|
| `scheduling.cron_interval_minutes` | How often to run monitoring | 60 |
| `fee_management.calculation_schedule` | Fee calculation frequency | monthly |
| `financial.minimum_balance_threshold` | Min balance to include | 0.001 |
| `logging.database_logging.retention_days` | Log retention period | 30 |

## Troubleshooting

**Tables don't exist?**
Run the migrations (step 1 above)

**Port 8002 in use?**
```bash
CONFIG_ADMIN_PORT=8003 python -m api.config_admin_web
```

**Changes not showing?**
Click "Refresh Cache" or wait 5 minutes