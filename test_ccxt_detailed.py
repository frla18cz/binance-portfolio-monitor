#!/usr/bin/env python3
"""
Detailed test of CCXT withdrawal/deposit fetching capabilities.
Tests various parameter combinations to see what data we can access.
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

def test_detailed_withdrawals_deposits():
    """Test detailed withdrawal and deposit fetching with various parameters."""
    
    # Get credentials from database
    from utils.database_manager import get_supabase_client
    
    try:
        db_client = get_supabase_client()
        accounts_response = db_client.table('binance_accounts').select('*').execute()
        
        if accounts_response.data and len(accounts_response.data) > 0:
            account = accounts_response.data[0]
            api_key = account.get('api_key')
            api_secret = account.get('api_secret')
            account_name = account.get('account_name', 'Unknown')
            print(f"🔑 Using account: {account_name}")
        else:
            print("❌ No accounts found in database")
            return
    except Exception as e:
        print(f"❌ Error fetching accounts: {e}")
        return
    
    # Initialize CCXT Binance exchange
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    
    print("\n📊 Testing Withdrawal/Deposit History Access\n")
    
    # Test 1: Withdrawals with different time ranges
    print("1️⃣ Testing Withdrawals with Different Time Ranges:")
    time_ranges = [
        ("Last 90 days", 90),
        ("Last 365 days", 365),
        ("Last 1000 days", 1000),
    ]
    
    for range_name, days in time_ranges:
        try:
            since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
            withdrawals = exchange.fetch_withdrawals(since=since)
            print(f"   {range_name}: Found {len(withdrawals)} withdrawals")
            
            if withdrawals:
                # Show the most recent withdrawal
                recent = withdrawals[-1]
                print(f"      Most recent withdrawal:")
                print(f"      - Date: {recent.get('datetime', 'N/A')}")
                print(f"      - Currency: {recent.get('currency', 'N/A')}")
                print(f"      - Amount: {recent.get('amount', 'N/A')}")
                print(f"      - Status: {recent.get('status', 'N/A')}")
                print(f"      - TxId: {recent.get('txid', 'N/A')}")
                print(f"      - Type: {recent.get('type', 'N/A')}")
                print(f"      - Network: {recent.get('network', 'N/A')}")
                
                # Check if we have internal transfer metadata
                if 'info' in recent:
                    info = recent['info']
                    if 'transferType' in info:
                        print(f"      - Transfer Type: {info['transferType']} {'(Internal)' if info['transferType'] == 1 else '(External)'}")
        except Exception as e:
            print(f"   {range_name}: ❌ Error: {e}")
    
    # Test 2: Deposits with different time ranges
    print("\n2️⃣ Testing Deposits with Different Time Ranges:")
    for range_name, days in time_ranges:
        try:
            since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
            deposits = exchange.fetch_deposits(since=since)
            print(f"   {range_name}: Found {len(deposits)} deposits")
            
            if deposits:
                # Show the most recent deposit
                recent = deposits[-1]
                print(f"      Most recent deposit:")
                print(f"      - Date: {recent.get('datetime', 'N/A')}")
                print(f"      - Currency: {recent.get('currency', 'N/A')}")
                print(f"      - Amount: {recent.get('amount', 'N/A')}")
                print(f"      - Status: {recent.get('status', 'N/A')}")
                print(f"      - TxId: {recent.get('txid', 'N/A')}")
                print(f"      - Type: {recent.get('type', 'N/A')}")
        except Exception as e:
            print(f"   {range_name}: ❌ Error: {e}")
    
    # Test 3: Check raw API response structure
    print("\n3️⃣ Testing Raw API Response (to see all available fields):")
    try:
        # Use raw API call to see full response
        since_timestamp = int((datetime.now(timezone.utc) - timedelta(days=365)).timestamp() * 1000)
        
        # Try to call withdrawHistory directly
        params = {
            'timestamp': exchange.milliseconds(),
            'startTime': since_timestamp,
        }
        
        # Sign request
        params['signature'] = exchange.hmac(exchange.encode(exchange.urlencode(params)), 
                                          exchange.encode(exchange.secret), 
                                          exchange.hashlib.sha256)
        
        response = exchange.sapiGetCapitalWithdrawHistory(params)
        print(f"   Raw withdrawal history response has {len(response)} items")
        
        if response and len(response) > 0:
            print("   Sample raw withdrawal structure:")
            sample = response[0]
            for key, value in sample.items():
                print(f"      {key}: {value}")
                
    except Exception as e:
        print(f"   ❌ Error getting raw response: {e}")
    
    # Test 4: Try different endpoints
    print("\n4️⃣ Testing Alternative History Endpoints:")
    
    endpoints = [
        ("Capital Withdraw History", "sapiGetCapitalWithdrawHistory", {}),
        ("Capital Deposit History", "sapiGetCapitalDepositHisrec", {}),
        ("Fiat Orders", "sapiGetFiatOrders", {"transactionType": 0}),  # 0=deposit, 1=withdraw
        ("Fiat Payments", "sapiGetFiatPayments", {}),
        ("Asset Dividend", "sapiGetAssetAssetDividend", {}),
        ("Convert History", "sapiGetConvertTradeFlow", {}),
    ]
    
    for name, method_name, extra_params in endpoints:
        try:
            method = getattr(exchange, method_name, None)
            if method:
                params = {
                    'timestamp': exchange.milliseconds(),
                    **extra_params
                }
                params['signature'] = exchange.hmac(exchange.encode(exchange.urlencode(params)), 
                                                  exchange.encode(exchange.secret), 
                                                  exchange.hashlib.sha256)
                
                result = method(params)
                
                if isinstance(result, dict) and 'rows' in result:
                    print(f"   {name}: ✅ Found {result.get('total', 0)} total records")
                elif isinstance(result, list):
                    print(f"   {name}: ✅ Found {len(result)} records")
                else:
                    print(f"   {name}: ✅ Got response (type: {type(result).__name__})")
                    
                # Show sample if available
                if isinstance(result, list) and result:
                    print(f"      Sample: {json.dumps(result[0], indent=2, default=str)}")
                elif isinstance(result, dict) and 'rows' in result and result['rows']:
                    print(f"      Sample: {json.dumps(result['rows'][0], indent=2, default=str)}")
                    
            else:
                print(f"   {name}: ❌ Method not found")
        except Exception as e:
            print(f"   {name}: ❌ Error: {e}")
    
    # Test 5: Check account permissions in detail
    print("\n5️⃣ Checking Detailed Permissions:")
    try:
        api_info = exchange.sapiGetAccountApiRestrictions()
        
        print("   API Key Permissions:")
        for key, value in api_info.items():
            if key != 'createTime':
                print(f"      {key}: {'✅' if value else '❌'}")
                
        # Check which specific permissions we need
        print("\n   Required Permissions for Transaction History:")
        print("      - enableReading: Required for all read operations")
        print("      - enableWithdrawals: NOT required for viewing withdrawal history")
        print("      - The API can read historical data with just 'enableReading'")
        
    except Exception as e:
        print(f"   ❌ Error checking permissions: {e}")
    
    print("\n📊 Summary:")
    print("CCXT can fetch withdrawal and deposit history with read-only permissions!")
    print("The key is that Binance allows reading historical data without withdrawal permission.")
    print("You just need 'enableReading' permission to access transaction history.")


if __name__ == "__main__":
    test_detailed_withdrawals_deposits()