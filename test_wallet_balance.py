#!/usr/bin/env python3
"""
Test script for Binance wallet balance endpoint
GET /sapi/v1/asset/wallet/balance
"""

import os
import sys
from datetime import datetime, UTC
from binance.client import Client as BinanceClient
from dotenv import load_dotenv

# Add project root to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import settings
from supabase import create_client

# Load environment variables
load_dotenv()

def test_wallet_balance():
    """Test the wallet balance endpoint for a single account"""
    
    # Initialize Supabase client
    supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
    
    # Fetch first account from database
    print("Fetching account from database...")
    response = supabase.table('binance_accounts').select('*').limit(1).execute()
    
    if not response.data:
        print("No accounts found in database!")
        return
    
    account = response.data[0]
    account_name = account.get('account_name', 'Unknown')
    api_key = account.get('api_key')
    api_secret = account.get('api_secret')
    
    if not api_key or not api_secret:
        print(f"Account {account_name} is missing API credentials!")
        return
    
    print(f"\nTesting wallet balance for account: {account_name}")
    print("-" * 50)
    
    try:
        # Initialize Binance client
        client = BinanceClient(api_key, api_secret, tld=settings.api.binance.tld)
        
        # Call the wallet balance endpoint
        print("\nCalling GET /sapi/v1/asset/wallet/balance...")
        response = client._request('GET', '/sapi/v1/asset/wallet/balance', True, {})
        
        print(f"\nResponse received at: {datetime.now(UTC).isoformat()}")
        
        # Debug: Check response type and structure
        print(f"Response type: {type(response)}")
        if isinstance(response, dict):
            print(f"Response keys: {response.keys()}")
            # Check if response has 'data' key (error response)
            if 'code' in response:
                print(f"\nAPI Error Response:")
                print(f"Code: {response.get('code')}")
                print(f"Message: {response.get('msg', 'No message')}")
                return
        
        print("\nWallet Balance Response:")
        print("=" * 50)
        
        total_usdt_value = 0.0
        active_wallets = []
        
        # Handle response - it should be a list
        wallets = response if isinstance(response, list) else []
        
        if not wallets:
            print("No wallet data returned")
            return
        
        # Process and display each wallet
        for i, wallet in enumerate(wallets):
            wallet_name = wallet.get('walletName', 'Unknown')
            balance = float(wallet.get('balance', '0'))
            activated = wallet.get('activate', False)
            
            print(f"\n{i+1}. {wallet_name}:")
            print(f"   Balance: ${balance:,.2f} USDT")
            print(f"   Activated: {activated}")
            
            if balance > 0:
                total_usdt_value += balance
                if balance > settings.financial.minimum_usd_value_threshold:
                    active_wallets.append({
                        'name': wallet_name,
                        'balance': balance,
                        'activated': activated
                    })
        
        print("\n" + "=" * 50)
        print(f"Total USDT Value: ${total_usdt_value:,.2f}")
        print(f"Active Wallets (>${settings.financial.minimum_usd_value_threshold} USDT):")
        for wallet in active_wallets:
            print(f"  - {wallet['name']}: ${wallet['balance']:,.2f}")
        
        # Raw response for debugging
        print("\n\nRaw Response (first 3 wallets):")
        print("-" * 50)
        import json
        print(json.dumps(wallets[:3] if wallets else response, indent=2))
        
    except Exception as e:
        print(f"\nError calling wallet balance endpoint: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Try to print more error details
        import traceback
        traceback.print_exc()
        
        # Check if it's a permission error
        if "permits universal transfer" in str(e).lower() or "permission" in str(e).lower():
            print("\nNote: This endpoint requires API key with 'Permits Universal Transfer' permission.")
            print("Please ensure your API key has the correct permissions on Binance.")

if __name__ == "__main__":
    test_wallet_balance()