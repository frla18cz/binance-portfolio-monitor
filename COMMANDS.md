# 🚀 Binance Monitor - Quick Commands Reference

*Rychlý přehled všech důležitých příkazů pro operativní práci s projektem*

## 📋 Obsah
- [Quick Start](#-quick-start)
- [Core Příkazy](#-core-příkazy)
- [Dashboard & Monitoring](#-dashboard--monitoring)
- [Fee Management](#-fee-management)
- [Testing & Debugging](#-testing--debugging)
- [Utility Scripts](#-utility-scripts)
- [AWS Deployment](#-aws-deployment)
- [Database Operations](#️-database-operations)

---

## 🚀 Quick Start

### Nejdůležitější příkazy pro rychlý začátek:

```bash
# Spustit monitoring jednou (manuálně)
python -m api.index

# Spustit web dashboard
python -m api.dashboard
# Otevřít: http://localhost:8000

# Spustit kontinuální monitoring (každou hodinu)
python deployment/aws/run_forever.py

# Rychlý test v demo režimu
export DEMO_MODE=true
python demo_test.py
```

---

## 🔧 Core Příkazy

### Hlavní monitoring
```bash
# Spustit monitoring všech účtů (api/index.py)
python -m api.index

# Debug NAV kalkulace
python debug_nav.py

# Kontinuální běh s automatickým restartem
python deployment/aws/run_forever.py
```

### Konfigurace
```bash
# Zobrazit aktuální konfiguraci
cat config/settings.json | jq '.'

# Upravit runtime konfiguraci
python scripts/manage_config.py
```

---

## 📊 Dashboard & Monitoring

### Web Dashboard
```bash
# Spustit dashboard server (port 8000)
python -m api.dashboard

# Dashboard URL
http://localhost:8000
http://localhost:8000/dashboard
```

### API Endpoints
```bash
# Aktuální metriky
curl http://localhost:8000/api/dashboard/metrics

# Alpha výpočty
curl http://localhost:8000/api/dashboard/alpha-metrics

# Fee tracking
curl http://localhost:8000/api/dashboard/fees

# Spustit výpočet poplatků
curl http://localhost:8000/api/calculate_fees
```

---

## 💰 Fee Management

### Výpočet poplatků
```bash
# Zobrazit konfiguraci poplatků
python scripts/run_fee_calculation.py --show-config

# Seznam účtů s fee rates
python scripts/run_fee_calculation.py --list-accounts

# Vypočítat poplatky pro konkrétní měsíc
python scripts/run_fee_calculation.py --month 2025-07

# Vypočítat poplatky za posledních N měsíců
python scripts/run_fee_calculation.py --last-n-months 3

# Dry run (bez zápisu do DB)
python scripts/run_fee_calculation.py --month 2025-07 --dry-run
```

---

## 🧪 Testing & Debugging

### Demo Mode
```bash
# Spustit v demo módu (bezpečné testování)
export DEMO_MODE=true
python demo_test.py

# Test různých tržních scénářů
python demo_test.py  # Interaktivní menu
```

### Debugging Tools
```bash
# Debug NAV kalkulace
python debug_nav.py

# Zkontrolovat historické transakce
python scripts/check_historical_transfers.py

# Debug transakce
python scripts/debug_transactions.py

# Test deposit processing
python scripts/test_deposit_processing.py
```

### Coin Pricing & Deposits
```bash
# Test coin pricing pro různé kryptoměny
python scripts/test_coin_pricing.py

# Simulace deposit flow (bez DB změn)
python scripts/simulate_deposit_flow.py

# Opravit metadata pro existující BTC depozity
python scripts/fix_deposit_metadata.py

# Aktualizovat depozity s chybějícími cenami
python scripts/update_missing_prices.py
```

---

## 🔍 Utility Scripts

### Benchmark Validation
```bash
# Validovat konzistenci benchmark výpočtů
python scripts/validate_benchmark_consistency.py

# Validovat konkrétní účet
python scripts/validate_benchmark_consistency.py --account "Simple"

# Aplikovat benchmark migrace
python scripts/apply_benchmark_migrations.py
```

### Runtime Configuration
```bash
# Spravovat runtime konfiguraci
python scripts/manage_config.py

# Aplikovat runtime config migraci
python scripts/apply_runtime_config_migration.py
```

---

## 🚀 AWS Deployment

### Deploy na EC2
```bash
# Deploy kódu na server
./deployment/aws/deploy_simple.sh <server-ip> <key.pem>

# Příklad:
./deployment/aws/deploy_simple.sh 54.123.45.67 ~/keys/my-key.pem
```

### Na serveru (po SSH)
```bash
# Přejít do adresáře
cd /home/ec2-user/binance-monitor

# Aktivovat virtuální prostředí
source venv/bin/activate

# Spustit monitoring
./deployment/aws/start_monitor.sh

# Připojit se k běžícímu monitoru
screen -r monitor

# Odpojit se (monitor běží dál)
# Stisknout: Ctrl+A, pak D

# Zobrazit logy
tail -f logs/continuous_runner.log
```

### Screen příkazy
```bash
# Seznam běžících sessions
screen -ls

# Připojit se k session
screen -r monitor

# Vytvořit novou session
screen -S monitor

# Ukončit session
# V session: Ctrl+C nebo exit
```

---

## 🗄️ Database Operations

### Snapshots (PostgreSQL backup/restore)

Prerequisites (macOS):
- Install CLI tools: `brew install libpq`
- Ensure PATH in zsh: `echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc && exec zsh`

Securely set DB URL in this shell (no secrets in chat):
```bash
read -s "PGPASS?DB password: "; export SUPABASE_DB_URL="postgres://postgres:${PGPASS}@db.<your-project>.supabase.co:5432/postgres?sslmode=require"; unset PGPASS; echo
```

Create a snapshot now:
```bash
python3 scripts/backup_db.py
```

Restore snapshot to a local DB (isolated "branch"):
```bash
createdb my_branch_db            # if not exists
python3 scripts/restore_db.py backups/latest.dump my_branch_db
psql postgres:///my_branch_db    # inspect
```

Troubleshooting:
- `pg_dump not found` -> install libpq and update PATH above
- auth failed -> verify SUPABASE_DB_URL (no braces, correct password, URL-encode special chars)
- module import error -> run from repo root: `python3 scripts/backup_db.py`

### Supabase MCP
```bash
# Project ID: axvqumsxlncbqzecjlxy

# Použití přes MCP (v Claude):
# mcp__supabase__list_tables
# mcp__supabase__execute_sql
# mcp__supabase__get_logs
```

### SQL Queries
```sql
-- Zkontrolovat poslední NAV data
SELECT * FROM nav_history 
ORDER BY timestamp DESC 
LIMIT 10;

-- TWR výpočet za posledních 30 dní
SELECT * FROM calculate_twr_period(
  (SELECT id FROM binance_accounts WHERE account_name = 'YourAccount'),
  NOW() - INTERVAL '30 days',
  NOW()
);

-- Měsíční fee kalkulace
SELECT * FROM calculate_monthly_fees(
  (SELECT id FROM binance_accounts WHERE account_name = 'YourAccount'),
  '2025-07-01'::DATE
);
```

---

## 📝 Poznámky

### Environment Variables
```bash
# Vytvořit .env soubor
cp .env.example .env

# Důležité proměnné:
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
DEMO_MODE=true  # Pro bezpečné testování
```

### Log Files
```bash
# Hlavní logy
logs/continuous_runner.log  # Runner log
logs/monitor.log           # Monitoring log
logs/dashboard.log         # Dashboard log
logs/monitor_logs.jsonl    # Structured logs

# Vyčistit staré logy
rm logs/*.log
```

### Process Management
```bash
# Zkontrolovat lock file
ls -la /tmp/.binance_monitor.lock

# Smazat lock (pokud je zaseknutý)
rm /tmp/.binance_monitor.lock
```

---

## 🔗 Rychlé odkazy

- **CLAUDE.md**: `/CLAUDE.md` - AI kontext a hlavní dokumentace
- **Settings**: `config/settings.json` - Konfigurace
- **Dashboard**: `api/dashboard.py` - Web UI kód
- **Monitor**: `api/index.py` - Core monitoring logika
- **Runner**: `deployment/aws/run_forever.py` - Kontinuální běh

---

*Pro detailní dokumentaci viz `docs/` adresář*