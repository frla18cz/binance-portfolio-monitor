#!/usr/bin/env python3
"""
Test different Binance API endpoints for internal transfers
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from binance.client import Client
import requests

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.database_manager import get_supabase_client

def test_internal_transfer_endpoints():
    print("=" * 80)
    print("Testing Binance Internal Transfer Endpoints")
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
    
    # Time range
    start_time = datetime.now(timezone.utc) - timedelta(days=7)
    start_timestamp = int(start_time.timestamp() * 1000)
    
    print(f"\nChecking transfers since: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # 1. Try internal transfer history endpoint
    print("\n1. Testing internal transfer history (undocumented):")
    try:
        # Try direct API call for internal transfers
        params = {
            'startTime': start_timestamp,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        # Sign and send request manually
        query_string = client._encode_params(params)
        params['signature'] = client._generate_signature(query_string)
        
        url = f"{client.API_URL}/sapi/v1/capital/transfer/internal"
        headers = {'X-MBX-APIKEY': client.API_KEY}
        
        response = requests.get(url, params=params, headers=headers)
        print(f"   Response status: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # 2. Try account transfer endpoint
    print("\n2. Testing account transfer query:")
    try:
        # Query account transfers
        endpoint = '/sapi/v1/asset/transfer'
        params = {
            'startTime': start_timestamp,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        result = client._request('GET', endpoint, True, params)
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {str(e)}")
        
    # 3. Try sub-account transfer with email
    print("\n3. Testing sub-account query transfer history:")
    try:
        # This endpoint might show transfers to other accounts
        endpoint = '/sapi/v1/sub-account/transfer/subUserHistory'
        params = {
            'startTime': start_timestamp,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        result = client._request('GET', endpoint, True, params)
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {str(e)}")
        
    # 4. Check account snapshot for withdrawals
    print("\n4. Testing account snapshot (shows daily balances):")
    try:
        snapshot = client.get_account_snapshot(type='SPOT', startTime=start_timestamp)
        if snapshot.get('snapshotVos'):
            print(f"   Found {len(snapshot['snapshotVos'])} snapshots")
            # Check latest snapshot
            if snapshot['snapshotVos']:
                latest = snapshot['snapshotVos'][-1]
                print(f"   Latest snapshot date: {datetime.fromtimestamp(latest['updateTime']/1000).strftime('%Y-%m-%d')}")
        else:
            print(f"   Result: {snapshot}")
    except Exception as e:
        print(f"   Error: {str(e)}")
        
    # 5. Try payment history
    print("\n5. Testing payment history:")
    try:
        # This might include P2P or internal transfers
        endpoint = '/sapi/v1/pay/transactions'
        params = {
            'startTime': start_timestamp,
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        result = client._request('GET', endpoint, True, params)
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {str(e)}")
        
    # 6. Check if withdrawal might be under "convert" history
    print("\n6. Testing convert history (sometimes internal transfers show here):")
    try:
        endpoint = '/sapi/v1/convert/tradeFlow'
        params = {
            'startTime': start_timestamp,
            'endTime': int(datetime.now().timestamp() * 1000),
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        result = client._request('GET', endpoint, True, params)
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {str(e)}")

if __name__ == "__main__":
    test_internal_transfer_endpoints()