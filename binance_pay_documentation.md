# Binance Pay - Získání výběrů a vkladů přes telefon/email

## Rychlý přehled

Tato dokumentace popisuje, jak získat **všechny platby přes telefon/email** z Binance účtu pomocí přímého volání Binance API (bez CCXT).

### Co získáte:
- ✅ Všechny příchozí platby přes telefon/email/Pay ID
- ✅ Všechny odchozí platby přes telefon/email/Pay ID  
- ✅ **BEZ ČASOVÉHO LIMITU** - vidíte všechny transakce

## Požadavky

### 1. API klíč
- Pouze **Enable Reading** (read-only) oprávnění
- Získáte na: Binance → API Management

### 2. Python knihovny
```bash
pip install requests
```
Žádné další knihovny nejsou potřeba!

## Jak to funguje

### Binance Pay endpoint
```
GET /sapi/v1/pay/transactions
```

**Důležité vlastnosti:**
- ✅ **Žádný časový limit** - vrací VŠECHNY transakce
- ✅ Obsahuje telefon/email platby
- ✅ Rozlišuje příchozí (kladná částka) a odchozí (záporná částka)

## Použití

### 1. Stáhněte skript
```bash
# Soubor: binance_pay_simple.py
```

### 2. Nastavte API údaje
```python
API_KEY = "váš_api_klíč"
API_SECRET = "váš_api_secret"
```

### 3. Spusťte
```bash
python binance_pay_simple.py
```

## Výstup

```
📱 BINANCE PAY TRANSAKCE (celkem: 4)
================================================================================

📥 PŘÍCHOZÍ PLATBY (2)
--------------------------------------------------------------------------------
⏰ Čas: 2025-07-02 14:14:27
💰 Částka: 6000.0 USDC
👤 Od: User-19af8
🔖 ID: P_A1UBSK9SJNN71115

📤 ODCHOZÍ PLATBY (2)  
--------------------------------------------------------------------------------
⏰ Čas: 2025-07-18 14:37:43
💰 Částka: 10.0 USDC
👤 Komu: User-Tomas_
📧 Email: rozirozi@seznam.cz
🔖 ID: P_A1UPBE6WV3H71113
```

## Struktura dat z API

### Příchozí platba (JSON)
```json
{
    "amount": "6000",              // Kladné číslo
    "currency": "USDC",
    "transactionTime": "1719949467394",
    "transactionId": "P_A1UBSK9SJNN71115",
    "payerInfo": {
        "name": "User-19af8",      // Jméno odesílatele
        "binanceId": "38755365"
    }
}
```

### Odchozí platba (JSON)
```json
{
    "amount": "-10",               // Záporné číslo
    "currency": "USDC",
    "transactionTime": "1721327863518",
    "transactionId": "P_A1UPBE6WV3H71113",
    "receiverInfo": {
        "name": "User-Tomas_",
        "email": "rozirozi@seznam.cz",  // Email příjemce
        "accountId": "235656193"
    }
}
```

## Klíčový kód (jak to funguje)

### 1. Vytvoření podpisu
```python
def create_signature(params, secret):
    query_string = urlencode(params)
    signature = hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature
```

### 2. Volání API
```python
def get_pay_transactions():
    endpoint = "/sapi/v1/pay/transactions"
    
    params = {
        'timestamp': int(time.time() * 1000)
    }
    
    params['signature'] = create_signature(params, API_SECRET)
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    response = requests.get(
        BASE_URL + endpoint,
        headers=headers,
        params=params
    )
    
    return response.json()
```

### 3. Rozlišení příchozích/odchozích
```python
for transaction in transactions:
    amount = float(transaction.get('amount', 0))
    if amount > 0:
        # Příchozí platba
        print(f"Přijato: +{amount}")
    else:
        # Odchozí platba  
        print(f"Odesláno: {amount}")
```

## Časté otázky

### Proč nevidím telefon/email odesílatele?
Binance z důvodu ochrany soukromí nezobrazuje kontaktní údaje odesílatelů. Vidíte pouze jejich uživatelské jméno.

### Je nějaký časový limit?
**NE!** Endpoint `/sapi/v1/pay/transactions` vrací všechny dostupné transakce bez ohledu na stáří.

### Potřebuji CCXT?
**NE!** Skript používá pouze standardní Python knihovnu `requests`.

### Mohu filtrovat podle data?
API endpoint nepodporuje filtrování podle data. Vrací všechny transakce najednou.

## Alternativní řešení s CCXT

Pokud už používáte CCXT:
```python
import ccxt

exchange = ccxt.binance({
    "apiKey": API_KEY,
    "secret": API_SECRET
})

# Stejný endpoint
transactions = exchange.sapi_get_pay_transactions()
```

## Binance Pay API Reference (pro LLM/AI)

### Endpoint specifikace
```
GET https://api.binance.com/sapi/v1/pay/transactions
```

**Účel:** Získání všech Binance Pay transakcí (platby přes telefon/email/Pay ID)

