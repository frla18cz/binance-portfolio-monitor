#!/usr/bin/env python3
"""
Test Binance Pay API endpoints - email/phone transfers might be under Pay system
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from binance.client import Client
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.database_manager import get_supabase_client

def test_binance_pay_endpoints():
    print("=" * 80)
    print("Testing Binance Pay API Endpoints")
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
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=2)
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(now.timestamp() * 1000)
    
    print(f"\nChecking from: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Checking to: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # List of potential Pay-related endpoints
    pay_endpoints = [
        # Pay transactions (might include email transfers)
        {
            'name': 'Pay Transactions',
            'endpoint': '/sapi/v1/pay/transactions',
            'params': {
                'startTime': start_timestamp,
                'endTime': end_timestamp
            }
        },
        # C2C (Customer to Customer) history
        {
            'name': 'C2C History',
            'endpoint': '/sapi/v1/c2c/orderMatch/listUserOrderHistory',
            'params': {
                'startTimestamp': start_timestamp,
                'endTimestamp': end_timestamp
            }
        },
        # Fiat payments
        {
            'name': 'Fiat Payment History',
            'endpoint': '/sapi/v1/fiat/payments',
            'params': {
                'beginTime': start_timestamp,
                'endTime': end_timestamp
            }
        },
        # Asset transfer history (internal transfers)
        {
            'name': 'Asset Transfer History',
            'endpoint': '/sapi/v1/asset/transfer',
            'params': {
                'type': 'MAIN_PAY',  # Main account to Pay account
                'startTime': start_timestamp,
                'endTime': end_timestamp
            }
        },
        # Universal transfer history
        {
            'name': 'Universal Transfer History',
            'endpoint': '/sapi/v1/asset/transfer',
            'params': {
                'startTime': start_timestamp,
                'endTime': end_timestamp
            }
        },
        # Capital flow (might show internal movements)
        {
            'name': 'Capital Flow',
            'endpoint': '/sapi/v1/capital/flow',
            'params': {
                'startTime': start_timestamp,
                'endTime': end_timestamp
            }
        },
        # Rebate history
        {
            'name': 'Rebate History',
            'endpoint': '/sapi/v1/rebate/taxQuery',
            'params': {
                'startTime': start_timestamp,
                'endTime': end_timestamp
            }
        }
    ]
    
    for endpoint_info in pay_endpoints:
        print(f"\n{'='*60}")
        print(f"Testing: {endpoint_info['name']}")
        print(f"Endpoint: {endpoint_info['endpoint']}")
        
        try:
            # Add timestamp for signing
            params = endpoint_info['params'].copy()
            params['timestamp'] = int(datetime.now().timestamp() * 1000)
            
            result = client._request('GET', endpoint_info['endpoint'], True, params)
            
            print(f"✅ Success!")
            
            # Handle different response formats
            if isinstance(result, dict):
                if 'data' in result:
                    data = result['data']
                    if isinstance(data, list):
                        print(f"Found {len(data)} records")
                        if data:
                            print("Sample record:")
                            print(json.dumps(data[0], indent=2))
                    else:
                        print(f"Data: {json.dumps(data, indent=2)}")
                else:
                    print(f"Response: {json.dumps(result, indent=2)}")
            elif isinstance(result, list):
                print(f"Found {len(result)} records")
                if result:
                    print("Sample record:")
                    print(json.dumps(result[0], indent=2))
            else:
                print(f"Response: {result}")
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error: {error_msg}")
            
            # Check if it's a specific error code
            if "APIError" in error_msg:
                # Extract error details
                if "-" in error_msg:
                    parts = error_msg.split("-", 1)
                    if len(parts) > 1:
                        print(f"   Details: {parts[1].strip()}")
    
    # Also check if the transfer might be in the deposit history (sometimes internal transfers show as deposits)
    print(f"\n{'='*60}")
    print("Checking deposit history (internal transfers sometimes appear here):")
    try:
        deposits = client.get_deposit_history(startTime=start_timestamp)
        print(f"Found {len(deposits)} deposits")
        
        if deposits:
            for d in deposits:
                deposit_time = datetime.fromtimestamp(d.get('insertTime', 0)/1000, timezone.utc)
                if deposit_time > start_time:
                    print(f"\nRecent deposit:")
                    print(f"  Amount: {d.get('amount')} {d.get('coin')}")
                    print(f"  Time: {deposit_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    print(f"  Status: {d.get('status')}")
                    print(f"  Network: {d.get('network', 'N/A')}")
                    print(f"  Address: {d.get('address', 'N/A')}")
                    print(f"  TX ID: {d.get('txId', 'N/A')}")
                    
    except Exception as e:
        print(f"Error checking deposits: {str(e)}")

if __name__ == "__main__":
    test_binance_pay_endpoints()