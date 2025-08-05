# Zpracování transferů mezi sub-účty

Tento dokument popisuje, jak systém zpracovává transfery finančních prostředků mezi hlavním (master) účtem a jeho sub-účty. Správné zpracování těchto transferů je klíčové pro přesné sledování výkonnosti a správu benchmarku.

## Klíčové principy

1.  **Interní pohyb, ne cashflow**: Převody mezi master a sub-účty jsou považovány za interní přesuny kapitálu. **Nemění celkovou hodnotu spravovaných aktiv**, a proto by neměly být interpretovány jako vklady (deposits) nebo výběry (withdrawals) ve smyslu čistého peněžního toku (cashflow) do nebo ze systému.

2.  **Symetrické zpracování**: Každý transfer má dvě strany:
    *   **Odeslání (Withdrawal)** z jednoho účtu.
    *   **Přijetí (Deposit)** na druhém účtu.
    Systém musí detekovat a zpracovat obě tyto strany, aby byla zachována konzistence.

3.  **Úprava benchmarku**: Jelikož se jedná o interní přesun, celková hodnota benchmarku **zůstává nezměněna**. Mění se pouze alokace prostředků (a tedy i benchmarku) mezi jednotlivými účty.
    *   U účtu, který prostředky **odesílá**, se benchmark proporcionálně **sníží**.
    *   U účtu, který prostředky **přijímá**, se benchmark proporcionálně **zvýší**.

## Technická implementace

Detekce a zpracování transferů probíhá v několika krocích v rámci `api/index.py`:

1.  **Detekce transferů**: Funkce `get_sub_account_transfers` v `api/sub_account_helper.py` používá oficiální `python-binance` knihovnu k načtení historie transferů. Pro zajištění kompletních dat se vždy používají **master API klíče**, které mají jako jediné přehled o všech transakcích.

2.  **Normalizace**: Data z Binance API jsou normalizována do jednotného formátu, kde je jasně určen směr transakce (`SUB_DEPOSIT` nebo `SUB_WITHDRAWAL`) pro každý dotčený účet.

3.  **Výpočet cashflow**: Funkce `process_account_transfers` spočítá čistý peněžní tok pro **každý účet zvlášť**.
    *   Pro účet odesílatele je tok záporný (např. -100 USDC).
    *   Pro účet příjemce je tok kladný (např. +100 USDC).

4.  **Atomická úprava benchmarku**:
    *   Funkce `adjust_benchmark_for_cashflow` je zavolána pro každý účet s jeho příslušným peněžním tokem.
    *   Tato funkce v rámci jedné databázové transakce provede následující:
        1.  Zapíše záznam o transakci do tabulky `processed_transactions`.
        2.  Zapíše záznam o úpravě do tabulky `benchmark_modifications`, kde je detailně popsán dopad na benchmark daného účtu.
        3.  Aktualizuje jednotky BTC a ETH v tabulce `benchmark_configs` pro daný účet.

Tento přístup zajišťuje, že každý interní transfer je správně zaúčtován, benchmarky jsou přesně upraveny a celý systém zůstává konzistentní.

