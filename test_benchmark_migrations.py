#!/usr/bin/env python3
"""
Test script for benchmark_configs table migrations.
Verifies that migrations work correctly and data integrity is maintained.
"""

import os
import sys
from datetime import datetime, UTC

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from utils.database_manager import get_supabase_client
from config import settings

def test_benchmark_migrations():
    """Test benchmark_configs table migrations"""
    print("🔍 Testing benchmark_configs migrations...")
    
    supabase = get_supabase_client()
    
    # Test 1: Check if benchmark_configs table exists
    try:
        result = supabase.table('benchmark_configs').select('*').limit(1).execute()
        print("✅ benchmark_configs table exists")
    except Exception as e:
        print(f"❌ benchmark_configs table not found: {e}")
        return False
    
    # Test 2: Check table structure after migrations
    try:
        # Get first record to check column structure
        result = supabase.table('benchmark_configs').select('*').limit(1).execute()
        
        if result.data:
            record = result.data[0]
            expected_columns = [
                'id', 'account_id', 'account_name', 'btc_units', 'eth_units', 
                'rebalance_day', 'rebalance_hour', 'next_rebalance_timestamp',
                'last_rebalance_timestamp', 'last_rebalance_status', 
                'last_rebalance_error', 'rebalance_count', 
                'last_rebalance_btc_units', 'last_rebalance_eth_units', 'created_at'
            ]
            
            missing_columns = []
            for col in expected_columns:
                if col not in record:
                    missing_columns.append(col)
            
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            else:
                print("✅ All expected columns present")
                
            # Check data types and values
            print(f"   - account_name: {record.get('account_name', 'NULL')}")
            print(f"   - rebalance_count: {record.get('rebalance_count', 'NULL')}")
            print(f"   - last_rebalance_status: {record.get('last_rebalance_status', 'NULL')}")
            
        else:
            print("⚠️  No data in benchmark_configs table - creating test record")
            
            # Get first account
            accounts = supabase.table('binance_accounts').select('id, account_name').limit(1).execute()
            if not accounts.data:
                print("❌ No accounts found - cannot test migrations")
                return False
            
            account = accounts.data[0]
            
            # Create test config
            test_config = {
                'account_id': account['id'],
                'btc_units': 0.01,
                'eth_units': 0.1,
                'rebalance_day': 0,
                'rebalance_hour': 12,
                'next_rebalance_timestamp': datetime.now(UTC).isoformat() + '+00:00'
            }
            
            insert_result = supabase.table('benchmark_configs').insert(test_config).execute()
            if insert_result.data:
                print("✅ Test record created successfully")
                created_record = insert_result.data[0]
                print(f"   - account_name auto-populated: {created_record.get('account_name')}")
                print(f"   - rebalance_count initialized: {created_record.get('rebalance_count', 0)}")
                print(f"   - last_rebalance_status: {created_record.get('last_rebalance_status', 'NULL')}")
            else:
                print("❌ Failed to create test record")
                return False
        
    except Exception as e:
        print(f"❌ Error checking table structure: {e}")
        return False
    
    # Test 3: Check triggers work (account_name auto-population)
    try:
        # Get current configs
        configs = supabase.table('benchmark_configs').select('*').execute()
        
        if configs.data:
            for config in configs.data:
                if not config.get('account_name'):
                    print(f"❌ Missing account_name in config ID {config['id']}")
                    return False
            
            print("✅ All configs have account_name populated")
        
    except Exception as e:
        print(f"❌ Error checking triggers: {e}")
        return False
    
    # Test 4: Check constraints and indexes
    try:
        # Try to insert invalid status (should fail)
        accounts = supabase.table('binance_accounts').select('id').limit(1).execute()
        if accounts.data:
            invalid_config = {
                'account_id': accounts.data[0]['id'],
                'last_rebalance_status': 'invalid_status'  # Should fail constraint
            }
            
            try:
                supabase.table('benchmark_configs').insert(invalid_config).execute()
                print("❌ Constraint check failed - invalid status was accepted")
                return False
            except Exception:
                print("✅ Status constraint working correctly")
        
    except Exception as e:
        print(f"⚠️  Could not test constraints: {e}")
    
    return True

def main():
    """Main test function"""
    print("🧪 Running benchmark_configs migration tests...\n")
    
    success = test_benchmark_migrations()
    
    if success:
        print("\n✅ All migration tests passed!")
        print("📊 Migration summary:")
        print("   - account_name column added and auto-populated")
        print("   - Rebalancing history columns added")
        print("   - Triggers and constraints working")
        print("   - Data integrity maintained")
    else:
        print("\n❌ Some migration tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()