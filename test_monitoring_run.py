#!/usr/bin/env python3
"""
Test running the monitoring system to see if it detects the withdrawal
"""

import os
import sys
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from api.index import monitor_account
from utils.database_manager import get_supabase_client
from api.logger import setup_logger

def test_monitoring_run():
    print("=" * 80)
    print("Testing Monitoring System - Will it detect the withdrawal?")
    print("=" * 80)
    
    # Setup
    logger = setup_logger()
    supabase = get_supabase_client()
    
    # Get Ondra(test) account
    accounts = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
    
    if not accounts.data:
        print("❌ Ondra(test) account not found")
        return
        
    account = accounts.data[0]
    print(f"✅ Found account: {account['account_name']} (ID: {account['id']})")
    
    # Check last processed time
    try:
        response = supabase.table('account_processing_status').select('*').eq('account_id', account['id']).execute()
        if response.data:
            last_processed = response.data[0]['last_processed_timestamp']
            print(f"\nLast processed: {last_processed}")
        else:
            print("\nNo processing status found - first run")
    except Exception as e:
        print(f"Error checking processing status: {e}")
    
    # Check if there are any existing withdrawals in database
    try:
        existing = supabase.table('processed_transactions').select('*').eq('account_id', account['id']).eq('transaction_type', 'WITHDRAWAL').execute()
        print(f"\nExisting withdrawals in database: {len(existing.data)}")
    except Exception as e:
        print(f"Error checking existing withdrawals: {e}")
    
    # Run monitoring for this account
    print(f"\n{'='*60}")
    print("Running monitor_account()...")
    print(f"{'='*60}\n")
    
    try:
        result = monitor_account(account, logger)
        print(f"\n✅ Monitoring completed successfully")
        print(f"Result: {result}")
    except Exception as e:
        print(f"\n❌ Monitoring failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Check if any new withdrawals were detected
    print(f"\n{'='*60}")
    print("Checking for new withdrawals after monitoring...")
    
    try:
        # Check processed_transactions
        new_withdrawals = supabase.table('processed_transactions').select('*').eq('account_id', account['id']).eq('transaction_type', 'WITHDRAWAL').order('created_at', desc=True).limit(5).execute()
        
        if new_withdrawals.data:
            print(f"\n✅ Found {len(new_withdrawals.data)} withdrawals in database!")
            for w in new_withdrawals.data:
                print(f"\nWithdrawal:")
                print(f"  ID: {w['transaction_id']}")
                print(f"  Amount: {w['amount']}")
                print(f"  Timestamp: {w['timestamp']}")
                print(f"  Status: {w['status']}")
                print(f"  Created: {w['created_at']}")
                if w.get('metadata'):
                    print(f"  Metadata: {w['metadata']}")
        else:
            print("\n❌ No withdrawals found in database after monitoring")
            
        # Check recent system logs for withdrawal detection
        print("\nChecking system logs for withdrawal-related messages...")
        logs = supabase.table('system_logs').select('*').eq('account_id', account['id']).order('timestamp', desc=True).limit(20).execute()
        
        withdrawal_logs = []
        for log in logs.data:
            if 'withdrawal' in log.get('message', '').lower() or 'withdraw' in log.get('operation', '').lower():
                withdrawal_logs.append(log)
                
        if withdrawal_logs:
            print(f"\nFound {len(withdrawal_logs)} withdrawal-related log entries:")
            for log in withdrawal_logs[:5]:
                print(f"\n  {log['timestamp']}: {log['operation']}")
                print(f"  Message: {log['message']}")
        
    except Exception as e:
        print(f"Error checking results: {e}")

if __name__ == "__main__":
    test_monitoring_run()