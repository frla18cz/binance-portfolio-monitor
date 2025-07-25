#!/usr/bin/env python3
"""
Script to analyze historical transfers across all accounts
Looks for different transfer types and provides statistics
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from binance.client import Client
from utils.database_manager import get_supabase_client
from api.index import get_prices

def analyze_historical_transfers(days_back=30):
    """Analyze historical transfers for all accounts"""
    print(f"🔍 Analyzing transfers from the last {days_back} days")
    print("=" * 80)
    
    try:
        supabase = get_supabase_client()
        
        # Get all accounts
        accounts = supabase.table('binance_accounts').select('*').execute()
        
        if not accounts.data:
            print("❌ No accounts found")
            return
            
        print(f"📊 Found {len(accounts.data)} accounts to analyze\n")
        
        # Statistics
        total_stats = {
            'total_deposits': 0,
            'total_withdrawals': 0,
            'external_withdrawals': 0,
            'internal_withdrawals': 0,
            'withdrawals_by_coin': defaultdict(int),
            'withdrawals_by_network': defaultdict(int),
            'internal_indicators': defaultdict(int)
        }
        
        # Analyze each account
        for account in accounts.data:
            print(f"\n{'='*60}")
            print(f"Account: {account['account_name']} (ID: {account['id'][:8]}...)")
            print(f"{'='*60}")
            
            # Initialize client
            client = Client(account['api_key'], account['api_secret'])
            
            # Calculate start time
            start_time = datetime.now(timezone.utc) - timedelta(days=days_back)
            start_timestamp = int(start_time.timestamp() * 1000)
            
            try:
                # Get withdrawals
                print(f"\n📤 Fetching withdrawals...")
                withdrawals = client.get_withdraw_history(startTime=start_timestamp)
                
                if withdrawals:
                    print(f"   Found {len(withdrawals)} withdrawals")
                    
                    # Analyze each withdrawal
                    for w in withdrawals:
                        total_stats['total_withdrawals'] += 1
                        
                        # Extract data
                        transfer_type = w.get('transferType', 0)
                        tx_id = w.get('txId', '')
                        coin = w.get('coin', 'UNKNOWN')
                        network = w.get('network', 'UNKNOWN')
                        amount = float(w.get('amount', 0))
                        status = w.get('status')
                        address = w.get('address', '')
                        
                        # Count by coin
                        total_stats['withdrawals_by_coin'][coin] += 1
                        
                        # Detect internal transfers
                        is_internal = False
                        internal_reason = []
                        
                        if transfer_type == 1:
                            is_internal = True
                            internal_reason.append('transferType=1')
                            total_stats['internal_indicators']['transferType=1'] += 1
                            
                        if 'internal' in tx_id.lower():
                            is_internal = True
                            internal_reason.append('txId contains "internal"')
                            total_stats['internal_indicators']['txId_internal'] += 1
                            
                        if 'off-chain' in tx_id.lower():
                            is_internal = True
                            internal_reason.append('txId contains "off-chain"')
                            total_stats['internal_indicators']['txId_offchain'] += 1
                            
                        if '@' in address:
                            is_internal = True
                            internal_reason.append('email address')
                            total_stats['internal_indicators']['email_address'] += 1
                            
                        if address.startswith('+'):
                            is_internal = True
                            internal_reason.append('phone number')
                            total_stats['internal_indicators']['phone_number'] += 1
                        
                        if is_internal:
                            total_stats['internal_withdrawals'] += 1
                            print(f"\n   🔄 INTERNAL TRANSFER DETECTED:")
                            print(f"      Amount: {amount} {coin}")
                            print(f"      Reasons: {', '.join(internal_reason)}")
                            print(f"      Address: {address[:20]}...")
                            print(f"      TX ID: {tx_id}")
                        else:
                            total_stats['external_withdrawals'] += 1
                            total_stats['withdrawals_by_network'][network] += 1
                        
                        # Show first few withdrawals in detail
                        if total_stats['total_withdrawals'] <= 3:
                            print(f"\n   Sample Withdrawal:")
                            print(f"   - Amount: {amount} {coin}")
                            print(f"   - Transfer Type: {transfer_type}")
                            print(f"   - Network: {network}")
                            print(f"   - TX ID: {tx_id}")
                            print(f"   - Status: {status}")
                            
                else:
                    print("   No withdrawals found")
                
                # Get deposits
                print(f"\n📥 Fetching deposits...")
                deposits = client.get_deposit_history(startTime=start_timestamp)
                
                if deposits:
                    print(f"   Found {len(deposits)} deposits")
                    total_stats['total_deposits'] += len(deposits)
                else:
                    print("   No deposits found")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
        # Print summary statistics
        print(f"\n{'='*80}")
        print("📊 SUMMARY STATISTICS")
        print(f"{'='*80}")
        print(f"\nTotal Transactions:")
        print(f"  - Deposits: {total_stats['total_deposits']}")
        print(f"  - Withdrawals: {total_stats['total_withdrawals']}")
        
        if total_stats['total_withdrawals'] > 0:
            print(f"\nWithdrawal Analysis:")
            print(f"  - External transfers: {total_stats['external_withdrawals']} ({total_stats['external_withdrawals']/total_stats['total_withdrawals']*100:.1f}%)")
            print(f"  - Internal transfers: {total_stats['internal_withdrawals']} ({total_stats['internal_withdrawals']/total_stats['total_withdrawals']*100:.1f}%)")
            
            print(f"\nInternal Transfer Indicators:")
            for indicator, count in total_stats['internal_indicators'].items():
                print(f"  - {indicator}: {count}")
            
            print(f"\nWithdrawals by Coin:")
            for coin, count in sorted(total_stats['withdrawals_by_coin'].items(), key=lambda x: x[1], reverse=True):
                print(f"  - {coin}: {count}")
                
            if total_stats['external_withdrawals'] > 0:
                print(f"\nExternal Withdrawals by Network:")
                for network, count in sorted(total_stats['withdrawals_by_network'].items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {network}: {count}")
        
        # Check database for processed transactions
        print(f"\n{'='*80}")
        print("📦 DATABASE ANALYSIS")
        print(f"{'='*80}")
        
        # Get transactions with metadata
        txns_with_metadata = supabase.table('processed_transactions')\
            .select('*')\
            .not_.is_('metadata', 'null')\
            .limit(10)\
            .execute()
            
        if txns_with_metadata.data:
            print(f"\n✅ Found {len(txns_with_metadata.data)} transactions with metadata in database")
            
            # Analyze metadata
            internal_in_db = 0
            for txn in txns_with_metadata.data:
                if txn['metadata'].get('transfer_type') == 1:
                    internal_in_db += 1
                    
            print(f"   - Internal transfers in DB: {internal_in_db}")
        else:
            print("\n⚠️ No transactions with metadata found in database")
            print("   (This is normal if monitoring hasn't run since the update)")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze historical transfers')
    parser.add_argument('--days', type=int, default=30, help='Number of days to look back (default: 30)')
    
    args = parser.parse_args()
    
    print("🔍 Historical Transfer Analysis")
    print("=" * 80)
    
    analyze_historical_transfers(args.days)

if __name__ == "__main__":
    main()