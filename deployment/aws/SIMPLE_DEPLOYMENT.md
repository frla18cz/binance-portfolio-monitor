# 🚀 Jednoduchý deployment Binance Monitoru na AWS EC2

Tento návod vás provede nasazením Binance Portfolio Monitoru na AWS EC2 instanci pomocí jednoduché Python smyčky a screen utility.

## 🏗️ Jak to funguje?

| Komponenta | Co dělá | Popis |
|------------|---------|-------|
| **`run_forever.py`** | ⏰ Časovač | Spouští monitoring každou hodinu |
| **`api/index.py`** | 👷 Pracant | Sbírá data z Binance, počítá hodnoty |
| **`api/dashboard.py`** | 📊 Display | Web rozhraní na portu 8000 |

## 📋 Požadavky

- AWS EC2 instance s Linuxem (Amazon Linux 2 nebo Ubuntu)
- Python 3.9+ nainstalovaný na serveru
- SSH přístup k instanci
- Binance API klíče

## 🛠️ Kroky nasazení

### 1. Připojení k EC2 instanci

```bash
# Připojte se k vaší EC2 instanci
ssh -i your-key.pem ec2-user@your-instance-ip

# Pro Ubuntu použijte:
# ssh -i your-key.pem ubuntu@your-instance-ip
```

### 2. Příprava prostředí

```bash
# Vytvořte adresář pro aplikaci
mkdir -p /home/ec2-user/binance-monitor
cd /home/ec2-user/binance-monitor

# Nainstalujte potřebné systémové balíčky
sudo yum update -y
sudo yum install -y python3.9 python3.9-pip git screen

# Pro Ubuntu:
# sudo apt update
# sudo apt install -y python3.9 python3.9-pip git screen
```

### 3. Nahrání kódu na server

**Možnost A: Použití deploy skriptu (doporučeno)**

Na vašem lokálním počítači:

```bash
# Přejděte do složky projektu
cd /path/to/binance_monitor_playground

# Spusťte deployment skript
chmod +x deployment/aws/deploy_simple.sh
./deployment/aws/deploy_simple.sh your-instance-ip your-key.pem
```

**Možnost B: Manuální nahrání**

```bash
# Na lokálním počítači
rsync -avz -e "ssh -i your-key.pem" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.env' \
    --exclude='logs' \
    . ec2-user@your-instance-ip:/home/ec2-user/binance-monitor/
```

### 4. Instalace Python závislostí

Na EC2 instanci:

```bash
cd /home/ec2-user/binance-monitor

# Vytvořte virtuální prostředí (doporučeno)
python3.9 -m venv venv
source venv/bin/activate

# Nainstalujte závislosti
pip install -r requirements.txt
```

### 5. Konfigurace aplikace

```bash
# Vytvořte .env soubor z příkladu
cp deployment/aws/.env.example .env

# Upravte .env soubor s vašimi údaji
nano .env
```

Vyplňte následující hodnoty:
- `SUPABASE_URL` - URL vaší Supabase instance
- `SUPABASE_ANON_KEY` - Anonymní klíč z Supabase
- `BINANCE_API_KEY` - Váš Binance API klíč (pouze pro čtení)
- `BINANCE_API_SECRET` - Váš Binance API secret

### 6. Test funkčnosti

```bash
# Aktivujte virtuální prostředí (pokud ještě není)
source venv/bin/activate

# Otestujte přístup k Binance API
python test_binance_aws.py

# Spusťte monitoring jednou pro test
python -m api.index

# Zkontrolujte dashboard (v novém terminálu)
python -m api.dashboard
```

### 7. Spuštění aplikace na pozadí

```bash
# Spusťte monitoring pomocí screen
chmod +x deployment/aws/start_monitor.sh
./deployment/aws/start_monitor.sh

# Aplikace nyní běží na pozadí!
```

## 📊 Správa aplikace

### Zobrazení běžící aplikace

```bash
# Seznam všech screen sessions
screen -ls

# Připojení k monitor session
screen -r monitor
```

### Odpojení od screen (aplikace dál běží)
Stiskněte `Ctrl+A` a pak `D`

### Zastavení aplikace

```bash
# Připojte se k session
screen -r monitor

# Zastavte aplikaci
Ctrl+C

# Ukončete screen session
exit
```

### Kontrola logů

```bash
# Zobrazit poslední logy
tail -f logs/monitor.log

# Zobrazit chyby
grep ERROR logs/monitor.log
```

### Restart aplikace

```bash
# Zastavte běžící aplikaci
screen -X -S monitor quit

# Spusťte znovu
./deployment/aws/start_monitor.sh
```

## 🌐 Přístup k dashboardu

Dashboard běží na portu 8000. Pro přístup:

1. **Možnost A: SSH tunel (bezpečnější)**
   ```bash
   # Na lokálním počítači
   ssh -i your-key.pem -L 8000:localhost:8000 ec2-user@your-instance-ip
   
   # Pak otevřete v prohlížeči: http://localhost:8000
   ```

2. **Možnost B: Přímý přístup (vyžaduje otevřený port)**
   ```bash
   # Otevřete port 8000 v AWS Security Group
   # Pak přistupte na: http://your-instance-ip:8000
   ```

## 🔧 Řešení problémů

### Aplikace se nespustí
```bash
# Zkontrolujte Python verzi
python3.9 --version

# Zkontrolujte chybějící závislosti
pip list

# Zkontrolujte .env soubor
cat .env
```

### Chyba "Service unavailable from restricted location"
- Používá se data-api.binance.vision pro veřejné endpointy
- Zkontrolujte region vaší EC2 instance (EU regiony fungují lépe)
- Zkuste `test_binance_aws.py` pro diagnostiku

### Screen session neexistuje
```bash
# Vytvořte novou session
screen -S monitor

# Spusťte aplikaci
./deployment/aws/start_monitor.sh
```

## 📈 Monitoring výkonu

```bash
# Využití CPU a paměti
top

# Místo na disku
df -h

# Velikost logů
du -sh logs/
```

## 🔐 Bezpečnostní doporučení

1. **Nikdy nenahrávejte .env soubor do Gitu**
2. **Použijte Binance API klíče pouze pro čtení**
3. **Pravidelně aktualizujte systém:**
   ```bash
   sudo yum update -y
   ```
4. **Nastavte automatické zálohování databáze v Supabase**

## 📝 Poznámky

- Aplikace sbírá data každou hodinu
- Dashboard se automaticky obnovuje každých 60 sekund
- Logy se ukládají do složky `logs/`
- Při restartu serveru je potřeba znovu spustit aplikaci

## 🚀 Upgrade na systemd (volitelné)

Až budete připraveni na robustnější řešení, můžete přejít na systemd service. Návod najdete v `SYSTEMD_DEPLOYMENT.md`.