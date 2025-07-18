#!/usr/bin/env python3
"""
Test withdrawal API with all status codes
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from binance.client import Client

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.database_manager import get_supabase_client

def test_all_withdrawal_statuses():
    print("=" * 80)
    print("Testing All Withdrawal Status Codes")
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
    
    # Test each status code individually
    status_codes = {
        0: "Email Sent",
        1: "Cancelled", 
        2: "Awaiting Approval",
        3: "Rejected",
        4: "Processing",
        5: "Failure",
        6: "Completed"
    }
    
    # Use a longer time range
    start_time = datetime.now(timezone.utc) - timedelta(days=90)
    start_timestamp = int(start_time.timestamp() * 1000)
    
    print(f"\nChecking withdrawals since: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Test without status filter first
    print("\n1. Testing WITHOUT status filter (should return all):")
    try:
        all_withdrawals = client.get_withdraw_history(startTime=start_timestamp)
        print(f"   ✅ Found {len(all_withdrawals)} total withdrawals")
        
        if all_withdrawals:
            # Check status distribution
            status_count = {}
            for w in all_withdrawals:
                status = w.get('status', 'unknown')
                status_count[status] = status_count.get(status, 0) + 1
            
            print("\n   Status distribution:")
            for status, count in status_count.items():
                status_name = status_codes.get(status, f"Unknown ({status})")
                print(f"      Status {status} ({status_name}): {count} withdrawals")
                
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test each status code
    print("\n2. Testing EACH status code individually:")
    for status_code, status_name in status_codes.items():
        try:
            withdrawals = client.get_withdraw_history(startTime=start_timestamp, status=status_code)
            if withdrawals:
                print(f"   Status {status_code} ({status_name}): {len(withdrawals)} withdrawals")
                # Show recent example
                latest = max(withdrawals, key=lambda x: x.get('applyTime', 0))
                apply_time = datetime.fromtimestamp(latest['applyTime']/1000, timezone.utc)
                print(f"      Latest: {latest.get('amount')} {latest.get('coin')} on {apply_time.strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            print(f"   Status {status_code} ({status_name}): Error - {str(e)}")
    
    # Test account API permissions
    print("\n3. Testing API Key Permissions:")
    try:
        # This endpoint shows API key permissions
        api_restrictions = client.get_account_api_trading_status()
        print(f"   API Trading Status: {api_restrictions}")
    except Exception as e:
        print(f"   Could not check API status: {str(e)}")
        
    # Try account status
    try:
        account_status = client.get_account_status()
        print(f"   Account Status: {account_status}")
    except Exception as e:
        print(f"   Could not check account status: {str(e)}")
        
    # Test if we can see internal transfers through payment history
    print("\n4. Testing other transfer endpoints:")
    try:
        # Try fiat payment history
        payments = client.get_fiat_payments_history()
        print(f"   Fiat payments: {len(payments.get('data', []))} found")
    except Exception as e:
        print(f"   Fiat payments error: {str(e)}")
        
    # Check if sub-account transfer API works
    try:
        # This might show internal transfers
        sub_transfers = client.get_subaccount_transfer_history()
        print(f"   Sub-account transfers: {len(sub_transfers)} found")
    except Exception as e:
        print(f"   Sub-account transfer error: {str(e)}")

if __name__ == "__main__":
    test_all_withdrawal_statuses()