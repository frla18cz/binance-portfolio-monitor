#!/usr/bin/env python3
"""
Test script for transaction processing with metadata
Tests the enhanced withdrawal detection including internal transfers
"""

import os
import sys
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config import settings
from utils.database_manager import get_supabase_client
from api.index import get_prices, process_deposits_withdrawals
from binance.client import Client

def test_transaction_processing():
    """Test transaction processing with focus on metadata capture"""
    print("=" * 60)
    print("Testing Enhanced Transaction Processing")
    print("=" * 60)
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Get test account
        accounts = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
        
        if not accounts.data:
            print("❌ Ondra(test) account not found")
            return
            
        account = accounts.data[0]
        print(f"✅ Found account: {account['account_name']} (ID: {account['id']})")
        
        # Create Binance client first (for price fetching)
        temp_client = Client('', '')  # Empty keys for public data
        
        # Get current prices
        print("\n📊 Fetching current prices...")
        prices = get_prices(temp_client)
        if prices:
            print(f"✅ BTC: ${prices['BTCUSDT']:,.2f}, ETH: ${prices['ETHUSDT']:,.2f}")
        else:
            print("❌ Failed to fetch prices")
            return
        
        # Get benchmark config
        benchmark_configs = supabase.table('benchmark_configs')\
            .select('*')\
            .eq('account_id', account['id'])\
            .execute()
            
        if not benchmark_configs.data:
            print("❌ No benchmark config found")
            return
            
        config = benchmark_configs.data[0]
        
        # Create Binance client
        client = Client(account['api_key'], account['api_secret'])
        
        # Process deposits/withdrawals
        print(f"\n🔄 Processing deposits/withdrawals for {account['account_name']}...")
        updated_config = process_deposits_withdrawals(
            supabase, client, account['id'], config, prices
        )
        print("✅ Transaction processing completed")
        
        # Check for recent transactions with metadata
        print("\n📋 Checking recent transactions with metadata...")
        recent_txns = supabase.table('processed_transactions')\
            .select('*')\
            .eq('account_id', account['id'])\
            .order('timestamp', desc=True)\
            .limit(10)\
            .execute()
        
        if recent_txns.data:
            print(f"\n📊 Found {len(recent_txns.data)} recent transactions:")
            for txn in recent_txns.data:
                print(f"\n--- Transaction ---")
                print(f"ID: {txn['transaction_id']}")
                print(f"Type: {txn['transaction_type']}")
                print(f"Amount: {txn['amount']}")
                print(f"Timestamp: {txn['timestamp']}")
                
                # Check metadata
                if txn.get('metadata'):
                    print(f"📦 Metadata:")
                    metadata = txn['metadata']
                    print(f"  Transfer Type: {metadata.get('transfer_type')} (0=external, 1=internal)")
                    print(f"  TX ID: {metadata.get('tx_id')}")
                    print(f"  Coin: {metadata.get('coin')}")
                    print(f"  Network: {metadata.get('network')}")
                    
                    # Highlight internal transfers
                    if metadata.get('transfer_type') == 1 or 'Internal transfer' in str(metadata.get('tx_id', '')):
                        print("  🔄 THIS IS AN INTERNAL TRANSFER!")
                else:
                    print("  No metadata")
        else:
            print("No recent transactions found")
        
        # Check system logs for internal transfer detection
        print("\n📜 Checking system logs for internal transfers...")
        logs = supabase.table('system_logs')\
            .select('*')\
            .eq('operation', 'internal_transfer_detected')\
            .order('timestamp', desc=True)\
            .limit(5)\
            .execute()
        
        if logs.data:
            print(f"\n🔍 Found {len(logs.data)} internal transfer logs:")
            for log in logs.data:
                print(f"\n{log['timestamp']}: {log['message']}")
                if log.get('data'):
                    print(f"Data: {log['data']}")
        else:
            print("No internal transfer logs found")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_transaction_processing()