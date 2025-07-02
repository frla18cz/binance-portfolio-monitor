# Binance Python SDK Dokumentace

## Přehled
Binance Connector Python je oficiální Python SDK pro Binance API. Podporuje jak REST API tak WebSocket připojení pro real-time data streaming.

## Instalace

```bash
pip install binance-connector
```

Alternativně z GitHub repozitáře:
```bash
pip install git+https://github.com/binance/binance-connector-python.git
```

## Základní konfigurace

### REST API Client

```python
from binance.spot import Spot

# Veřejné endpointy (bez autentifikace)
client = Spot()

# Privátní endpointy (s API klíči)  
client = Spot(api_key='<api_key>', api_secret='<api_secret>')

# Testnet
client = Spot(base_url='https://testnet.binance.vision')

# S dalšími parametry
client = Spot(
    api_key='<api_key>',
    api_secret='<api_secret>',
    base_url='https://api.binance.com',
    timeout=10,
    show_limit_usage=True,
    show_header=True
)
```

### Autentifikační metody

```python
# HMAC (výchozí)
client = Spot(api_key='<api_key>', api_secret='<api_secret>')

# RSA klíče
client = Spot(api_key='<api_key>', private_key='<private_key_content>')

# ED25519 klíče
with open('./private_key.pem', 'rb') as f:
    private_key = f.read()
client = Spot(api_key='<api_key>', private_key=private_key, private_key_pass='<password>')
```

## REST API Příklady

### Market Data (veřejné)

```python
from binance.spot import Spot

client = Spot()

# Server time
print(client.time())

# Exchange info
print(client.exchange_info())

# Klines/Candlestick data
print(client.klines("BTCUSDT", "1m"))
print(client.klines("BNBUSDT", "1h", limit=10))

# Order book
print(client.depth("BTCUSDT"))

# Recent trades
print(client.trades("BTCUSDT"))

# 24hr ticker statistics
print(client.ticker_24hr("BTCUSDT"))

# Current price
print(client.ticker_price("BTCUSDT"))
```

### Account & Trading (privátní)

```python
client = Spot(api_key='<api_key>', api_secret='<api_secret>')

# Account information
print(client.account())

# Open orders
print(client.get_open_orders())

# Order history
print(client.get_orders("BTCUSDT"))

# Trade history
print(client.my_trades("BTCUSDT"))

# Nový obchod - Market order
market_order = {
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'type': 'MARKET',
    'quantity': 0.001
}
response = client.new_order(**market_order)

# Nový obchod - Limit order
limit_order = {
    'symbol': 'BTCUSDT',
    'side': 'SELL',
    'type': 'LIMIT',
    'timeInForce': 'GTC',
    'quantity': 0.002,
    'price': 50000
}
response = client.new_order(**limit_order)

# Zrušit obchod
client.cancel_order('BTCUSDT', orderId=12345)

# Zrušit všechny otevřené obchody
client.cancel_open_orders('BTCUSDT')
```

## WebSocket API

### WebSocket API Client

```python
import logging
from binance.websocket.spot.websocket_api import SpotWebsocketAPIClient

def message_handler(_, message):
    logging.info(message)

def on_close(_):
    logging.info("Connection closed")

# Inicializace
ws_client = SpotWebsocketAPIClient(
    on_message=message_handler,
    on_close=on_close
)

# Test připojení
ws_client.ping_connectivity()

# Server time
ws_client.server_time()

# Ticker data
ws_client.ticker(symbol="BNBBUSD", type="FULL")

# Multiple symbols
ws_client.ticker(
    symbols=["BNBBUSD", "BTCUSDT"],
    type="MINI",
    windowSize="2h"
)

# Account info (vyžaduje API klíče)
ws_client.account()

# Nový obchod přes WebSocket
ws_client.new_order(
    symbol="BTCUSDT",
    side="BUY",
    type="MARKET",
    quantity=0.001
)

# Zavřít připojení
ws_client.stop()
```

### WebSocket Stream Client