### Požadované parametry

| Parametr | Typ | Povinný | Popis |
|----------|-----|---------|-------|
| `timestamp` | LONG | ANO | Unix timestamp v milisekundách |
| `signature` | STRING | ANO | HMAC SHA256 podpis |
| `recvWindow` | LONG | NE | Časové okno platnosti (výchozí: 5000ms) |

### Autentizace

1. **API klíč v hlavičce:**
   ```
   X-MBX-APIKEY: váš_api_klíč
   ```

2. **Vytvoření podpisu:**
   ```python
   # 1. Sestavit query string
   query_string = "timestamp=1625097600000"
   
   # 2. Vytvořit HMAC SHA256
   signature = hmac.new(
       api_secret.encode('utf-8'),
       query_string.encode('utf-8'),
       hashlib.sha256
   ).hexdigest()
   
   # 3. Přidat podpis
   final_url = f"?{query_string}&signature={signature}"
   ```

### Response struktura

```json
{
    "code": "000000",
    "message": "success",
    "data": [
        {
            // Společné atributy
            "orderType": "C2C",
            "transactionId": "P_A1UBSK9SJNN71115",
            "transactionTime": "1719949467394",
            "amount": "6000",              // Kladné = příchozí, záporné = odchozí
            "currency": "USDC",
            "walletType": "2",
            
            // Pro příchozí platby
            "payerInfo": {
                "name": "User-19af8",      // Uživatelské jméno odesílatele
                "binanceId": "38755365",
                "email": "sender@email.com", // Pouze pokud je dostupné
                "phone": "+1234567890"       // Pouze pokud je dostupné
            },
            
            // Pro odchozí platby
            "receiverInfo": {
                "name": "User-Tomas_",
                "type": "USER",
                "email": "rozirozi@seznam.cz",
                "accountId": "235656193"
            }
        }
    ],
    "success": true
}
```

### Rozlišení typu transakce

```python
# Příchozí vs odchozí
if float(transaction['amount']) > 0:
    # Příchozí platba - hledejte payerInfo
    sender = transaction['payerInfo']['name']
else:
    # Odchozí platba - hledejte receiverInfo
    recipient = transaction['receiverInfo']['email']
```

### Příklady volání

#### cURL
```bash
timestamp=$(date +%s000)
query="timestamp=$timestamp"
signature=$(echo -n "$query" | openssl dgst -sha256 -hmac "$API_SECRET" | cut -d' ' -f2)

curl -H "X-MBX-APIKEY: $API_KEY" \
     "https://api.binance.com/sapi/v1/pay/transactions?$query&signature=$signature"
```

#### Python (requests)
```python
import requests
import time
import hmac
import hashlib

def get_binance_pay_transactions(api_key, api_secret):
    base_url = "https://api.binance.com"
    endpoint = "/sapi/v1/pay/transactions"
    
    timestamp = int(time.time() * 1000)
    params = f"timestamp={timestamp}"
    
    signature = hmac.new(
        api_secret.encode('utf-8'),
        params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {'X-MBX-APIKEY': api_key}
    url = f"{base_url}{endpoint}?{params}&signature={signature}"
    
    response = requests.get(url, headers=headers)
    return response.json()
```

#### JavaScript (Node.js)
```javascript
const crypto = require('crypto');
const axios = require('axios');

async function getBinancePayTransactions(apiKey, apiSecret) {
    const timestamp = Date.now();
    const params = `timestamp=${timestamp}`;
    
    const signature = crypto
        .createHmac('sha256', apiSecret)
        .update(params)
        .digest('hex');
    
    const url = `https://api.binance.com/sapi/v1/pay/transactions?${params}&signature=${signature}`;
    
    const response = await axios.get(url, {
        headers: { 'X-MBX-APIKEY': apiKey }
    });
    
    return response.data;
}
```

### Rate limity
- Weight: 3000
- Limit: 12000 požadavků za minutu pro IP
- Doporučení: Cachovat odpovědi, endpoint vrací všechny transakce

### Chybové kódy
- `-1102`: Povinný parametr chybí
- `-1021`: Timestamp mimo rozsah serverového času
- `-1022`: Neplatný podpis
- `-2014`: Neplatný API klíč

### Důležité poznámky pro LLM
1. **Časový limit:** Tento endpoint NEMÁ časový limit - vrací všechny transakce
2. **Filtrování:** Endpoint nepodporuje filtrování - musíte filtrovat lokálně
3. **Identifikace plateb:** Příchozí mají kladnou částku, odchozí zápornou
4. **Soukromí:** Email/telefon odesílatele často není dostupný z důvodu ochrany soukromí
5. **Oprávnění:** Stačí read-only API klíč s povoleným čtením

## Závěr

- Jednoduchý skript (150 řádků)
- Žádné externí knihovny kromě `requests`
- Získáte všechny telefon/email platby
- Bez časového limitu
- Read-only API klíč stačí