#!/usr/bin/env python3
"""
Test script for complete monitoring flow
Tests proxy, wallet access, NAV calculation, and database operations
"""

import os
import sys
import json
import requests
from datetime import datetime, UTC
from tabulate import tabulate

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import settings
from utils.database_manager import get_supabase_client
from api.index import create_binance_client, get_comprehensive_nav, get_prices
from api.logger import get_logger, LogCategory

def test_proxy_configuration():
    """Test proxy configuration and status"""
    print("\n=== PROXY CONFIGURATION TEST ===")
    
    is_vercel = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))
    proxy_url_exists = bool(os.environ.get('OXYLABS_PROXY_URL'))
    proxy_configured = hasattr(settings, 'proxy') and settings.proxy.enabled_on_vercel
    proxy_is_active = hasattr(settings, 'proxy') and settings.proxy.is_active
    
    proxy_info = [
        ["Environment", "Vercel" if is_vercel else "Local"],
        ["Proxy URL Set", "Yes" if proxy_url_exists else "No"],
        ["Proxy Configured", "Yes" if proxy_configured else "No"],
        ["Proxy Active", "Yes" if proxy_is_active else "No"],
    ]
    
    if proxy_is_active and settings.proxy.url:
        proxy_host = settings.proxy.url.split('@')[-1] if '@' in settings.proxy.url else 'proxy'
        proxy_info.append(["Proxy Host", proxy_host])
    
    print(tabulate(proxy_info, headers=["Setting", "Value"], tablefmt="grid"))
    
    return {
        "is_vercel": is_vercel,
        "proxy_active": proxy_is_active,
        "proxy_url_exists": proxy_url_exists
    }

def test_price_fetching():
    """Test price fetching via data API"""
    print("\n=== PRICE FETCHING TEST ===")
    
    try:
        # Test direct price fetch
        client = create_binance_client(for_prices_only=True)
        btc_ticker = client.get_symbol_ticker(symbol='BTCUSDT')
        eth_ticker = client.get_symbol_ticker(symbol='ETHUSDT')
        
        # Test get_prices function
        prices = get_prices(client)
        
        price_info = [
            ["BTC Price (direct)", f"${float(btc_ticker['price']):,.2f}"],
            ["ETH Price (direct)", f"${float(eth_ticker['price']):,.2f}"],
            ["BTC Price (get_prices)", f"${prices['BTCUSDT']:,.2f}"],
            ["ETH Price (get_prices)", f"${prices['ETHUSDT']:,.2f}"],
            ["API URL", client.API_URL]
        ]
        
        print(tabulate(price_info, headers=["Metric", "Value"], tablefmt="grid"))
        print("✅ Price fetching successful")
        
        return True, prices
        
    except Exception as e:
        print(f"❌ Price fetching failed: {str(e)}")
        return False, None

def test_account_access(account, prices):
    """Test access to a single account"""
    account_id = account['id']
    account_name = account['account_name']
    
    print(f"\n--- Testing account: {account_name} ---")
    
    try:
        # Create client with real credentials
        client = create_binance_client(
            api_key=account['binance_api_key'],
            api_secret=account['binance_api_secret']
        )
        
        # Test basic account access
        try:
            spot_account = client.get_account()
            permissions = spot_account.get('permissions', [])
            print(f"✅ Spot wallet access successful - Permissions: {permissions}")
        except Exception as e:
            print(f"❌ Spot wallet access failed: {str(e)}")
            if "restricted location" in str(e).lower():
                print("   ⚠️  Geographic restriction detected - proxy may not be working")
            return False, None
        
        # Get comprehensive NAV
        logger = get_logger()
        nav_result = get_comprehensive_nav(
            client,
            logger=logger,
            account_id=account_id,
            account_name=account_name,
            prices=prices
        )
        
        # Display NAV breakdown
        nav_info = [
            ["Total NAV", f"${nav_result['total_nav']:,.2f}"],
            ["Spot", f"${nav_result['breakdown']['spot_total']:,.2f}"],
            ["Futures", f"${nav_result['breakdown']['futures_total']:,.2f}"],
            ["Funding", f"${nav_result['breakdown']['funding_total']:,.2f}"],
            ["Earn", f"${nav_result['breakdown']['earn_total']:,.2f}"],
            ["Staking", f"${nav_result['breakdown']['staking_total']:,.2f}"]
        ]
        
        print(tabulate(nav_info, headers=["Component", "Value"], tablefmt="grid"))
        
        return True, nav_result
        
    except Exception as e:
        print(f"❌ Account access failed: {str(e)}")
        return False, None

def test_database_operations():
    """Test database connectivity and operations"""
    print("\n=== DATABASE TEST ===")
    
    try:
        supabase = get_supabase_client()
        
        # Test reading accounts
        accounts_result = supabase.table('binance_accounts').select('*').execute()
        accounts = accounts_result.data if accounts_result else []
        
        print(f"✅ Database connection successful")
        print(f"   Found {len(accounts)} accounts")
        
        # Test system_logs table
        logs_result = supabase.table('system_logs').select('*').limit(1).execute()
        print(f"✅ System logs table accessible")
        
        return True, accounts
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False, []

def main():
    """Run complete monitoring flow test"""
    print("BINANCE PORTFOLIO MONITOR - COMPLETE FLOW TEST")
    print("=" * 50)
    
    # Test 1: Proxy Configuration
    proxy_status = test_proxy_configuration()
    
    # Test 2: Price Fetching
    price_success, prices = test_price_fetching()
    if not price_success:
        print("\n❌ Cannot continue without price data")
        return
    
    # Test 3: Database
    db_success, accounts = test_database_operations()
    if not db_success or not accounts:
        print("\n❌ Cannot continue without database access or accounts")
        return
    
    # Test 4: Account Access
    print("\n=== ACCOUNT ACCESS TESTS ===")
    
    total_nav = 0.0
    successful_accounts = 0
    
    for account in accounts:
        success, nav_result = test_account_access(account, prices)
        if success and nav_result:
            total_nav += nav_result['total_nav']
            successful_accounts += 1
    
    # Summary
    print("\n=== TEST SUMMARY ===")
    summary_info = [
        ["Proxy Active", "Yes" if proxy_status['proxy_active'] else "No"],
        ["Price API Working", "Yes" if price_success else "No"],
        ["Database Connected", "Yes" if db_success else "No"],
        ["Accounts Tested", len(accounts)],
        ["Successful", successful_accounts],
        ["Failed", len(accounts) - successful_accounts],
        ["Total NAV", f"${total_nav:,.2f}"]
    ]
    
    print(tabulate(summary_info, headers=["Metric", "Value"], tablefmt="grid"))
    
    # Final verdict
    print("\n=== FINAL VERDICT ===")
    if successful_accounts == len(accounts) and price_success and db_success:
        print("✅ ALL TESTS PASSED - System is fully operational!")
        if proxy_status['is_vercel'] and not proxy_status['proxy_active']:
            print("⚠️  Warning: Running on Vercel but proxy is not active")
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
        if proxy_status['is_vercel'] and not proxy_status['proxy_active']:
            print("💡 Tip: Set OXYLABS_PROXY_URL environment variable on Vercel")

if __name__ == "__main__":
    main()