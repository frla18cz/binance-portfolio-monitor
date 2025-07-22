#!/usr/bin/env python3
"""
Debug tool for viewing transaction details and metadata
Helps troubleshoot transaction detection and processing
"""

import os
import sys
from datetime import datetime, timezone
import json
from tabulate import tabulate

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.database_manager import get_supabase_client

def format_timestamp(ts_str):
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return ts_str

def debug_transactions(account_name=None, limit=20, show_metadata=True):
    """Debug transaction data from database"""
    print("🔍 Transaction Debug Tool")
    print("=" * 100)
    
    try:
        supabase = get_supabase_client()
        
        # Build query
        query = supabase.table('processed_transactions').select('*, binance_accounts!inner(account_name)')
        
        if account_name:
            query = query.eq('binance_accounts.account_name', account_name)
            print(f"Filtering for account: {account_name}")
        
        # Get transactions
        transactions = query.order('timestamp', desc=True).limit(limit).execute()
        
        if not transactions.data:
            print("\n❌ No transactions found")
            return
            
        print(f"\n📊 Found {len(transactions.data)} transactions (showing latest {limit})\n")
        
        # Group by account
        by_account = {}
        for txn in transactions.data:
            acc_name = txn['binance_accounts']['account_name']
            if acc_name not in by_account:
                by_account[acc_name] = []
            by_account[acc_name].append(txn)
        
        # Display transactions by account
        for acc_name, txns in by_account.items():
            print(f"\n{'='*80}")
            print(f"Account: {acc_name}")
            print(f"{'='*80}")
            
            # Prepare table data
            table_data = []
            internal_count = 0
            
            for txn in txns:
                # Basic info
                row = [
                    txn['transaction_id'][:20] + '...' if len(txn['transaction_id']) > 20 else txn['transaction_id'],
                    txn['transaction_type'],
                    f"{float(txn['amount']):.4f}",
                    format_timestamp(txn['timestamp']),
                    txn['status']
                ]
                
                # Check if internal
                is_internal = False
                if txn.get('metadata'):
                    metadata = txn['metadata']
                    if metadata.get('transfer_type') == 1 or 'Internal' in str(metadata.get('tx_id', '')):
                        is_internal = True
                        internal_count += 1
                
                row.append('🔄 Internal' if is_internal else '🌐 External')
                table_data.append(row)
            
            # Display table
            headers = ['Transaction ID', 'Type', 'Amount', 'Timestamp', 'Status', 'Transfer Type']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            
            print(f"\nSummary: {internal_count} internal transfers out of {len(txns)} total")
            
            # Show detailed metadata if requested
            if show_metadata:
                print(f"\n📦 Metadata Details:")
                metadata_found = False
                
                for txn in txns:
                    if txn.get('metadata'):
                        metadata_found = True
                        print(f"\n  Transaction: {txn['transaction_id'][:30]}...")
                        metadata = txn['metadata']
                        print(f"    - Transfer Type: {metadata.get('transfer_type')} {'(Internal)' if metadata.get('transfer_type') == 1 else '(External)'}")
                        print(f"    - TX ID: {metadata.get('tx_id', 'N/A')}")
                        print(f"    - Coin: {metadata.get('coin', 'N/A')}")
                        print(f"    - Network: {metadata.get('network', 'N/A')}")
                        
                if not metadata_found:
                    print("    No transactions with metadata found")
        
        # Check for internal transfer logs
        print(f"\n{'='*80}")
        print("📜 Internal Transfer Detection Logs")
        print(f"{'='*80}")
        
        logs = supabase.table('system_logs')\
            .select('*')\
            .eq('operation', 'internal_transfer_detected')\
            .order('timestamp', desc=True)\
            .limit(10)\
            .execute()
            
        if logs.data:
            print(f"\nFound {len(logs.data)} internal transfer detection logs:\n")
            
            log_table = []
            for log in logs.data:
                log_table.append([
                    format_timestamp(log['timestamp']),
                    log['account_id'][:8] + '...',
                    log['message'][:50] + '...' if len(log['message']) > 50 else log['message']
                ])
                
            print(tabulate(log_table, headers=['Timestamp', 'Account', 'Message'], tablefmt='grid'))
        else:
            print("\nNo internal transfer detection logs found")
            
        # Statistics
        print(f"\n{'='*80}")
        print("📊 Overall Statistics")
        print(f"{'='*80}")
        
        # Count transactions by type
        stats = supabase.table('processed_transactions')\
            .select('transaction_type', count='exact')\
            .execute()
            
        if stats.count:
            print(f"\nTotal transactions in database: {stats.count}")
            
        # Count transactions with metadata
        with_metadata = supabase.table('processed_transactions')\
            .select('*', count='exact')\
            .not_.is_('metadata', 'null')\
            .execute()
            
        if with_metadata.count:
            print(f"Transactions with metadata: {with_metadata.count}")
            
            # Count internal transfers
            internal_transfers = 0
            for txn in with_metadata.data:
                if txn['metadata'].get('transfer_type') == 1:
                    internal_transfers += 1
                    
            print(f"Internal transfers detected: {internal_transfers}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug transaction data')
    parser.add_argument('--account', type=str, help='Filter by account name')
    parser.add_argument('--limit', type=int, default=20, help='Number of transactions to show (default: 20)')
    parser.add_argument('--no-metadata', action='store_true', help='Hide detailed metadata')
    
    args = parser.parse_args()
    
    debug_transactions(
        account_name=args.account,
        limit=args.limit,
        show_metadata=not args.no_metadata
    )

if __name__ == "__main__":
    main()