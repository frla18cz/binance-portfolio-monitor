#!/usr/bin/env python3
"""
Reset account data for fresh start
Clears all historical data for a specific account while preserving configuration
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database_manager import get_supabase_client
from api.logger import MonitorLogger, LogCategory

# Create logger instance
logger = MonitorLogger()

def get_accounts():
    """Get list of all accounts"""
    db_client = get_supabase_client()
    response = (db_client.table('binance_accounts')
        .select('id, account_name, is_sub_account, email, master_api_key')
        .order('account_name')
        .execute())
    
    return response.data if response.data else []

def reset_account_data(account_id, account_name, skip_confirmation=False):
    """
    Reset all data for a specific account
    
    Args:
        account_id: UUID of the account
        account_name: Name of the account (for display)
        skip_confirmation: Skip confirmation prompt (for programmatic use)
    """
    if not skip_confirmation:
        print(f"\n⚠️  WARNING: This will delete all data for account '{account_name}'")
        print("   This includes:")
        print("   - All transaction history")
        print("   - All NAV history")
        print("   - All benchmark data")
        print("   - Processing status")
        print("\n   The account configuration and API keys will be preserved.")
        
        confirm = input(f"\n❓ Are you sure you want to reset '{account_name}'? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Reset cancelled.")
            return False
    
    db_client = get_supabase_client()
    
    try:
        logger.info(LogCategory.SYSTEM, "account_reset_start",
                   f"Starting reset for account: {account_name}",
                   account_id=account_id)
        
        # Start transaction-like operations
        deleted_counts = {}
        
        # 1. Reset benchmark config first (to avoid foreign key issues)
        response = db_client.table('benchmark_configs')\
            .update({
                'btc_units': None,
                'eth_units': None,
                'initialized_at': None,
                'last_rebalance_timestamp': None,
                'next_rebalance_timestamp': None,
                'last_rebalance_status': None,
                'last_rebalance_error': None,
                'rebalance_count': 0,
                'last_rebalance_btc_units': None,
                'last_rebalance_eth_units': None,
                'last_modification_type': None,
                'last_modification_timestamp': None,
                'last_modification_amount': None,
                'last_modification_id': None
            })\
            .eq('account_id', account_id)\
            .execute()
        
        print("✅ Reset benchmark configuration")
        
        # 2. Delete processed transactions
        response = db_client.table('processed_transactions')\
            .select('count')\
            .eq('account_id', account_id)\
            .execute()
        
        count_before = response.data[0]['count'] if response.data else 0
        
        response = db_client.table('processed_transactions')\
            .delete()\
            .eq('account_id', account_id)\
            .execute()
        
        deleted_counts['processed_transactions'] = count_before
        print(f"✅ Deleted {count_before} processed transactions")
        
        # 3. Delete NAV history
        response = db_client.table('nav_history')\
            .select('count')\
            .eq('account_id', account_id)\
            .execute()
        
        count_before = response.data[0]['count'] if response.data else 0
        
        response = db_client.table('nav_history')\
            .delete()\
            .eq('account_id', account_id)\
            .execute()
        
        deleted_counts['nav_history'] = count_before
        print(f"✅ Deleted {count_before} NAV history records")
        
        # 4. Delete account processing status
        response = db_client.table('account_processing_status')\
            .delete()\
            .eq('account_id', account_id)\
            .execute()
        
        print("✅ Cleared account processing status")
        
        # 5. Delete benchmark modifications
        response = db_client.table('benchmark_modifications')\
            .delete()\
            .eq('account_id', account_id)\
            .execute()
        
        print("✅ Cleared benchmark modifications")
        
        # 6. Delete benchmark rebalance history
        response = db_client.table('benchmark_rebalance_history')\
            .delete()\
            .eq('account_id', account_id)\
            .execute()
        
        print("✅ Cleared benchmark rebalance history")

        # 7. Delete fee tracking
        response = db_client.table('fee_tracking')\
            .delete()\
            .eq('account_id', account_id)\
            .execute()
        
        print("✅ Cleared fee tracking")
        
        logger.info(LogCategory.SYSTEM, "account_reset_complete",
                   f"Successfully reset account: {account_name}",
                   account_id=account_id,
                   data={'deleted_counts': deleted_counts})
        
        print(f"\n✨ Account '{account_name}' has been reset successfully!")
        print("   The account is now ready for fresh monitoring.")
        return True
        
    except Exception as e:
        logger.error(LogCategory.SYSTEM, "account_reset_error",
                    f"Error resetting account {account_name}: {str(e)}",
                    account_id=account_id, error=str(e))
        print(f"\n❌ Error resetting account: {str(e)}")
        return False

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset account data for fresh start')
    parser.add_argument('--account', '-a', help='Account name to reset')
    parser.add_argument('--list', '-l', action='store_true', help='List all accounts')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    if args.list:
        accounts = get_accounts()
        if accounts:
            print("\n📊 Available accounts:")
            for acc in accounts:
                print(f"   - {acc['account_name']}")
        else:
            print("❌ No accounts found")
        return
    
    if not args.account:
        # Interactive mode
        accounts = get_accounts()
        if not accounts:
            print("❌ No accounts found in database")
            return
            
        print("\n📊 Available accounts:")
        for i, acc in enumerate(accounts, 1):
            print(f"   {i}. {acc['account_name']}")
        
        try:
            choice = input("\n❓ Select account number to reset (or 'q' to quit): ")
            if choice.lower() == 'q':
                print("👋 Goodbye!")
                return
                
            idx = int(choice) - 1
            if 0 <= idx < len(accounts):
                account = accounts[idx]
                reset_account_data(account['id'], account['account_name'], args.yes)
            else:
                print("❌ Invalid selection")
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Cancelled")
            
    else:
        # Direct account name provided
        accounts = get_accounts()
        account = next((acc for acc in accounts if acc['account_name'] == args.account), None)
        
        if account:
            reset_account_data(account['id'], account['account_name'], args.yes)
        else:
            print(f"❌ Account '{args.account}' not found")
            print("\nAvailable accounts:")
            for acc in accounts:
                print(f"   - {acc['account_name']}")

if __name__ == "__main__":
    main()