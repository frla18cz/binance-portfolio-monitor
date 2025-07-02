# Bybit Python SDK Documentation

## Overview

This documentation provides comprehensive guidance for integrating with Bybit's V5 API using the official Python SDK (`pybit`). The V5 API unifies trading across Spot, Derivatives, and Options products with a single, consistent interface.

## Key Features

- **Unified Trading**: Trade Spot, USDT Perpetual, USDC Perpetual, USDC Futures, Inverse Perpetual, Inverse Futures, and Options
- **Cross-Product Margin**: Portfolio margin mode with fund sharing across products
- **Unified Trading Account (UTA)**: Enhanced capital efficiency
- **Official Python SDK**: Lightweight, high-performance connector for HTTP and WebSocket APIs

## Installation

```bash
pip install pybit
```

**Requirements**: Python 3.9.1 or higher

## Authentication

### API Key Setup

1. Visit [Bybit API Management](https://www.bybit.com/app/user/api-management)
2. Generate API Key and Secret
3. Configure permissions for your trading needs

### Authentication Headers

```python
# Required headers for authenticated requests
headers = {
    'X-BAPI-API-KEY': 'your_api_key',
    'X-BAPI-TIMESTAMP': str(timestamp),
    'X-BAPI-RECV-WINDOW': '5000',
    'X-BAPI-SIGN': signature  # HMAC-SHA256 signature
}
```

## Quick Start

### Basic HTTP Session

```python
from pybit.unified_trading import HTTP

# Initialize session
session = HTTP(
    testnet=False,  # Set to True for testnet
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# Get server time
server_time = session.get_server_time()
print(f"Server time: {server_time}")
```

### Market Data

```python
# Get orderbook
orderbook = session.get_orderbook(
    category="linear",  # linear, inverse, option, spot
    symbol="BTCUSDT"
)

# Get recent trades
trades = session.get_public_trade_history(
    category="linear",
    symbol="BTCUSDT",
    limit=50
)

# Get kline data
klines = session.get_kline(
    category="linear",
    symbol="BTCUSDT",
    interval="1",  # 1m, 5m, 15m, 30m, 1h, 4h, 1d
    limit=100
)

# Get instrument info
instruments = session.get_instruments_info(
    category="linear",
    symbol="BTCUSDT"
)
```

## Trading Operations

### Account Information

```python
# Get account balance
balance = session.get_wallet_balance(
    accountType="UNIFIED"  # UNIFIED, CONTRACT, SPOT
)

# Get positions
positions = session.get_positions(
    category="linear",
    symbol="BTCUSDT"
)

# Get open orders
orders = session.get_open_orders(
    category="linear",
    symbol="BTCUSDT"
)
```

### Order Management

```python
# Place a market order
market_order = session.place_order(
    category="linear",
    symbol="BTCUSDT",
    side="Buy",
    orderType="Market",
    qty="0.001"
)

# Place a limit order
limit_order = session.place_order(
    category="linear",
    symbol="BTCUSDT",
    side="Buy",
    orderType="Limit",
    qty="0.001",
    price="45000"
)

# Place a conditional order
conditional_order = session.place_order(
    category="linear",
    symbol="BTCUSDT",
    side="Buy",
    orderType="Limit",
    qty="0.001",
    price="45000",
    triggerPrice="46000",
    triggerDirection=1,  # 1: rise, 2: fall
    triggerBy="LastPrice"
)

# Cancel an order
cancel_result = session.cancel_order(
    category="linear",
    symbol="BTCUSDT",
    orderId="order_id_here"
)

# Modify an order
modify_result = session.amend_order(
    category="linear",
    symbol="BTCUSDT",
    orderId="order_id_here",
    qty="0.002",
    price="44000"
)
```

### Batch Operations

```python
# Place multiple orders
batch_orders = session.place_batch_order(
    category="linear",
    request=[
        {
            "symbol": "BTCUSDT",
            "side": "Buy",
            "orderType": "Limit",
            "qty": "0.001",
            "price": "45000"
        },
        {
            "symbol": "ETHUSDT",
            "side": "Sell",
            "orderType": "Limit",
            "qty": "0.01",
            "price": "3000"
        }
    ]
)

# Cancel multiple orders
cancel_batch = session.cancel_batch_order(
    category="linear",
    request=[
        {"symbol": "BTCUSDT", "orderId": "order_id_1"},
        {"symbol": "ETHUSDT", "orderId": "order_id_2"}
    ]
)
```

## WebSocket Integration

### Real-time Market Data

```python
from pybit.unified_trading import WebSocket

def handle_message(message):
    print(f"Received: {message}")

# Initialize WebSocket
ws = WebSocket(
    testnet=False,
    channel_type="linear",  # linear, inverse, option, spot
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# Subscribe to orderbook
ws.orderbook_stream(
    symbol="BTCUSDT",
    callback=handle_message
)

# Subscribe to trade stream
ws.trade_stream(
    symbol="BTCUSDT",
    callback=handle_message
)

# Subscribe to kline stream
ws.kline_stream(
    symbol="BTCUSDT",
    interval="1",
    callback=handle_message
)
```

### Private WebSocket Streams

```python
# Subscribe to position updates
ws.position_stream(callback=handle_message)

# Subscribe to order updates
ws.order_stream(callback=handle_message)

# Subscribe to execution updates
ws.execution_stream(callback=handle_message)

# Subscribe to wallet updates
ws.wallet_stream(callback=handle_message)
```

## Categories and Symbols

### Supported Categories

- **linear**: USDT Perpetual, USDC Perpetual, USDC Futures
- **inverse**: Inverse Perpetual, Inverse Futures
- **spot**: Spot trading
- **option**: Options trading

### Common Symbols

```python
# Linear contracts
symbols = [
    "BTCUSDT",    # Bitcoin USDT Perpetual
    "ETHUSDT",    # Ethereum USDT Perpetual
    "ADAUSDT",    # Cardano USDT Perpetual
    "SOLUSDT",    # Solana USDT Perpetual
]

# Inverse contracts
inverse_symbols = [
    "BTCUSD",     # Bitcoin USD Perpetual
    "ETHUSD",     # Ethereum USD Perpetual
]

# Spot pairs
spot_symbols = [
    "BTCUSDT",    # Bitcoin/USDT Spot
    "ETHUSDT",    # Ethereum/USDT Spot
]
```

## Error Handling

```python
from pybit.exceptions import InvalidRequestError

try:
    # Make API call
    result = session.place_order(
        category="linear",
        symbol="BTCUSDT",
        side="Buy",
        orderType="Market",
        qty="0.001"
    )
    print(f"Order placed: {result}")
    
except InvalidRequestError as e:
    print(f"Invalid request: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Rate Limits

Bybit implements rate limiting to ensure fair usage:

- **Public endpoints**: Generally higher limits
- **Private endpoints**: Lower limits based on API key tier
- **WebSocket connections**: Limited concurrent connections

Always implement proper error handling and respect rate limits to avoid temporary bans.

## Advanced Features

### Portfolio Margin Mode

```python
# Switch to portfolio margin mode
switch_result = session.switch_margin_mode(
    category="linear",
    symbol="BTCUSDT",
    tradeMode=1,  # 0: cross margin, 1: isolated margin
    buyLeverage="10",
    sellLeverage="10"
)
```

### Risk Management

```python
# Set trading stop
stop_result = session.set_trading_stop(
    category="linear",
    symbol="BTCUSDT",
    positionIdx=0,  # 0: one-way mode, 1: buy side, 2: sell side
    stopLoss="40000",
    takeProfit="50000"
)

# Set leverage
leverage_result = session.set_leverage(
    category="linear",
    symbol="BTCUSDT",
    buyLeverage="10",
    sellLeverage="10"
)
```

## Best Practices

1. **Use Testnet First**: Always test your integration on testnet before going live
2. **Handle Rate Limits**: Implement exponential backoff for rate limit handling
3. **Secure API Keys**: Store API keys securely, never commit them to version control
4. **Error Handling**: Always wrap API calls in try-catch blocks
5. **WebSocket Reconnection**: Implement reconnection logic for WebSocket streams
6. **Position Sizing**: Implement proper position sizing to manage risk

## Resources

- **GitHub Repository**: [pybit on GitHub](https://github.com/bybit-exchange/pybit)
- **Official API Documentation**: [Bybit V5 API Docs](https://bybit-exchange.github.io/docs/v5/intro)
- **PyPI Package**: [pybit on PyPI](https://pypi.org/project/pybit/)
- **Community Support**: 
  - Telegram: @bybitdevs
  - Discord: Bybit API Community

## Migration from V3 to V5

If you're migrating from V3 to V5 API:

1. Update endpoint URLs to V5 format
2. Add `category` parameter to specify product type
3. Update authentication headers
4. Review response format changes
5. Test thoroughly on testnet

The V5 API provides a more unified and efficient trading experience across all Bybit products.