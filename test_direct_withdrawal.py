#!/usr/bin/env python3
"""
Direct test of Binance withdrawal API for Ondra(test) account
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from binance.client import Client

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config import settings
from utils.database_manager import get_supabase_client

def test_withdrawal_api_direct():
    print("=" * 80)
    print("Direct Binance Withdrawal API Test")
    print("=" * 80)
    
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
    
    # Test multiple time ranges
    time_ranges = [
        ("Last 1 hour", 1),
        ("Last 24 hours", 24),
        ("Last 7 days", 168),
        ("Last 30 days", 720)
    ]
    
    for label, hours in time_ranges:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        start_timestamp = int(start_time.timestamp() * 1000)
        
        print(f"\n{'='*60}")
        print(f"📅 {label} (since {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')})")
        print(f"{'='*60}")
        
        try:
            # Get withdrawal history with no status filter to see all
            withdrawals = client.get_withdraw_history(startTime=start_timestamp)
            
            print(f"\n📊 Found {len(withdrawals)} withdrawals")
            
            if withdrawals:
                print("\n🔍 Withdrawal details:")
                for i, w in enumerate(withdrawals):
                    print(f"\n--- Withdrawal {i+1} ---")
                    # Print all fields
                    for key, value in w.items():
                        print(f"  {key}: {value}")
                        
                    # Highlight important fields
                    if w.get('coin') == 'USDT' and abs(float(w.get('amount', 0)) - 10) < 0.1:
                        print("\n⚠️  THIS COULD BE YOUR $10 USDT WITHDRAWAL!")
                        
            # Also test with status filter (completed only)
            print("\n📋 Testing with status=6 filter (completed):")
            completed_withdrawals = client.get_withdraw_history(startTime=start_timestamp, status=6)
            print(f"   Found {len(completed_withdrawals)} completed withdrawals")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            
    # Also test universal transfer history
    print(f"\n{'='*80}")
    print("Testing Universal Transfer History (internal transfers)")
    print(f"{'='*80}")
    
    try:
        # Try to get universal transfer history
        transfers = client.universal_transfer_history()
        print(f"Found {len(transfers.get('rows', []))} transfers")
        if transfers.get('rows'):
            for t in transfers['rows']:
                print(f"  {t}")
    except Exception as e:
        print(f"Universal transfer API error: {str(e)}")
        print("(This is normal if account doesn't have universal transfer permission)")

if __name__ == "__main__":
    test_withdrawal_api_direct()