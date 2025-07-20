# Synchronizace běhů monitoringu s hodinami

## Přehled

Tato dokumentace popisuje funkci synchronizace běhů monitoringu s reálným časem. Namísto relativního plánování od času spuštění se monitoring nyní spouští v pevně daných časech synchronizovaných s hodinami.

## Jak to funguje

### Předchozí chování (relativní plánování)
- Spuštění v 14:37 s intervalem 10 minut
- Běhy: 14:47, 14:57, 15:07, 15:17...

### Nové chování (synchronizované plánování)
- Spuštění v 14:37 s intervalem 10 minut
- Běhy: 14:40, 14:50, 15:00, 15:10...

## Příklady synchronizace

### Interval 5 minut
Běhy v: :00, :05, :10, :15, :20, :25, :30, :35, :40, :45, :50, :55

### Interval 10 minut
Běhy v: :00, :10, :20, :30, :40, :50

### Interval 15 minut
Běhy v: :00, :15, :30, :45

### Interval 30 minut
Běhy v: :00, :30

### Interval 60 minut
Běhy v: :00

## Implementace

Funkce `calculate_next_run()` v souboru `deployment/aws/run_forever.py` nyní:

1. **Získá aktuální čas**: `datetime.now()`
2. **Načte interval**: Ze souboru `config/settings.json`
3. **Vypočítá další časový slot**:
   - Zjistí kolik minut uplynulo od začátku hodiny
   - Určí, kolik intervalů již proběhlo
   - Vypočítá kdy bude další interval
4. **Zaokrouhlí na celé sekundy**: Nastaví sekundy a mikrosekundy na 0
5. **Ošetří přechod přes půlnoc**: Správně zpracuje přechod na další den

## Výhody

### 1. Předvídatelnost
- Administrátoři přesně vědí, kdy monitoring poběží
- Snadnější plánování údržby a kontroly

### 2. Synchronizace s jinými systémy
- Kompatibilní s cron úlohami
- Snadná integrace s externími systémy

### 3. Lepší debugging
- V logech jsou časy běhů konzistentní
- Jednodušší analýza problémů

### 4. Úspora zdrojů
- Více instancí může sdílet stejné časové sloty
- Efektivnější využití cache

## Konfigurace

Interval se nastavuje v souboru `config/settings.json`:

```json
{
  "scheduling": {
    "cron_interval_minutes": 10,
    ...
  }
}
```

## Příklad běhu

```
🚀 První spuštění monitoringu...
✅ Monitoring úspěšně dokončen
⏰ Další běh naplánován na: 14:40:00 (za 3 minut)
💤 Čekám 180 sekund...

🔄 Běh #2
✅ Monitoring úspěšně dokončen
⏰ Další běh naplánován na: 14:50:00 (za 10 minut)
💤 Čekám 600 sekund...
```

## Testování

Pro otestování funkcionality:

1. Nastavte krátký interval (např. 5 minut)
2. Spusťte monitoring v libovolný čas
3. Ověřte, že další běhy jsou synchronizované s hodinami

```bash
# Nastavit 5 minutový interval
# V config/settings.json: "cron_interval_minutes": 5

# Spustit monitoring
cd deployment/aws
./start_monitor.sh

# Sledovat logy
tail -f ~/binance_monitor/logs/continuous_runner.log
```

## Poznámky

- První běh po spuštění proběhne ihned
- Následující běhy jsou již synchronizované
- Při změně intervalu je nutné restartovat monitoring
- Funkce správně zpracovává přechod přes půlnoc