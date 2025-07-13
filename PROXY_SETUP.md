# Oxylabs Proxy Setup for Binance Monitor on Vercel

## Overview

This document describes the proxy configuration used to bypass Binance API geographic restrictions when running on Vercel's cloud infrastructure.

## Problem Statement

Binance blocks API requests from major cloud provider IP ranges (AWS, GCP, Azure, Vercel) as part of their geographic restriction policy. This affects:
- ❌ Private API endpoints (account data, NAV, balances, transactions)
- ✅ Public data endpoints can use `data-api.binance.vision` (prices work without proxy)

## Solution Architecture

We use Oxylabs proxy service to route Binance API requests through residential IPs that are not blocked:

```
Vercel Function → Oxylabs Proxy → Binance API → Response
```

## Configuration

### 1. Environment Variable

Set the following environment variable on Vercel:

```bash
OXYLABS_PROXY_URL=https://customer-USERNAME:PASSWORD@cz-pr.oxylabs.io:18001
```

**Important**: Replace `USERNAME` and `PASSWORD` with your actual Oxylabs credentials.

### 2. Automatic Activation

The proxy activates automatically when:
- Running on Vercel (detected via `VERCEL` or `VERCEL_ENV` environment variables)
- `OXYLABS_PROXY_URL` environment variable is configured
- Making authenticated API calls (not needed for price fetching)

### 3. Configuration in settings.json

```json
"proxy": {
    "enabled_on_vercel": true,
    "url_env": "OXYLABS_PROXY_URL",
    "timeout_seconds": 30,
    "verify_ssl": true,
    "description": "Proxy configuration for bypassing Binance geographic restrictions on Vercel"
}
```

## Implementation Details

### Proxy Detection Logic

The `ProxyConfig` class in `config/__init__.py` includes smart activation:

```python
@property
def is_active(self) -> bool:
    """Check if proxy should be active (Vercel environment + URL configured)."""
    is_vercel = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))
    return self.enabled_on_vercel and is_vercel and bool(self.url)
```

### Client Creation

The `create_binance_client()` function in `api/index.py` handles proxy application:

```python
def create_binance_client(api_key='', api_secret='', tld='com', for_prices_only=False):
    client = BinanceClient(api_key, api_secret, tld=tld)
    
    # Price-only clients use data API (no proxy needed)
    if for_prices_only:
        client.API_URL = 'https://data-api.binance.vision/api'
        return client
    
    # Apply proxy for authenticated endpoints on Vercel
    if hasattr(settings, 'proxy') and settings.proxy.is_active:
        # ... proxy configuration ...
```

## Usage Patterns

### 1. Price Fetching (No Proxy)
```python
# Always uses data-api.binance.vision
client = create_binance_client(for_prices_only=True)
prices = client.get_symbol_ticker(symbol='BTCUSDT')
```

### 2. Account Data (Proxy on Vercel)
```python
# Uses proxy on Vercel, direct connection locally
client = create_binance_client(api_key, api_secret)
nav = client.futures_account()
```

### 3. Dashboard (No Proxy)
The dashboard (`api/dashboard.py`) only reads from Supabase database and never calls Binance API directly, so no proxy is needed.

## Vercel Deployment

1. **Add Environment Variable**:
   ```bash
   vercel env add OXYLABS_PROXY_URL
   # Enter the full proxy URL when prompted
   ```

2. **Deploy**:
   ```bash
   vercel --prod
   ```

3. **Verify**:
   - Check system logs for "proxy_enabled" entries
   - Monitor successful API calls in Supabase logs

## Testing

### Local Testing (No Proxy)
```bash
# Run locally - proxy will NOT activate
python -m api.index
```

### Vercel Testing (With Proxy)
```bash
# Set test environment variable
export VERCEL=1
export OXYLABS_PROXY_URL=https://customer-USERNAME:PASSWORD@cz-pr.oxylabs.io:18001

# Run with simulated Vercel environment
python -m api.index
```

## Troubleshooting

### 1. Proxy Not Activating
- Check if `VERCEL` or `VERCEL_ENV` environment variables are set
- Verify `OXYLABS_PROXY_URL` is properly configured
- Look for "proxy_enabled" in system logs

### 2. Authentication Errors
- Verify Oxylabs credentials are correct
- Check proxy URL format: `https://customer-USERNAME:PASSWORD@HOST:PORT`
- Ensure no special characters in password need URL encoding

### 3. Connection Timeouts
- Default timeout is 30 seconds (configurable in settings.json)
- Oxylabs proxy may add 2-3 seconds latency
- Consider increasing timeout for large data requests

### 4. SSL Verification
- Set `verify_ssl: false` in settings.json if SSL issues occur
- Not recommended for production without investigating root cause

## Security Considerations

1. **Never commit proxy credentials** to version control
2. **Use environment variables** for all sensitive data
3. **Monitor proxy usage** to prevent unauthorized access
4. **Rotate credentials** periodically
5. **Restrict proxy access** to specific Vercel projects

## Cost Optimization

- Proxy is only used for authenticated endpoints
- Price fetching uses free data-api.binance.vision
- Dashboard doesn't use proxy (database only)
- Hourly cron minimizes proxy usage

## Alternative Solutions

If Oxylabs proxy becomes unavailable:

1. **Other Proxy Services**: Bright Data, SmartProxy, IPRoyal
2. **VPS Solution**: Deploy on non-cloud VPS with residential IP
3. **API Gateway**: Use AWS API Gateway in allowed regions
4. **Binance Cloud**: Use Binance's own cloud services

## References

- [Oxylabs Documentation](https://developers.oxylabs.io/)
- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Vercel Environment Variables](https://vercel.com/docs/environment-variables)