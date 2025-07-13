#!/usr/bin/env python3
"""
Test script for proxy configuration and activation logic
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from api.index import create_binance_client
from api.logger import get_logger, LogCategory

def test_proxy_config():
    """Test proxy configuration loading"""
    print("\n=== Testing Proxy Configuration ===")
    
    if hasattr(settings, 'proxy'):
        print(f"✅ Proxy config loaded")
        print(f"  - enabled_on_vercel: {settings.proxy.enabled_on_vercel}")
        print(f"  - url_env: {settings.proxy.url_env}")
        print(f"  - timeout_seconds: {settings.proxy.timeout_seconds}")
        print(f"  - verify_ssl: {settings.proxy.verify_ssl}")
        
        # Check proxy URL
        proxy_url = settings.proxy.url
        if proxy_url:
            # Hide credentials in output
            if '@' in proxy_url:
                parts = proxy_url.split('@')
                safe_url = parts[0].split('//')[0] + '//*****:*****@' + parts[1]
            else:
                safe_url = proxy_url
            print(f"  - proxy URL: {safe_url}")
        else:
            print(f"  - proxy URL: Not set (env var {settings.proxy.url_env} missing)")
        
        # Check activation
        print(f"\n  - is_active: {settings.proxy.is_active}")
        print(f"  - VERCEL env: {os.getenv('VERCEL', 'Not set')}")
        print(f"  - VERCEL_ENV env: {os.getenv('VERCEL_ENV', 'Not set')}")
    else:
        print("❌ Proxy config not found in settings")

def test_client_creation():
    """Test Binance client creation with different scenarios"""
    print("\n\n=== Testing Client Creation ===")
    
    # Test 1: Price-only client (should use data API)
    print("\n1. Price-only client:")
    client = create_binance_client(for_prices_only=True)
    print(f"  - API URL: {client.API_URL}")
    print(f"  - Expected: https://data-api.binance.vision/api")
    print(f"  - ✅ Correct" if client.API_URL == 'https://data-api.binance.vision/api' else "  - ❌ Incorrect")
    
    # Test 2: Regular client without Vercel env
    print("\n2. Regular client (no Vercel env):")
    client = create_binance_client('test_key', 'test_secret')
    print(f"  - API URL: {client.API_URL}")
    print(f"  - Has session: {hasattr(client, 'session') and client.session is not None}")
    print(f"  - Expected: No proxy session")
    
    # Test 3: Regular client with simulated Vercel env
    print("\n3. Regular client (simulated Vercel):")
    original_vercel = os.getenv('VERCEL')
    try:
        os.environ['VERCEL'] = '1'
        # Reload settings to pick up env change
        from config import get_settings
        test_settings = get_settings(force_reload=True)
        
        if hasattr(test_settings, 'proxy'):
            print(f"  - Proxy is_active: {test_settings.proxy.is_active}")
        
        # Note: Can't fully test without actual proxy URL in env
        print("  - (Full test requires OXYLABS_PROXY_URL env var)")
    finally:
        if original_vercel:
            os.environ['VERCEL'] = original_vercel
        else:
            os.environ.pop('VERCEL', None)

def test_price_fetch():
    """Test fetching prices using data API"""
    print("\n\n=== Testing Price Fetch ===")
    
    try:
        client = create_binance_client(for_prices_only=True)
        
        # Test BTC price
        btc_ticker = client.get_symbol_ticker(symbol='BTCUSDT')
        btc_price = float(btc_ticker['price'])
        print(f"✅ BTC price fetched: ${btc_price:,.2f}")
        
        # Test ETH price
        eth_ticker = client.get_symbol_ticker(symbol='ETHUSDT')
        eth_price = float(eth_ticker['price'])
        print(f"✅ ETH price fetched: ${eth_price:,.2f}")
        
        print("\nData API working correctly!")
        
    except Exception as e:
        print(f"❌ Error fetching prices: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("Binance Monitor - Proxy Configuration Test")
    print("=" * 50)
    
    test_proxy_config()
    test_client_creation()
    test_price_fetch()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("=" * 50)