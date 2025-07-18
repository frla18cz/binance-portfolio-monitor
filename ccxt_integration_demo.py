#!/usr/bin/env python3
"""
Demonstration of how to integrate CCXT for transaction history capture.
This shows how to replace the problematic python-binance implementation with CCXT.
"""

import os
import sys
import json
from datetime import datetime, timezone
import ccxt
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('.env')

def fetch_transactions_with_ccxt(api_key, api_secret, account_id, account_name):
    """
    Fetch all deposits and withdrawals using CCXT.
    Returns a list of transactions in a format compatible with the existing system.
    """
    
    # Initialize CCXT Binance exchange
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    
    transactions = []
    
    # Fetch deposits
    try:
        deposits = exchange.fetch_deposits()
        print(f"   Found {len(deposits)} deposits for {account_name}")
        
        for deposit in deposits:
            # Convert CCXT format to our system format
            transaction = {
                'account_id': account_id,
                'transaction_id': deposit.get('id', ''),
                'type': 'deposit',
                'currency': deposit.get('currency', ''),
                'amount': float(deposit.get('amount', 0)),
                'timestamp': deposit.get('datetime', ''),
                'status': deposit.get('status', ''),
                'txid': deposit.get('txid', ''),
                'metadata': {
                    'network': deposit.get('network', ''),
                    'address': deposit.get('address', ''),
                    'tag': deposit.get('tag', ''),
                    'fee': deposit.get('fee', {}).get('cost', 0) if deposit.get('fee') else 0,
                    'raw_info': deposit.get('info', {})  # Store raw Binance response
                }
            }
            transactions.append(transaction)
    except Exception as e:
        print(f"   ❌ Error fetching deposits: {e}")
    
    # Fetch withdrawals
    try:
        withdrawals = exchange.fetch_withdrawals()
        print(f"   Found {len(withdrawals)} withdrawals for {account_name}")
        
        for withdrawal in withdrawals:
            # Check if it's an internal transfer
            info = withdrawal.get('info', {})
            is_internal = (info.get('transferType') == 1 or 
                          info.get('txId') == 'Internal transfer')
            
            transaction = {
                'account_id': account_id,
                'transaction_id': withdrawal.get('id', ''),
                'type': 'withdrawal',
                'currency': withdrawal.get('currency', ''),
                'amount': float(withdrawal.get('amount', 0)),
                'timestamp': withdrawal.get('datetime', ''),
                'status': withdrawal.get('status', ''),
                'txid': withdrawal.get('txid', ''),
                'metadata': {
                    'network': withdrawal.get('network', '') or info.get('network', ''),
                    'address': withdrawal.get('address', '') or info.get('address', ''),
                    'tag': withdrawal.get('tag', ''),
                    'fee': withdrawal.get('fee', {}).get('cost', 0) if withdrawal.get('fee') else 0,
                    'is_internal_transfer': is_internal,
                    'transfer_type': info.get('transferType', 0),
                    'raw_info': info  # Store raw Binance response
                }
            }
            
            if is_internal:
                print(f"      ⚡ Internal transfer detected: {withdrawal.get('datetime')} - {withdrawal.get('amount')} {withdrawal.get('currency')}")
            
            transactions.append(transaction)
    except Exception as e:
        print(f"   ❌ Error fetching withdrawals: {e}")
    
    # Also fetch dividend/distribution records (airdrops, token swaps, etc.)
    try:
        params = {'timestamp': exchange.milliseconds()}
        response = exchange.sapiGetAssetAssetDividend(params)
        
        if response and response.get('total', 0) > 0:
            print(f"   Found {response['total']} dividend/distribution records")
            
            for record in response.get('rows', []):
                # Convert dividend record to transaction format
                transaction = {
                    'account_id': account_id,
                    'transaction_id': f"div_{record.get('id', '')}",
                    'type': 'deposit',  # Treat dividends as deposits
                    'currency': record.get('asset', ''),
                    'amount': float(record.get('amount', 0)),
                    'timestamp': datetime.fromtimestamp(record.get('divTime', 0) / 1000, tz=timezone.utc).isoformat(),
                    'status': 'ok',
                    'txid': f"dividend_{record.get('tranId', '')}",
                    'metadata': {
                        'source': 'dividend',
                        'info': record.get('enInfo', ''),
                        'raw_info': record
                    }
                }
                transactions.append(transaction)
    except Exception as e:
        print(f"   ⚠️  Could not fetch dividend records: {e}")
    
    return transactions


