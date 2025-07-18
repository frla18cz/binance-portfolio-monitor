#!/usr/bin/env python3
"""
Test script to check withdrawal detection including internal transfers
Tests what fields are returned by Binance API for different withdrawal types
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from binance.client import Client
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import settings
from utils.database_manager import get_supabase_client

def test_withdrawal_api():
    """Test what withdrawal API returns"""
    print("=" * 60)
    print("Testing Binance Withdrawal Detection")
    print("=" * 60)
    
    # Get Ondra(test) account
    supabase = get_supabase_client()
    accounts = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
    
    if not accounts.data:
        print("❌ Ondra(test) account not found")
        return
        
    account = accounts.data[0]
    print(f"✅ Found account: {account['account_name']} (ID: {account['id']})")
    
    # Initialize Binance client
    client = Client(account['api_key'], account['api_secret'])
    
    # Check withdrawals from last 7 days
    start_time = datetime.now(timezone.utc) - timedelta(days=7)
    start_timestamp = int(start_time.timestamp() * 1000)
    
    print(f"\n📅 Checking withdrawals since: {start_time.isoformat()}")
    
    try:
        # Get withdrawal history
        withdrawals = client.get_withdraw_history(startTime=start_timestamp)
        
        print(f"\n📊 Found {len(withdrawals)} withdrawals")
        
        if withdrawals:
            print("\n🔍 Detailed withdrawal information:")
            for i, withdrawal in enumerate(withdrawals):
                print(f"\n--- Withdrawal {i+1} ---")
                print(f"ID: {withdrawal.get('id')}")
                print(f"Amount: {withdrawal.get('amount')} {withdrawal.get('coin', 'UNKNOWN')}")
                print(f"Apply Time: {datetime.fromtimestamp(withdrawal.get('applyTime', 0)/1000, timezone.utc).isoformat()}")
                print(f"Status: {withdrawal.get('status')} (0=Email Sent,1=Cancelled,2=Awaiting Approval,3=Rejected,4=Processing,5=Failure,6=Completed)")
                print(f"Network: {withdrawal.get('network', 'N/A')}")
                print(f"Address: {withdrawal.get('address', 'N/A')}")
                print(f"TxId: {withdrawal.get('txId', 'N/A')}")
                
                # Check for transferType field
                transfer_type = withdrawal.get('transferType')
                if transfer_type is not None:
                    print(f"⚡ Transfer Type: {transfer_type} (0=external, 1=internal)")
                else:
                    print("⚡ Transfer Type: Not present in response")
                
                # Check if it's internal transfer
                if withdrawal.get('txId') == 'Internal transfer' or withdrawal.get('txId') == 'Off-chain transfer':
                    print("🔄 This is an INTERNAL TRANSFER!")
                
                # Print all fields for debugging
                print("\nAll fields in withdrawal object:")
                for key, value in withdrawal.items():
                    print(f"  {key}: {value}")
        else:
            print("\n⚠️ No withdrawals found in the last 24 hours")
            
        # Also check deposits for comparison
        print("\n" + "=" * 60)
        print("Checking deposits for comparison...")
        
        deposits = client.get_deposit_history(startTime=start_timestamp)
        print(f"\n📊 Found {len(deposits)} deposits")
        
        if deposits:
            print("\n🔍 Sample deposit structure:")
            deposit = deposits[0]
            for key, value in deposit.items():
                print(f"  {key}: {value}")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Try to get more error details
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")

if __name__ == "__main__":
    test_withdrawal_api()