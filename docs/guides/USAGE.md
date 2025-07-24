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
python -m api.dashboard              # Enhanced Dashboard na http://localhost:8000/dashboard
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
python -m api.dashboard
```

URL: http://localhost:8001/dashboard

### API Endpoints:
- `/api/dashboard/status` - System status
- `/api/dashboard/logs` - Recent logs
- `/api/dashboard/metrics` - Portfolio metrics
- `/api/dashboard/chart-data` - NAV chart data with period filtering
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

## 📊 Clean Benchmark System

Systém používá "clean start" přístup pro přesné benchmark kalkulace:

**Klíčové vlastnosti:**
- ✅ Ukládá historické BTC/ETH ceny s každým NAV záznamem
- ✅ Dynamický 50/50 BTC/ETH benchmark s weekly rebalancing (pondělí)
- ✅ Používá skutečné historické ceny místo současných cen
- ✅ Přesné porovnání výkonnosti od inception bodu

**Test a debug nástroje:**
```bash
python test_clean_benchmark.py    # Test databázové struktury
python debug_nav.py               # Debug NAV kalkulace s detaily
```

**SQL migrace (pokud potřeba):**
```sql
-- Přidat price columns do nav_history tabulky
ALTER TABLE nav_history 
ADD COLUMN btc_price NUMERIC(10,2),
ADD COLUMN eth_price NUMERIC(10,2);
```

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

## 📊 NAV Kalkulace - Vysoká přesnost

### ✅ Nový přesný výpočet NAV
Systém nyní používá **pokročilou NAV kalkulaci**, která dosahuje **99.76% přesnosti** vůči Binance dashboardu:

**Metoda výpočtu:**
1. **Spot účet**: Všechny assety převedené na USD za live ceny
2. **Futures účet**: `marginBalance` za každý asset (wallet + unrealized P&L) převedený na USD
3. **Celkový NAV**: Součet spot + futures hodnot

**Formule:**
```
NAV = Spot_Assets_USD + Futures_marginBalance_USD
```

**Proč je to přesné:**
- 🎯 **Live price konverze**: Používá real-time BTC/USDT a ostatní asset ceny
- 💰 **Margin balance**: Zahrnuje unrealized P&L do kalkulace assetů  
- 📊 **Dashboard parity**: Přesně odpovídá tomu, co ukazuje Binance dashboard
- 🔧 **Multi-asset podpora**: Správně zpracovává BTC, BNFCR, USDT a ostatní assety

**Porovnání metod:**
- **Stará metoda**: `totalWalletBalance + totalUnrealizedProfit` (~$400k, 5% chyba)
- **Nová metoda**: Asset-by-asset konverze s margin balances (~$422k, 0.24% chyba)

**Debug nástroje:**
```bash
python debug_nav.py    # Detailní breakdown všech komponent NAV
```

Výsledek ukazuje:
- Spot BTC konverzi
- Futures asset breakdown (BTC, BNFCR, atd.)
- Porovnání s dashboard hodnotou
- Přesnost výpočtu

### Chart data s price columns
Pokud chart nezobrazuje data správně:
```bash
python test_clean_benchmark.py    # Ověří price columns
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
# Zkontrolujte port 8001 
lsof -i :8001

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
├── test_clean_benchmark.py  # Clean benchmark test script
├── debug_nav.py             # NAV calculation debug script
├── add_price_columns.sql    # SQL migration for price columns
├── dashboard.html           # Dashboard frontend
├── .env                     # Environment variables
└── docs/
    └── guides/
        └── USAGE.md                 # Tento soubor
```