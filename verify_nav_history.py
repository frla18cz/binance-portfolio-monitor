#!/usr/bin/env python3
"""
Verify nav_history table after migration
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import settings
from supabase import create_client
from datetime import datetime, UTC

def verify_nav_history():
    """Verify nav_history table structure and test account_name population."""
    
    print("🔧 Connecting to Supabase...")
    supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
    
    # Check if account_name column exists
    print("\n🔍 Checking nav_history structure...")
    try:
        # First, get accounts
        accounts_result = supabase.table('binance_accounts').select('id, account_name').execute()
        accounts = accounts_result.data
        
        if not accounts:
            print("❌ No accounts found in binance_accounts table")
            return
        
        print(f"✅ Found {len(accounts)} accounts:")
        for acc in accounts:
            print(f"   - {acc['account_name']} (ID: {acc['id']})")
        
        # Try to query nav_history with account_name
        print("\n🔍 Checking nav_history table...")
        nav_result = supabase.table('nav_history').select('*').limit(5).order('timestamp', desc=True).execute()
        
        if nav_result.data:
            print(f"✅ Found {len(nav_result.data)} recent records:")
            for record in nav_result.data:
                account_name = record.get('account_name', 'NOT SET')
                print(f"   - {record['timestamp']}: NAV ${record['nav']:.2f} | Account: {account_name}")
        else:
            print("ℹ️  No records in nav_history (table is empty)")
        
        # Test inserting a new record
        print("\n🧪 Testing new record insertion...")
        test_account = accounts[0]
        test_data = {
            'account_id': test_account['id'],
            'timestamp': datetime.now(UTC).isoformat(),
            'nav': 10000.00,
            'benchmark_value': 9500.00,
            'btc_price': 45000.00,
            'eth_price': 3000.00
        }
        
        try:
            insert_result = supabase.table('nav_history').insert(test_data).execute()
            
            # Query back the inserted record
            verify_result = supabase.table('nav_history').select('*').order('timestamp', desc=True).limit(1).execute()
            
            if verify_result.data:
                inserted = verify_result.data[0]
                if inserted.get('account_name'):
                    print(f"✅ Trigger working! Account name auto-populated: {inserted['account_name']}")
                else:
                    print("❌ Trigger not working - account_name is empty")
                
                # Clean up test record
                supabase.table('nav_history').delete().eq('id', inserted['id']).execute()
                print("🧹 Test record cleaned up")
            
        except Exception as e:
            print(f"❌ Error testing insertion: {str(e)}")
            print("   This might mean the migration hasn't been applied yet")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if "column" in str(e).lower() and "account_name" in str(e).lower():
            print("   The account_name column doesn't exist yet - run the migration first")

def main():
    """Main function."""
    print("🗄️  Binance Portfolio Monitor - Verify nav_history")
    print("=" * 60)
    
    verify_nav_history()

if __name__ == "__main__":
    main()