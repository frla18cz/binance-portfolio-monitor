#!/usr/bin/env python3
"""
Test CCXT library for accessing Binance transaction history with read-only permissions.
This script explores what transaction data we can access without withdrawal permissions.
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
import ccxt
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('.env')

def test_ccxt_binance():
    """Test CCXT's Binance implementation for transaction history access."""
    
    # Try to get credentials from database first (like main app)
    from utils.database_manager import get_supabase_client
    
    try:
        db_client = get_supabase_client()
        accounts_response = db_client.table('binance_accounts').select('*').execute()
        
        if accounts_response.data and len(accounts_response.data) > 0:
            # Use the first account for testing
            account = accounts_response.data[0]
            api_key = account.get('api_key')
            api_secret = account.get('api_secret')
            account_name = account.get('account_name', 'Unknown')
            print(f"🔑 Using account: {account_name}")
        else:
            # Fall back to environment variables
            api_key = os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_API_SECRET')
            account_name = "Environment Variables"
    except Exception as e:
        print(f"❌ Error fetching accounts from database: {e}")
        # Fall back to environment variables
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        account_name = "Environment Variables"
    
    if not api_key or not api_secret:
        print("❌ No API credentials found in database or environment variables")
        return
    
    # Initialize CCXT Binance exchange
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',  # or 'future', 'margin', 'delivery'
        }
    })
    
    print("🔍 Testing CCXT Binance Implementation\n")
    
    # 1. Check exchange capabilities
    print("1️⃣ Exchange Capabilities:")
    capabilities = {
        'fetchWithdrawals': exchange.has['fetchWithdrawals'],
        'fetchDeposits': exchange.has['fetchDeposits'],
        'fetchTransactions': exchange.has['fetchTransactions'],
        'fetchLedger': exchange.has['fetchLedger'],
        'fetchTransfers': exchange.has['fetchTransfers'],
        'fetchMyTrades': exchange.has['fetchMyTrades'],
        'fetchBalance': exchange.has['fetchBalance'],
    }
    for capability, supported in capabilities.items():
        print(f"   {capability}: {'✅' if supported else '❌'}")
    
    print("\n2️⃣ Testing API Permissions:")
    try:
        # Try to fetch account info to check permissions
        account_info = exchange.fetch_account()
        permissions = account_info.get('info', {}).get('permissions', [])
        print(f"   Permissions: {permissions}")
        
        # Check specific permission flags
        can_trade = account_info.get('info', {}).get('canTrade', False)
        can_withdraw = account_info.get('info', {}).get('canWithdraw', False)
        can_deposit = account_info.get('info', {}).get('canDeposit', False)
        
        print(f"   Can Trade: {'✅' if can_trade else '❌'}")
        print(f"   Can Withdraw: {'✅' if can_withdraw else '❌'}")
        print(f"   Can Deposit: {'✅' if can_deposit else '❌'}")
    except Exception as e:
        print(f"   ❌ Error fetching account info: {e}")
    
    # 3. Test fetchWithdrawals (if supported)
    print("\n3️⃣ Testing fetchWithdrawals:")
    if exchange.has['fetchWithdrawals']:
        try:
            # Fetch withdrawals from last 30 days
            since = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
            withdrawals = exchange.fetch_withdrawals(since=since, limit=10)
            print(f"   ✅ Found {len(withdrawals)} withdrawals")
            
            # Show sample withdrawal structure
            if withdrawals:
                print("   Sample withdrawal structure:")
                sample = withdrawals[0]
                for key in ['id', 'txid', 'timestamp', 'datetime', 'currency', 'amount', 'status', 'type']:
                    if key in sample:
                        print(f"      {key}: {sample[key]}")
        except ccxt.InsufficientFunds as e:
            print(f"   ❌ Insufficient funds error: {e}")
        except ccxt.PermissionDenied as e:
            print(f"   ❌ Permission denied: {e}")
        except ccxt.BaseError as e:
            print(f"   ❌ CCXT error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
    else:
        print("   ❌ fetchWithdrawals not supported")
    
    # 4. Test fetchDeposits (if supported)
    print("\n4️⃣ Testing fetchDeposits:")
    if exchange.has['fetchDeposits']:
        try:
            # Fetch deposits from last 30 days
            since = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
            deposits = exchange.fetch_deposits(since=since, limit=10)
            print(f"   ✅ Found {len(deposits)} deposits")
            
            # Show sample deposit structure
            if deposits:
                print("   Sample deposit structure:")
                sample = deposits[0]
                for key in ['id', 'txid', 'timestamp', 'datetime', 'currency', 'amount', 'status', 'type']:
                    if key in sample:
                        print(f"      {key}: {sample[key]}")
        except ccxt.PermissionDenied as e:
            print(f"   ❌ Permission denied: {e}")
        except ccxt.BaseError as e:
            print(f"   ❌ CCXT error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
    else:
        print("   ❌ fetchDeposits not supported")
    
    # 5. Test fetchLedger (if supported)
    print("\n5️⃣ Testing fetchLedger:")
    if exchange.has['fetchLedger']:
        try:
            # Fetch ledger entries from last 7 days
            since = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000)
            ledger = exchange.fetch_ledger(since=since, limit=10)
            print(f"   ✅ Found {len(ledger)} ledger entries")
            
            # Show sample ledger structure
            if ledger:
                print("   Sample ledger entry:")
                sample = ledger[0]
                for key in ['id', 'timestamp', 'datetime', 'direction', 'account', 'referenceId', 
                           'referenceAccount', 'type', 'currency', 'amount', 'before', 'after', 'status']:
                    if key in sample:
                        print(f"      {key}: {sample[key]}")
        except ccxt.PermissionDenied as e:
            print(f"   ❌ Permission denied: {e}")
        except ccxt.BaseError as e:
            print(f"   ❌ CCXT error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
    else:
        print("   ❌ fetchLedger not supported")
    
    # 6. Test fetchTransfers (internal transfers)
    print("\n6️⃣ Testing fetchTransfers (internal transfers):")
    if exchange.has['fetchTransfers']:
        try:
            # Fetch transfers from last 30 days
            since = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
            transfers = exchange.fetch_transfers(since=since, limit=10)
            print(f"   ✅ Found {len(transfers)} transfers")
            
            # Show sample transfer structure
            if transfers:
                print("   Sample transfer structure:")
                sample = transfers[0]
                for key in ['id', 'timestamp', 'datetime', 'currency', 'amount', 'fromAccount', 
                           'toAccount', 'status', 'type']:
                    if key in sample:
                        print(f"      {key}: {sample[key]}")
        except ccxt.PermissionDenied as e:
            print(f"   ❌ Permission denied: {e}")
        except ccxt.BaseError as e:
            print(f"   ❌ CCXT error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
    else:
        print("   ❌ fetchTransfers not supported")
    
    # 7. Alternative: Try to use private API endpoints directly
    print("\n7️⃣ Testing Direct API Access (Account Statement):")
    try:
        # Try to access account statement endpoint directly
        # This is similar to what python-binance does
        response = exchange.sapiGetAccountApiRestrictions()
        print(f"   API Restrictions: {json.dumps(response, indent=2)}")
    except Exception as e:
        print(f"   ❌ Error accessing API restrictions: {e}")
    
    # 8. Check if we can access funding wallet transactions
    print("\n8️⃣ Testing Funding Wallet Access:")
    try:
        # Try to fetch funding wallet info
        funding_response = exchange.sapiPostAssetGetFundingAsset()
        print(f"   ✅ Funding wallet accessible")
        if funding_response:
            print(f"   Found {len(funding_response)} funding assets")
    except Exception as e:
        print(f"   ❌ Error accessing funding wallet: {e}")
    
    print("\n📊 Summary:")
    print("CCXT provides structured methods for accessing transaction history,")
    print("but they still require the same Binance API permissions as python-binance.")
    print("Read-only API keys will likely face the same limitations.")
    

def test_alternative_endpoints():
    """Test alternative endpoints that might work with read-only permissions."""
    
    # Try to get credentials from database first
    from utils.database_manager import get_supabase_client
    
    try:
        db_client = get_supabase_client()
        accounts_response = db_client.table('binance_accounts').select('*').execute()
        
        if accounts_response.data and len(accounts_response.data) > 0:
            account = accounts_response.data[0]
            api_key = account.get('api_key')
            api_secret = account.get('api_secret')
        else:
            api_key = os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_API_SECRET')
    except:
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        return
    
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    
    print("\n\n🔧 Testing Alternative Endpoints:")
    
    # List of endpoints to test
    endpoints_to_test = [
        ('Asset Dividend Record', 'sapiGetAssetAssetDividend'),
        ('Dust Log', 'sapiGetAssetDribblet'),
        ('Asset Detail', 'sapiGetAssetAssetDetail'),
        ('Trade Fee', 'sapiGetAssetTradeFee'),
        ('Account Status', 'sapiGetAccountStatus'),
        ('Account API Trading Status', 'sapiGetAccountApiTradingStatus'),
    ]
    
    for name, method in endpoints_to_test:
        print(f"\n   Testing {name}:")
        try:
            # Get the method from exchange object
            api_method = getattr(exchange, method, None)
            if api_method:
                result = api_method()
                if result:
                    print(f"   ✅ Success - returned {len(result) if isinstance(result, list) else 'data'}")
                    # Show sample if it's a list with items
                    if isinstance(result, list) and result:
                        print(f"   Sample: {json.dumps(result[0], indent=2)}")
                    elif isinstance(result, dict):
                        # Show first few keys
                        keys = list(result.keys())[:5]
                        print(f"   Keys: {keys}")
                else:
                    print(f"   ⚠️  No data returned")
            else:
                print(f"   ❌ Method not found")
        except Exception as e:
            print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    test_ccxt_binance()
    test_alternative_endpoints()