def demonstrate_ccxt_integration():
    """Demonstrate how CCXT can replace python-binance for transaction history."""
    
    from utils.database_manager import get_supabase_client
    
    print("🚀 CCXT Integration Demonstration\n")
    print("This shows how CCXT can fetch transaction history with read-only permissions.\n")
    
    try:
        db_client = get_supabase_client()
        accounts_response = db_client.table('binance_accounts').select('*').execute()
        
        if not accounts_response.data:
            print("❌ No accounts found in database")
            return
        
        all_transactions = []
        
        # Process each account
        for account in accounts_response.data:
            account_id = account['id']
            account_name = account['account_name']
            api_key = account['api_key']
            api_secret = account['api_secret']
            
            print(f"\n📊 Processing account: {account_name}")
            print("-" * 50)
            
            # Fetch transactions using CCXT
            transactions = fetch_transactions_with_ccxt(
                api_key, api_secret, account_id, account_name
            )
            
            all_transactions.extend(transactions)
            
            # Show summary
            deposits = [t for t in transactions if t['type'] == 'deposit']
            withdrawals = [t for t in transactions if t['type'] == 'withdrawal']
            
            print(f"\n   Summary:")
            print(f"   - Deposits: {len(deposits)}")
            print(f"   - Withdrawals: {len(withdrawals)}")
            print(f"   - Total: {len(transactions)}")
        
        # Show all transactions found
        print(f"\n\n{'='*70}")
        print(f"TOTAL TRANSACTIONS FOUND: {len(all_transactions)}")
        print(f"{'='*70}\n")
        
        # Group by type
        by_type = {}
        for t in all_transactions:
            t_type = t['type']
            if t_type not in by_type:
                by_type[t_type] = []
            by_type[t_type].append(t)
        
        for t_type, items in by_type.items():
            print(f"\n{t_type.upper()}S ({len(items)} total):")
            print("-" * 50)
            
            # Sort by timestamp
            items.sort(key=lambda x: x['timestamp'])
            
            for t in items[-10:]:  # Show last 10
                is_internal = t.get('metadata', {}).get('is_internal_transfer', False)
                internal_marker = " [INTERNAL]" if is_internal else ""
                source = t.get('metadata', {}).get('source', '')
                source_marker = f" [{source.upper()}]" if source else ""
                
                print(f"{t['timestamp']} | {t['amount']:>15.8f} {t['currency']:<6} | "
                      f"Status: {t['status']:<10} | TxID: {t['txid'][:20]}...{internal_marker}{source_marker}")
        
        # Show how this would be saved to the database
        print(f"\n\n{'='*70}")
        print("HOW TO INTEGRATE INTO EXISTING SYSTEM:")
        print(f"{'='*70}\n")
        
        print("1. Replace the fetch_new_transactions() function in api/index.py with CCXT calls")
        print("2. The transaction format above is compatible with the existing database schema")
        print("3. CCXT provides all necessary fields including metadata for internal transfers")
        print("4. This works with READ-ONLY API permissions - no dangerous permissions needed!")
        print("\nKey advantages of CCXT:")
        print("- ✅ Works with read-only permissions")
        print("- ✅ Detects internal transfers")
        print("- ✅ Includes dividend/distribution records")
        print("- ✅ Provides comprehensive metadata")
        print("- ✅ Well-maintained library with good documentation")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demonstrate_ccxt_integration()