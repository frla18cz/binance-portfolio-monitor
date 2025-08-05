# První běh po resetu - Jak to funguje

## Přehled

Když smažete všechna data pro účet (jako jsme udělali pro Ondra(test)), systém se při prvním běhu chová speciálně, aby zabránil dvojitému započítání transakcí.

## Krok po kroku - Co se děje při prvním běhu

### 1. Kontrola benchmark konfigurace

```python
if not config.get('btc_units') and not config.get('eth_units'):
    # Benchmark není inicializovaný!
```

- Systém zjistí, že `btc_units = 0` a `eth_units = 0`
- To znamená, že účet ještě nebyl inicializován

### 2. Inicializace benchmarku

```python
config = initialize_benchmark(db_client, config, account_id, nav, prices, logger)
```

Při inicializaci se stane:
- Vezme se aktuální NAV (např. 1650 USD)
- Rozdělí se 50/50 mezi BTC a ETH
- Vypočítají se jednotky: `btc_units = 825 / btc_price`, `eth_units = 825 / eth_price`
- **DŮLEŽITÉ**: Nastaví se `initialized_at = NOW()`

### 3. Načtení transakcí

Systém načte transakce z Binance API:
- Deposits (vklady)
- Withdrawals (výběry)
- Pay transactions (email/phone převody)

**Od kdy?** Od `last_processed_timestamp` nebo posledních 30 dní

### 4. Filtrování transakcí - KLÍČOVÝ KROK!

```python
initialized_at = config.get('initialized_at')
if initialized_at:
    initialized_dt = datetime.fromisoformat(initialized_at)
    
    # Odfiltrují se transakce PŘED inicializací
    unprocessed_transactions = [
        txn for txn in unprocessed_transactions
        if datetime.fromisoformat(txn['timestamp']) >= initialized_dt
    ]
```

**Co to znamená?**
- Všechny transakce PŘED `initialized_at` se IGNORUJÍ
- Zpracují se pouze transakce PO inicializaci

## Příklad scénáře

### Timeline:
```
2025-07-15 10:00 - Deposit 1000 USDT (historická transakce)
2025-07-17 14:00 - Withdrawal 50 USDT (historická transakce)
2025-07-20 12:00 - RESET DAT (smazání všeho)
2025-07-20 12:15 - První běh monitoru:
                   - NAV = 1650 USD
                   - Benchmark inicializován na 1650 USD
                   - initialized_at = 2025-07-20 12:15
2025-07-20 13:00 - Nový deposit 100 USDT
```

### Co se zpracuje?
- ❌ Deposit 1000 USDT - NE (před initialized_at)
- ❌ Withdrawal 50 USDT - NE (před initialized_at)
- ✅ Deposit 100 USDT - ANO (po initialized_at)

## Proč je to důležité?

### Bez tohoto mechanismu:
1. Benchmark by se inicializoval na 1650 USD
2. Pak by se přičetl historický deposit 1000 USDT → benchmark 2650 USD
3. Odečetl by se withdrawal 50 USDT → benchmark 2600 USD
4. Ale NAV je jen 1650 USD!
5. **Výsledek**: Benchmark by byl o 950 USD vyšší než NAV

### S tímto mechanismem:
1. Benchmark se inicializuje na 1650 USD
2. Historické transakce se ignorují
3. Benchmark = NAV = 1650 USD ✅

## Jak ověřit, že to funguje správně?

### 1. Zkontrolujte logy

Hledejte zprávu:
```
"pre_init_filtered" - "Filtered out X pre-initialization transactions"
```

### 2. SQL dotaz
```sql
-- Zkontrolujte initialized_at
SELECT account_id, btc_units, eth_units, initialized_at
FROM benchmark_configs
WHERE account_id = 'your-account-id';

-- Zkontrolujte, že nejsou staré transakce
SELECT COUNT(*) 
FROM processed_transactions
WHERE account_id = 'your-account-id'
AND timestamp < (
    SELECT initialized_at 
    FROM benchmark_configs 
    WHERE account_id = 'your-account-id'
);
-- Mělo by vrátit 0
```

## FAQ

### Q: Co když chci zpracovat i historické transakce?

A: Museli byste:
1. Smazat `initialized_at` z benchmark_configs
2. Nebo ho nastavit na dřívější datum
3. **ALE POZOR**: To může vést k nesprávným výpočtům!

### Q: Jak dlouho zpět systém hledá transakce?

A: Standardně 30 dní (`settings.scheduling.historical_period_days`)

### Q: Co se stane, když během inicializace přijde nová transakce?

A: Zpracuje se při dalším běhu. Systém si pamatuje `last_processed_timestamp`.

### Q: Můžu resetovat jen transakce, ale nechat benchmark?

A: Ano, ale musíte být opatrní:
```sql
-- Smazat jen transakce
DELETE FROM processed_transactions WHERE account_id = 'xxx';
DELETE FROM account_processing_status WHERE account_id = 'xxx';
-- Benchmark zůstane
```

## Shrnutí

První běh po resetu je navržen tak, aby:
1. Inicializoval benchmark na aktuální NAV
2. Ignoroval historické transakce před inicializací
3. Zabránil dvojitému započítání
4. Začal "čistý" monitoring od tohoto bodu

Toto chování je automatické a nevyžaduje žádnou konfiguraci.