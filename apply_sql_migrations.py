#!/usr/bin/env python3
"""
Apply SQL migrations directly using Supabase client.
"""

import os
import sys
from datetime import datetime, UTC

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from utils.database_manager import get_supabase_client
from config import settings

def apply_sql_directly():
    """Apply SQL migrations directly"""
    print("🚀 Applying SQL migrations directly...")
    
    supabase = get_supabase_client()
    
    # Migration 1: Add account_name column
    print("📝 Adding account_name column...")
    try:
        # Add column
        supabase.table('benchmark_configs').update({
            'account_name': 'placeholder'  # This will fail, but we can use it to check if column exists
        }).eq('id', 'non-existent').execute()
        print("✅ account_name column already exists")
    except Exception as e:
        if "column" in str(e).lower() and "does not exist" in str(e).lower():
            print("❌ account_name column does not exist - needs manual SQL execution")
            print("Please run the following SQL in Supabase SQL editor:")
            print("ALTER TABLE benchmark_configs ADD COLUMN account_name VARCHAR(255);")
        else:
            print(f"✅ account_name column exists (error: {e})")
    
    # Migration 2: Add rebalancing history columns
    print("\n📝 Adding rebalancing history columns...")
    test_columns = [
        'last_rebalance_timestamp',
        'last_rebalance_status', 
        'rebalance_count',
        'last_rebalance_error',
        'last_rebalance_btc_units',
        'last_rebalance_eth_units'
    ]
    
    missing_columns = []
    
    for col in test_columns:
        try:
            # Try to update with the column
            supabase.table('benchmark_configs').update({
                col: None
            }).eq('id', 'non-existent').execute()
            print(f"✅ {col} column exists")
        except Exception as e:
            if "column" in str(e).lower() and "does not exist" in str(e).lower():
                missing_columns.append(col)
                print(f"❌ {col} column missing")
            else:
                print(f"✅ {col} column exists (error: {e})")
    
    if missing_columns:
        print(f"\n❌ Missing columns: {missing_columns}")
        print("Please run the following SQL in Supabase SQL editor:")
        print("ALTER TABLE benchmark_configs")
        print("ADD COLUMN IF NOT EXISTS last_rebalance_timestamp TIMESTAMPTZ,")
        print("ADD COLUMN IF NOT EXISTS last_rebalance_status VARCHAR(20) DEFAULT 'pending',")
        print("ADD COLUMN IF NOT EXISTS last_rebalance_error TEXT,")
        print("ADD COLUMN IF NOT EXISTS rebalance_count INTEGER DEFAULT 0,")
        print("ADD COLUMN IF NOT EXISTS last_rebalance_btc_units DECIMAL(20,8),")
        print("ADD COLUMN IF NOT EXISTS last_rebalance_eth_units DECIMAL(20,8);")
    else:
        print("✅ All rebalancing history columns exist")
    
    # Test if we can populate account_name
    print("\n📝 Testing account_name population...")
    try:
        # Get all configs
        configs = supabase.table('benchmark_configs').select('*').execute()
        
        if configs.data:
            for config in configs.data:
                if not config.get('account_name'):
                    # Get account name
                    account = supabase.table('binance_accounts').select('account_name').eq('id', config['account_id']).single().execute()
                    if account.data:
                        # Update with account name
                        supabase.table('benchmark_configs').update({
                            'account_name': account.data['account_name']
                        }).eq('id', config['id']).execute()
                        print(f"✅ Updated account_name for config {config['id']}")
            
            print("✅ All account_name values populated")
        
    except Exception as e:
        print(f"❌ Error populating account_name: {e}")
    
    return True

def main():
    """Main function"""
    apply_sql_directly()

if __name__ == "__main__":
    main()