# Binance Portfolio Monitor - Návod k použití

## 🚀 Rychlý start

```bash
# 1. Nastavte API klíče v .env souboru
# SUPABASE_URL=your_supabase_url
# SUPABASE_ANON_KEY=your_supabase_key

# 2. Přidejte Binance API klíče do databáze
# INSERT INTO binance_accounts (account_name, api_key, api_secret)
# VALUES ('Your Account', 'your_api_key', 'your_api_secret');

# 3. Spusťte monitoring
python run_live.py

# 4. Spusťte dashboard
python api/dashboard.py
```

## 📊 Spuštění

### 🔴 Live Mode (reálný monitoring)

**Kompletní monitoring s dashboardem:**
```bash
python run_live.py                    # Jednorázové spuštění
python api/dashboard.py              # Dashboard na http://localhost:8000/dashboard
```

**Jen scraping dat (bez dashboardu):**
```bash
python scrape_data.py                # Nový wrapper script
python -m api.index                  # Přímo main modul
```

**Kontrola databáze:**
```bash
python check_data.py                 # Zkontroluje stav DB a poslední data
```

## 🔧 Nastavení

### Environment Variables

V `.env` souboru:
```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
```

### API Klíče

V databázi `binance_accounts`:
```sql
INSERT INTO binance_accounts (account_name, api_key, api_secret)
VALUES ('Your Account', 'your_api_key', 'your_api_secret');
```

## 📊 Dashboard

Dashboard zobrazuje:
- 📈 Aktuální NAV a benchmark performance
- 💰 Real-time BTC a ETH ceny
- 📋 Logy a system metrics
- 📊 Portfolio performance historie

```bash
python api/dashboard.py
```

URL: http://localhost:8000/dashboard

### API Endpoints:
- `/api/dashboard/status` - System status
- `/api/dashboard/logs` - Recent logs
- `/api/dashboard/metrics` - Portfolio metrics
- `/api/dashboard/run-monitoring` - Trigger monitoring

## 📊 Jen scraping dat (bez dashboardu)

Pro pravidelné krmení databáze daty:

```bash
# Jednorázové spuštění
python scrape_data.py

# Nebo přímo main modul
python -m api.index

# Zkontrolovat stav databáze
python check_data.py
```

**Výhody jen scrapingu:**
- ✅ Rychlejší - bez dashboard overhead
- ✅ Minimální resource usage
- ✅ Ideální pro cron jobs
- ✅ Stejná data jako s dashboardem

## 🔍 Kontrola dat

```bash
python check_data.py
```

Zobrazí:
- 💼 Počet účtů v databázi
- 📈 Poslední NAV záznamy
- ⚙️ Benchmark konfigurace
- 💰 Recent transactions

## 🛡️ Bezpečnostní poznámky

1. **API klíče ukládejte bezpečně** - nikdy je necommitujte do gitu
2. **Používejte read-only API klíče** pokud možno
3. **Pravidelně kontrolujte logy** na podezřelé aktivity
4. **Backup databáze** pravidelně

## ⚙️ Automatické spouštění

### 🔧 Lokálně (u vás na počítači):

**Jednoduché nastavení cron jobu:**
```bash
python setup_cron.py
# Vyberte možnost 1 pro automatické spouštění každé 2 minuty
```

**Nebo daemon pro development:**
```bash
python monitor_daemon.py --minutes 2
# Běží kontinuálně, ukončení Ctrl+C
```

**Manuální crontab:**
```bash
# Přidejte do crontab -e:
*/2 * * * * /path/to/venv/bin/python /path/to/project/scrape_data.py >> /path/to/project/logs/cron.log 2>&1
```

### ☁️ Na Vercelu:

**Automatické nasazení:**
```bash
# vercel.json už je připraven - data se budou stahovat každé 2 minuty
vercel deploy
```

## 🚨 Troubleshooting

### Chyby API klíčů:
```bash
# Zkontrolujte .env soubor
cat .env

# Zkontrolujte databázi
python check_data.py
```

### Dashboard nefunguje:
```bash
# Zkontrolujte port 8000
lsof -i :8000

# Zkontrolujte logy
tail -f logs/monitor.log
```

### Databáze problémy:
```bash
# Test připojení
python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
print('✅ Supabase connected')
"
```

## 📁 Struktura souborů

```
binance_monitor_playground/
├── api/
│   ├── dashboard.py          # Dashboard API
│   ├── index.py             # Hlavní monitoring logika
│   └── logger.py            # Logging systém
├── run_live.py              # Live mode runner
├── scrape_data.py           # Data scraping script
├── check_data.py            # Database check script
├── dashboard.html           # Dashboard frontend
├── .env                     # Environment variables
└── USAGE.md                 # Tento soubor
```