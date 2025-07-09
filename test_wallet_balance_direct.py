#!/usr/bin/env python3
"""
Direct test of Binance wallet balance endpoint using requests library
GET /sapi/v1/asset/wallet/balance
"""

import os
import sys
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from datetime import datetime, UTC
from dotenv import load_dotenv

# Add project root to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import settings
from supabase import create_client

# Load environment variables
load_dotenv()

def create_signature(query_string, secret):
    """Create HMAC SHA256 signature for Binance API"""
    return hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_wallet_balance_direct():
    """Test the wallet balance endpoint using direct requests"""
    
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
    
    # Prepare request
    base_url = f"https://api.binance.{settings.api.binance.tld}"
    endpoint = "/sapi/v1/asset/wallet/balance"
    
    # Create timestamp
    timestamp = int(time.time() * 1000)
    
    # Create query parameters
    params = {
        'timestamp': timestamp
    }
    
    # Create signature
    query_string = urlencode(params)
    signature = create_signature(query_string, api_secret)
    params['signature'] = signature
    
    # Prepare headers
    headers = {
        'X-MBX-APIKEY': api_key
    }
    
    try:
        # Make the request
        print(f"\nCalling GET {base_url}{endpoint}...")
        print(f"Timestamp: {timestamp}")
        
        response = requests.get(
            f"{base_url}{endpoint}",
            params=params,
            headers=headers,
            timeout=settings.api.binance.timeout_seconds
        )
        
        print(f"\nHTTP Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error Response: {response.text}")
            return
        
        # Parse response
        data = response.json()
        
        print(f"\nResponse received at: {datetime.now(UTC).isoformat()}")
        print(f"Response type: {type(data)}")
        
        # Check if it's an error response
        if isinstance(data, dict) and 'code' in data:
            print(f"\nAPI Error:")
            print(f"Code: {data.get('code')}")
            print(f"Message: {data.get('msg', 'No message')}")
            return
        
        # Process wallet data
        wallets = data if isinstance(data, list) else []
        
        print("\nWallet Balance Response:")
        print("=" * 50)
        
        total_usdt_value = 0.0
        active_wallets = []
        
        # Process each wallet
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
        print(json.dumps(wallets[:3] if wallets else data, indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"\nRequest error: {e}")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_wallet_balance_direct()