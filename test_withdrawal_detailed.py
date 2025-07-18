#!/usr/bin/env python3
"""
Detailed test of withdrawal API to understand why internal transfers aren't detected
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

def test_withdrawal_api_detailed():
    print("=" * 80)
    print("Detailed Withdrawal API Test")
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
    
    # Current time
    now = datetime.now(timezone.utc)
    print(f"\nCurrent time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Withdrawal made approximately: {(now - timedelta(minutes=60)).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Test different time ranges
    time_ranges = [
        ("Last 2 hours", timedelta(hours=2)),
        ("Last 24 hours", timedelta(hours=24)),
        ("Last 7 days", timedelta(days=7)),
    ]
    
    for range_name, delta in time_ranges:
        print(f"\n{'='*60}")
        print(f"Testing: {range_name}")
        print(f"{'='*60}")
        
        start_time = now - delta
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(now.timestamp() * 1000)
        
        print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"End: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        # 1. Test get_withdraw_history with various parameters
        print("\n1. Testing get_withdraw_history():")
        try:
            # Try with just startTime
            withdrawals = client.get_withdraw_history(startTime=start_timestamp)
            print(f"   ✅ API call succeeded")
            print(f"   Found {len(withdrawals)} withdrawals")
            
            if withdrawals:
                for i, w in enumerate(withdrawals):
                    print(f"\n   Withdrawal {i+1}:")
                    print(f"   - ID: {w.get('id')}")
                    print(f"   - Amount: {w.get('amount')} {w.get('coin')}")
                    print(f"   - Status: {w.get('status')} (0=pending, 1=success, etc)")
                    print(f"   - Apply Time: {datetime.fromtimestamp(w.get('applyTime', 0)/1000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    print(f"   - Transfer Type: {w.get('transferType')} (0=external, 1=internal)")
                    print(f"   - Network: {w.get('network', 'N/A')}")
                    print(f"   - Address: {w.get('address', 'N/A')}")
                    print(f"   - TX ID: {w.get('txId', 'N/A')}")
                    print(f"   - Full data: {json.dumps(w, indent=2)}")
            else:
                print("   No withdrawals found in this time range")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            
        # 2. Try with both startTime and endTime
        print("\n2. Testing get_withdraw_history() with endTime:")
        try:
            withdrawals = client.get_withdraw_history(startTime=start_timestamp, endTime=end_timestamp)
            print(f"   ✅ API call succeeded with endTime parameter")
            print(f"   Found {len(withdrawals)} withdrawals")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            
        # 3. Try without any parameters (should get recent withdrawals)
        if range_name == "Last 2 hours":
            print("\n3. Testing get_withdraw_history() without parameters:")
            try:
                withdrawals = client.get_withdraw_history()
                print(f"   ✅ API call succeeded without parameters")
                print(f"   Found {len(withdrawals)} withdrawals (default time range)")
                
                # Check if any are from today
                today_count = 0
                for w in withdrawals:
                    apply_time = datetime.fromtimestamp(w.get('applyTime', 0)/1000, timezone.utc)
                    if apply_time.date() == now.date():
                        today_count += 1
                        
                print(f"   Withdrawals from today: {today_count}")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                
    # 4. Check account status
    print("\n" + "="*80)
    print("Checking Account Permissions:")
    print("="*80)
    
    try:
        # Get account status
        account_status = client.get_account_status()
        print(f"Account status: {json.dumps(account_status, indent=2)}")
    except Exception as e:
        print(f"Error getting account status: {str(e)}")
        
    # 5. Try API trading status
    try:
        api_status = client.get_account_api_trading_status()
        print(f"\nAPI trading status: {json.dumps(api_status, indent=2)}")
    except Exception as e:
        print(f"Error getting API status: {str(e)}")
        
    print("\n" + "="*80)
    print("SUMMARY:")
    print("- Check if withdrawal shows up in any time range")
    print("- Check transferType field (1 = internal)")
    print("- Internal transfers might show 'Internal transfer' as txId")
    print("- If no withdrawals found, the issue might be:")
    print("  1. API permissions (though read-only should work)")
    print("  2. Internal transfers via email might use different endpoint")
    print("  3. Transfer might still be processing")
    print("="*80)

if __name__ == "__main__":
    test_withdrawal_api_detailed()