```python
import logging
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient

def message_handler(_, message):
    logging.info(message)

# Inicializace
ws_client = SpotWebsocketStreamClient(on_message=message_handler)

# Aggregate trades
ws_client.agg_trade(symbol="bnbusdt")

# Kline/Candlestick streams
ws_client.kline(symbol="btcusdt", interval="1m")

# Ticker streams
ws_client.ticker(symbol="ethusdt")

# Order book streams
ws_client.partial_book_depth(symbol="adausdt", level=10, speed=100)

# All market tickers
ws_client.all_ticker()

# Kombinované streamy
ws_client.instant_subscribe([
    'bnbusdt@bookTicker',
    'ethusdt@bookTicker'
], callback=message_handler)

# Zavřít připojení
ws_client.stop()
```

## Pokročilé funkce

### Proxy nastavení

```python
from binance.spot import Spot
from binance.websocket.spot.websocket_api import SpotWebsocketAPIClient

# REST API s proxy
proxies = {'https': 'http://1.2.3.4:8080'}
client = Spot(proxies=proxies)

# WebSocket s proxy
ws_client = SpotWebsocketAPIClient(
    on_message=message_handler,
    proxies=proxies
)
```

### Timeout a další parametry

```python
# Timeout
client = Spot(timeout=10)

# Time unit (microseconds vs milliseconds)
client = Spot(time_unit="microsecond")

# Show rate limit usage
client = Spot(show_limit_usage=True)

# Show response headers
client = Spot(show_header=True)

# RecvWindow pro signed endpoints
client = Spot(api_key='<key>', api_secret='<secret>')
response = client.get_order('BTCUSDT', orderId=11, recvWindow=10000)
```

### Request IDs pro WebSocket

```python
# Custom request ID
ws_client.ping_connectivity(id="my_request_id")

# Auto-generated ID
ws_client.ping_connectivity()
```

## Dostupné moduly a funkce

### Market Data
- `ping()` - Test připojení
- `time()` - Server time  
- `exchange_info()` - Exchange informace
- `depth()` - Order book
- `trades()` - Recent trades
- `klines()` - Kline/candlestick data
- `ticker_24hr()` - 24hr ticker statistics
- `ticker_price()` - Symbol price ticker
- `book_ticker()` - Order book ticker

### Account & Trading
- `account()` - Account informace
- `new_order()` - Nový obchod
- `cancel_order()` - Zrušit obchod
- `get_order()` - Detail obchodu
- `get_open_orders()` - Otevřené obchody
- `get_orders()` - Historie obchodů
- `my_trades()` - Trade history

### Wallet
- `system_status()` - System status
- `coin_info()` - Coin informace
- `account_snapshot()` - Account snapshot
- `withdraw_history()` - Výběr historie
- `deposit_address()` - Deposit adresa
- `user_asset()` - User assets

### Margin Trading
- Margin account management
- Margin trading operations
- Cross/Isolated margin

### Futures
- Futures account info
- Futures trading
- Position management

### Staking
- ETH staking operations
- Staking rewards
- WBETH operations

### Sub-Account Management
- Sub-account creation
- Asset transfers
- Sub-account trading

## Error Handling

```python
from binance.spot import Spot
from binance.error import ClientError, ServerError

client = Spot(api_key='<key>', api_secret='<secret>')

try:
    response = client.account()
except ClientError as error:
    print(f"Client error: {error.status_code} - {error.error_message}")
except ServerError as error:
    print(f"Server error: {error.status_code} - {error.error_message}")
```

## Testování

```bash
# Instalace test dependencies
pip install -r requirements/requirements-test.txt

# Spuštění testů
python -m pytest tests/
```

## Konfigurace pro examples

Vytvoř `examples/config.ini`:
```ini
[keys]
api_key=your_api_key_here
api_secret=your_api_secret_here
```

## Užitečné odkazy

- [Oficiální GitHub repo](https://github.com/binance/binance-connector-python)
- [Binance API dokumentace](https://binance-docs.github.io/apidocs/)
- [Binance Testnet](https://testnet.binance.vision/)

## Poznámky

- Všechny privátní endpointy vyžadují API key a secret
- Pro production používej pouze HTTPS
- Respektuj rate limity
- Pro testování používej Binance Testnet
- WebSocket připojení automaticky ping-pong pro keep-alive
- SDK podporuje jak sync tak async operace přes WebSocket