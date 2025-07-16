# 🚀 PyCharm + EC2 Deployment Guide

Jednoduchý návod pro nasazení přes PyCharm na AWS EC2.

## 📋 Předpoklady
- ✅ Máte EC2 instanci
- ✅ Máte .pem SSH klíč
- ✅ PyCharm je propojený s EC2

## 🔧 Krok 1: Nastavení PyCharm Deployment

### Pokud ještě nemáte nastaveno:
1. **Tools → Deployment → Configuration**
2. **Klikněte + (přidat) → SFTP**
3. **Vyplňte:**
   - Name: `AWS EC2 Monitor`
   - Host: `vaše-ec2-ip`
   - Username: `ec2-user` (nebo `ubuntu`)
   - Authentication: Key pair
   - Private key: vyberte váš `.pem` soubor
   - Root path: `/home/ec2-user/binance-monitor`

4. **Test připojení:** klikněte "Test Connection"

### Mapping (důležité!):
- Local path: `/Users/.../binance_monitor_playground`
- Deployment path: `/`
- Web path: nechat prázdné

## 📤 Krok 2: Upload projektu

1. **Pravým tlačítkem na projekt** → Deployment → Upload to AWS EC2 Monitor
2. Nebo: **Tools → Deployment → Upload to AWS EC2 Monitor**
3. Počkejte na dokončení (vidíte progress bar)

## 💻 Krok 3: SSH Terminal v PyCharm

1. **Tools → Start SSH Session → AWS EC2 Monitor**
2. Nebo: **View → Tool Windows → Terminal** → New Session → SSH

## 🛠️ Krok 4: Instalace na serveru

V SSH terminálu spusťte postupně:

```bash
# 1. Přejděte do projektu
cd /home/ec2-user/binance-monitor

# 2. Vytvořte Python prostředí
python3 -m venv venv
source venv/bin/activate

# 3. Nainstalujte závislosti
pip install -r requirements.txt

# 4. Vytvořte konfiguraci
cp deployment/aws/.env.example .env
nano .env
```

### Vyplňte v .env souboru:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
BINANCE_API_KEY=váš_api_klíč
BINANCE_API_SECRET=váš_secret
```

Uložte: `Ctrl+X`, pak `Y`, pak `Enter`

## 🧪 Krok 5: Test

```bash
# Test připojení k Binance
python test_binance_aws.py

# Test jednoho běhu monitoringu
python -m api.index

# Pokud vše funguje, pokračujte...
```

## 🏃 Krok 6: Spuštění aplikace

### Možnost A: Screen (doporučeno)
```bash
# Vytvořte screen session
screen -S monitor

# Spusťte aplikaci
python deployment/aws/run_forever.py

# Odpojte se (aplikace běží dál)
# Stiskněte: Ctrl+A, pak D
```

### Možnost B: Nohup
```bash
# Spusťte na pozadí
nohup python deployment/aws/run_forever.py > logs/monitor.log 2>&1 &

# Zobrazí PID procesu
echo $!
```

## 📊 Krok 7: Přístup k dashboardu

### V PyCharm:
1. **View → Tool Windows → Database**
2. **SSH/SSL tab → Use SSH tunnel**
3. Nebo použijte SSH tunel:

```bash
# Na lokálním počítači (ne na serveru!)
ssh -i váš-klíč.pem -L 8000:localhost:8000 ec2-user@ec2-ip
```

Pak otevřete: **http://localhost:8000**

## 🔍 Užitečné příkazy

### Kontrola běžící aplikace:
```bash
# Zobrazit screen sessions
screen -ls

# Připojit se zpět
screen -r monitor

# Zobrazit logy
tail -f logs/continuous_runner.log
```

### Restart aplikace:
```bash
# Zastavit
screen -X -S monitor quit

# Spustit znovu
screen -S monitor
python deployment/aws/run_forever.py
```

### Synchronizace změn z PyCharm:
1. Udělejte změny lokálně
2. **Tools → Deployment → Upload to AWS EC2 Monitor**
3. Restartujte aplikaci na serveru

## ❓ Časté problémy

### "Permission denied" při SSH
- Zkontrolujte že .pem soubor má správná práva: `chmod 400 váš-klíč.pem`

### "Module not found"
- Ujistěte se že jste v aktivním venv: `source venv/bin/activate`

### Dashboard se nenačítá
- Zkontrolujte firewall/security group - port 8000 musí být otevřený
- Nebo použijte SSH tunel (bezpečnější)

## 📝 Poznámky

- Aplikace sbírá data každou hodinu
- Logy najdete v `/home/ec2-user/binance-monitor/logs/`
- Dashboard běží na portu 8000
- Po restartu EC2 je potřeba aplikaci spustit znovu