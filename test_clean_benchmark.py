#!/usr/bin/env python3
"""
Test script for the clean benchmark system.
Verifies database structure and tests the new price column functionality.
"""

import os
import sys
from datetime import datetime, UTC
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def main():
    print("🧪 Testing Clean Benchmark System")
    print("=" * 50)
    
    # Initialize Supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        return False
    
    supabase = create_client(supabase_url, supabase_key)
    print("✅ Supabase client initialized")
    
    # Test 1: Check nav_history table structure
    print("\n📋 Test 1: Database Structure")
    print("-" * 30)
    
    try:
        # Try to query with price columns
        result = supabase.table('nav_history').select('account_id, timestamp, nav, benchmark_value, btc_price, eth_price').limit(1).execute()
        print("✅ Price columns (btc_price, eth_price) exist in nav_history table")
        
        if result.data:
            print(f"📊 Current record count: {len(result.data)}")
            sample_record = result.data[0]
            print(f"📝 Sample record structure: {list(sample_record.keys())}")
        else:
            print("📊 No records found in nav_history (clean start confirmed)")
            
    except Exception as e:
        if 'btc_price' in str(e) or 'eth_price' in str(e):
            print("❌ Price columns missing from nav_history table")
            print(f"   Error: {str(e)}")
            print("   📋 Please run the SQL migration:")
            print("   ALTER TABLE nav_history ADD COLUMN btc_price NUMERIC(10,2), ADD COLUMN eth_price NUMERIC(10,2);")
            return False
        else:
            print(f"❌ Database error: {str(e)}")
            return False
    
    # Test 2: Check benchmark configs
    print("\n⚙️  Test 2: Benchmark Configuration")
    print("-" * 30)
    
    try:
        configs = supabase.table('benchmark_configs').select('*').execute()
        if configs.data:
            for config in configs.data:
                account_id = config.get('account_id')
                btc_units = config.get('btc_units', 0)
                eth_units = config.get('eth_units', 0)
                print(f"📈 Account {account_id}: BTC={btc_units:.6f}, ETH={eth_units:.6f}")
        else:
            print("📊 No benchmark configs found")
            
    except Exception as e:
        print(f"❌ Error checking benchmark configs: {str(e)}")
    
    # Test 3: Check account setup
    print("\n👤 Test 3: Account Setup")
    print("-" * 30)
    
    try:
        accounts = supabase.table('binance_accounts').select('id, account_name, api_key').execute()
        if accounts.data:
            for account in accounts.data:
                account_name = account.get('account_name', 'Unknown')
                has_api_key = bool(account.get('api_key'))
                print(f"👤 Account: {account_name} (API Key: {'✅' if has_api_key else '❌'})")
        else:
            print("📊 No accounts configured")
            
    except Exception as e:
        print(f"❌ Error checking accounts: {str(e)}")
    
    print("\n🏁 Test Summary")
    print("=" * 50)
    print("✅ Clean benchmark system ready for testing")
    print("📝 Next steps:")
    print("   1. If price columns are missing, run: add_price_columns.sql in Supabase")
    print("   2. Run monitoring: python scrape_data.py")
    print("   3. Check dashboard: python api/dashboard.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)