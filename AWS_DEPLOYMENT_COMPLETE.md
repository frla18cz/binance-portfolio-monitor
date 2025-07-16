# 🚀 AWS EC2 Deployment - Kompletní návod

Jednoduchý a přímočarý návod pro nasazení Binance Portfolio Monitoru na AWS EC2.

## 📋 Co budete potřebovat

- AWS účet s EC2 instancí (Amazon Linux 2 nebo Ubuntu)
- SSH přístup k instanci 
- PyCharm (volitelné, ale doporučené)
- API klíče pro Binance a Supabase

## 🎯 Rychlý přehled

1. **Nahrajete kód** na EC2 (přes PyCharm nebo Git)
2. **Nastavíte prostředí** (Python, dependencies, .env)
3. **Spustíte aplikaci** (Python script běžící přes screen)
4. **Dashboard** poběží na portu 8000

Celý proces zabere ~15 minut.

## 📚 Návody podle situace

### A) Máte PyCharm propojený s EC2

Použijte **[PYCHARM_DEPLOYMENT.md](deployment/aws/PYCHARM_DEPLOYMENT.md)** - obsahuje:
- Nastavení PyCharm deployment
- Upload přes IDE
- SSH terminal přímo v PyCharm
- Synchronizace změn

### B) Chcete použít automatický script

Použijte **[deploy_simple.sh](deployment/aws/deploy_simple.sh)**:
```bash
./deployment/aws/deploy_simple.sh váš-server-ip váš-klíč.pem
```

### C) Preferujete manuální postup

Následujte **[SIMPLE_DEPLOYMENT.md](deployment/aws/SIMPLE_DEPLOYMENT.md)** - krok po kroku instrukce.

## 🚀 Nejjednodušší cesta (5 kroků)

### 1. Nahrajte kód na server

**Možnost A - Git (nejjednodušší):**
```bash
ssh ec2-user@váš-server-ip
git clone https://github.com/yourusername/binance_monitor_playground.git
cd binance_monitor_playground
```

**Možnost B - PyCharm:**
- Tools → Deployment → Upload to...

**Možnost C - Jakkoliv jinak:**
- FTP, SCP, rsync... cokoliv vám vyhovuje

### 2. Připojte se na server

```bash
ssh ec2-user@váš-server-ip
cd binance_monitor_playground
```

### 3. Nastavte Python prostředí

```bash
# Nainstalujte Python (pokud není)
sudo yum install -y python3 python3-pip

# Vytvořte virtuální prostředí
python3 -m venv venv
source venv/bin/activate

# Nainstalujte závislosti
pip install -r requirements.txt
```

### 4. Vytvořte konfiguraci

```bash
# Zkopírujte vzorový soubor
cp deployment/aws/.env.example .env

# Upravte hodnoty
nano .env
```

Vyplňte tyto 4 hodnoty:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
BINANCE_API_KEY=váš_api_klíč
BINANCE_API_SECRET=váš_secret
```

### 5. Spusťte aplikaci

```bash
# Otestujte že vše funguje
python test_binance_aws.py

# Spusťte monitoring
screen -S monitor
python deployment/aws/run_forever.py

# Odpojte se od screen (aplikace běží dál)
# Stiskněte: Ctrl+A, pak D
```

**✅ Hotovo!** Aplikace běží a sbírá data každou hodinu.

## 📊 Přístup k dashboardu

Dashboard běží na: `http://váš-server-ip:8000`

**Pro bezpečný přístup použijte SSH tunel:**
```bash
# Na vašem lokálním počítači
ssh -L 8000:localhost:8000 ec2-user@váš-server-ip

# Pak otevřete
http://localhost:8000
```

## 🔧 Správa aplikace

### Zobrazit běžící aplikaci
```bash
screen -ls              # Seznam sessions
screen -r monitor       # Připojit se
```

### Zobrazit logy
```bash
tail -f logs/continuous_runner.log
tail -f logs/monitor.log
```

### Restartovat aplikaci
```bash
screen -X -S monitor quit               # Zastavit
screen -S monitor                       # Nová session  
python deployment/aws/run_forever.py    # Spustit znovu
```

## ❓ Řešení problémů

### "Module not found"
```bash
# Aktivujte virtuální prostředí
source venv/bin/activate
```

### "Service unavailable from restricted location"
- Aplikace automaticky používá data-api.binance.vision
- Zkontrolujte region vaší EC2 instance (EU regiony fungují lépe)

### Dashboard se nenačítá
- Zkontrolujte Security Group - port 8000 musí být otevřený
- Nebo použijte SSH tunel (doporučeno)

### Screen session neexistuje po restartu
- Po restartu serveru musíte aplikaci spustit znovu
- Zvažte upgrade na systemd pro automatický start

## 📁 Struktura souborů

```
binance_monitor_playground/
├── deployment/aws/
│   ├── run_forever.py        # Hlavní script (nekonečná smyčka)
│   ├── start_monitor.sh      # Pomocný script pro screen
│   ├── .env.example          # Vzorová konfigurace
│   └── *.md                  # Dokumentace
├── api/
│   ├── index.py             # Monitoring logic
│   └── dashboard.py         # Web dashboard
└── .env                     # Vaše konfigurace (vytvořte)
```

## 🔐 Bezpečnostní doporučení

1. **Používejte Binance API klíče pouze pro čtení**
2. **Nikdy nenahrávejte .env do Gitu**
3. **Omezte přístup k portu 8000 pouze na vaši IP**
4. **Pravidelně aktualizujte systém**

## 🚀 Další kroky

1. **Monitoring**: Nastavte CloudWatch nebo jiný monitoring
2. **Zálohování**: Pravidelné zálohy databáze
3. **Systemd**: Pro robustnější řešení přejděte na systemd service
4. **HTTPS**: Nastavte reverse proxy s SSL certifikátem

## 📝 Poznámky

- Aplikace sbírá data **každou hodinu**
- Dashboard se **automaticky obnovuje** každých 60 sekund
- Logy se ukládají do složky `logs/`
- Python 3.7+ je dostačující

---

**Potřebujete pomoc?** Zkontrolujte:
- [SIMPLE_DEPLOYMENT.md](deployment/aws/SIMPLE_DEPLOYMENT.md) - detailní kroky
- [PYCHARM_DEPLOYMENT.md](deployment/aws/PYCHARM_DEPLOYMENT.md) - pro PyCharm uživatele
- [CLAUDE.md](CLAUDE.md) - poznámky a řešení problémů