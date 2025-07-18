#!/usr/bin/env python3
"""
Test User Universal Transfer API - the correct endpoint for internal transfers
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from binance.client import Client

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.database_manager import get_supabase_client

def test_user_universal_transfer():
    print("=" * 80)
    print("Testing User Universal Transfer Query")
    print("=" * 80)
    
    # Get Ondra(test) account
    supabase = get_supabase_client()
    accounts = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
    
    if not accounts.data:
        print("❌ Ondra(test) account not found")
        return
        
    account = accounts.data[0]
    print(f"✅ Found account: {account['account_name']}")
    
    # Initialize Binance client
    client = Client(account['api_key'], account['api_secret'])
    
    # Time range - last 7 days
    start_time = datetime.now(timezone.utc) - timedelta(days=7)
    end_time = datetime.now(timezone.utc)
    
    print(f"\nChecking transfers from {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    
    # Test User Universal Transfer Query endpoint
    # This is the correct endpoint for querying internal transfers between accounts
    print("\n1. Testing User Universal Transfer Query (sapi/v1/asset/universalTransfer):")
    try:
        params = {
            'type': 'MAIN_PAY',  # Try different transfer types
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'current': 1,
            'size': 100
        }
        
        # Try different transfer types that might capture email transfers
        transfer_types = [
            'MAIN_PAY',           # Main account to Pay account
            'PAY_MAIN',           # Pay account to Main account  
            'MAIN_FUNDING',       # Main to Funding
            'FUNDING_MAIN',       # Funding to Main
            'MAIN_UMFUTURE',      # Main to USDⓈ-M Futures
            'UMFUTURE_MAIN',      # USDⓈ-M Futures to Main
            'MAIN_CMFUTURE',      # Main to COIN-M Futures
            'CMFUTURE_MAIN',      # COIN-M Futures to Main
            'MAIN_MARGIN',        # Main to Margin
            'MARGIN_MAIN'         # Margin to Main
        ]
        
        for transfer_type in transfer_types:
            try:
                params['type'] = transfer_type
                result = client._request('GET', 'sapi/v1/asset/universalTransfer', True, params)
                
                if result and result.get('rows'):
                    print(f"\n   ✅ Found transfers for type {transfer_type}:")
                    for row in result['rows']:
                        print(f"      {row}")
                else:
                    print(f"   No transfers found for type: {transfer_type}")
                    
            except Exception as e:
                error_msg = str(e)
                if 'You are not authorized' not in error_msg and 'data' not in error_msg:
                    print(f"   Error for type {transfer_type}: {error_msg}")
                    
    except Exception as e:
        print(f"   General error: {str(e)}")
        
    # Try the main withdrawal endpoint with different parameters
    print("\n\n2. Testing withdrawal history with offset parameter:")
    try:
        # Maybe we need to use offset parameter
        offset = 0
        limit = 1000
        all_withdrawals = []
        
        while True:
            params = {
                'offset': offset,
                'limit': limit
            }
            withdrawals = client.get_withdraw_history(**params)
            
            if not withdrawals:
                break
                
            all_withdrawals.extend(withdrawals)
            
            if len(withdrawals) < limit:
                break
                
            offset += limit
            
        print(f"   Total withdrawals found (all time): {len(all_withdrawals)}")
        
        # Check for USDT withdrawals
        usdt_withdrawals = [w for w in all_withdrawals if w.get('coin') == 'USDT']
        print(f"   USDT withdrawals: {len(usdt_withdrawals)}")
        
        if usdt_withdrawals:
            print("\n   Recent USDT withdrawals:")
            for w in usdt_withdrawals[:5]:  # Show last 5
                apply_time = datetime.fromtimestamp(w['applyTime']/1000, timezone.utc)
                print(f"      {apply_time.strftime('%Y-%m-%d %H:%M')} - {w['amount']} USDT - Status: {w['status']}")
                if 'address' in w:
                    print(f"         Address: {w['address'][:20]}...")
                if 'txId' in w:
                    print(f"         TxId: {w['txId'][:30]}...")
                    
    except Exception as e:
        print(f"   Error: {str(e)}")
        
    # Check if the API key has the right permissions
    print("\n\n3. Checking API Key permissions:")
    try:
        api_permissions = client.get_account_api_permissions()
        print(f"   Permissions: {api_permissions}")
    except Exception as e:
        # Try alternate method
        try:
            status = client.get_account_status()
            print(f"   Account status: {status}")
            
            # Try to get API key restrictions
            api_status = client.get_account_api_trading_status()
            print(f"   API trading status: {api_status}")
        except Exception as e2:
            print(f"   Could not check permissions: {str(e2)}")

if __name__ == "__main__":
    test_user_universal_transfer()