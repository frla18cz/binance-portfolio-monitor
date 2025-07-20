# Process Lock Documentation

## Přehled

Process Lock je mechanismus, který zabraňuje spuštění více instancí Binance Portfolio Monitoru současně. Používá file-based locking s kontrolou běžících procesů.

## Jak Process Lock funguje

### 1. Základní princip

Když spustíte monitoring (`run_forever.py`):

1. **Vytvoří se lock soubor**: `/tmp/.binance_monitor.lock`
2. **Do souboru se zapíše JSON** s informacemi:
   ```json
   {
     "pid": 12345,
     "timestamp": "2025-07-20T10:30:00+00:00",
     "hostname": "ip-172-31-47-56"
   }
   ```
3. **Při ukončení** se lock soubor smaže

### 2. Kontrola při spuštění

Když se pokusíte spustit druhou instanci:

1. **Zkontroluje existenci lock souboru**
2. **Pokud existuje**, přečte PID a zkontroluje:
   - Běží proces s tímto PID? → **ZAMÍTNUTO** (jiná instance běží)
   - Proces neběží? → Pokračuje k další kontrole
3. **Kontrola stáří locku** (stale lock detection)

## Co je "Stale Lock"?

**Stale lock** = zastaralý/mrtvý lock = situace, kdy:
- Lock soubor existuje
- ALE proces, který ho vytvořil, už neběží (crashed, killed, server restart)
- Lock soubor zůstal "viset" v systému

### Příklad vzniku stale locku:

1. Spustíte monitoring (PID 12345)
2. Server se náhle restartuje (power outage, crash)
3. Lock soubor `/tmp/.binance_monitor.lock` zůstane
4. Po restartu už proces 12345 neexistuje
5. Lock je "stale" (zastaralý)

## Stale Lock Detection

Process Lock automaticky detekuje a řeší stale locks:

```python
def acquire(self, max_age_seconds: int = 3600) -> bool:
    """
    max_age_seconds: Maximum stáří lock souboru (default 1 hodina)
    """
```

### Jak to funguje:

1. **Čte timestamp z lock souboru**
2. **Vypočítá stáří**: `age = now - lock_timestamp`
3. **Pokud `age > max_age_seconds` (1 hodina)**:
   - Lock je považován za "stale"
   - Může být převzat novou instancí
   - I když původní proces možná stále běží!

### Příklad scénáře:

```
10:00 - Instance A vytvoří lock (PID 12345)
10:30 - Instance A stále běží normálně
11:00 - Instance A stále běží normálně
11:01 - Pokus o spuštění Instance B:
        - Lock je starší než 1 hodina
        - Instance B převezme lock!
        - Teď běží 2 instance (což nechceme)
```

## Praktické scénáře

### Scénář 1: Normální běh
```
$ python deployment/aws/run_forever.py
✅ Process lock získán
🚀 Monitoring běží...
```

### Scénář 2: Pokus o duplicitní spuštění
```
# Terminal 1
$ python deployment/aws/run_forever.py
✅ Process lock získán
🚀 Monitoring běží...

# Terminal 2 (současně)
$ python deployment/aws/run_forever.py
❌ Jiná instance monitoringu již běží!
Pokud jste si jisti, že žádná jiná instance neběží, smažte lock soubor: /tmp/.binance_monitor.lock
```

### Scénář 3: Po crashy
```
# Monitoring crashnul, lock soubor zůstal
$ python deployment/aws/run_forever.py
# Zkontroluje PID - proces neběží
✅ Process lock získán (starý lock byl mrtvý)
🚀 Monitoring běží...
```

### Scénář 4: Stale lock (po 1 hodině)
```
# Instance běží déle než 1 hodinu
# Někdo se pokusí spustit druhou instanci
$ python deployment/aws/run_forever.py
⚠️  Lock je starší než 1 hodina, převezmu ho
✅ Process lock získán
🚀 Monitoring běží...
# POZOR: Teď možná běží 2 instance!
```

## Kde funguje Process Lock?

- ✅ **Linux** (AWS EC2, Ubuntu, etc.)
- ✅ **macOS** (lokální development)
- ✅ **Jakýkoliv Unix systém** s `/tmp` adresářem
- ❌ **Windows** - potřebuje úpravu cesty (např. `C:\Temp`)

## Troubleshooting

### Problém 1: "Jiná instance již běží" ale žádná neběží

**Příčina**: Stale lock po crashy

**Řešení**:
```bash
# Zkontrolujte běžící procesy
ps aux | grep python | grep run_forever

# Pokud žádný neběží, smažte lock
rm /tmp/.binance_monitor.lock

# Spusťte znovu
python deployment/aws/run_forever.py
```

### Problém 2: Chci spustit víc instancí záměrně

**Řešení**: Použijte různé lock names
```python
# Instance 1
lock = ProcessLock("binance_monitor_account1")

# Instance 2  
lock = ProcessLock("binance_monitor_account2")
```

### Problém 3: Lock soubor nemůžu smazat

**Příčina**: Nedostatečná oprávnění

**Řešení**:
```bash
# Zkontrolujte vlastníka
ls -la /tmp/.binance_monitor.lock

# Smažte s sudo
sudo rm /tmp/.binance_monitor.lock
```

## Konfigurace

### Změna timeout pro stale lock

V `run_forever.py`:
```python
# Default: 1 hodina
lock.acquire()

# Vlastní timeout: 2 hodiny
lock.acquire(max_age_seconds=7200)

# Vlastní timeout: 30 minut
lock.acquire(max_age_seconds=1800)
```

### Změna umístění lock souboru

V `utils/process_lock.py`:
```python
# Default
ProcessLock("binance_monitor", lock_dir="/tmp")

# Vlastní umístění
ProcessLock("binance_monitor", lock_dir="/var/run")
ProcessLock("binance_monitor", lock_dir="/home/user/locks")
```

## Best Practices

1. **Neměňte default timeout** (1 hodina) bez dobrého důvodu
2. **Monitorujte logy** pro "lock acquired" a "lock released" zprávy
3. **Při deploymentu** vždy zastavte starou instanci před spuštěním nové
4. **Používejte systemd** nebo supervisor pro automatický restart po crashy
5. **Pravidelně kontrolujte**, že neběží duplicitní instance:
   ```bash
   ps aux | grep -c "run_forever.py"
   ```

## Technické detaily

### Kontrola běžícího procesu

```python
def _is_process_running(self, pid: int) -> bool:
    try:
        os.kill(pid, 0)  # Signal 0 = jen kontrola, nezabíjí
        return True
    except ProcessLookupError:
        return False  # Proces neexistuje
    except PermissionError:
        return True   # Proces existuje, ale nemáme práva
```

### Struktura lock souboru

```json
{
  "pid": 12345,              // Process ID
  "timestamp": "2025-07...", // ISO format s timezone
  "hostname": "ip-172..."    // Název serveru
}
```

### Context Manager podpora

```python
# Automatické uvolnění locku
with ProcessLock("binance_monitor") as lock:
    # Váš kód zde
    pass
# Lock se automaticky uvolní
```

## Závěr

Process Lock je jednoduchý ale účinný mechanismus prevence duplicitních běhů. Hlavní omezení je 1-hodinový timeout pro stale lock detection - pokud váš monitoring běží déle než hodinu nepřetržitě, zvažte zvýšení tohoto limitu nebo použití robustnějšího řešení (systemd, supervisor).