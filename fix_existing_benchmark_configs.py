#!/usr/bin/env python3
"""
Migration script to fix existing benchmark configs after adding initialized_at column.

This script:
1. Sets initialized_at to NOW() for existing configs (assumes they're already correct)
2. Deletes all processed_transactions (to prevent duplicate processing)
3. Verifies benchmark values are reasonable (ratio close to 1.0)

Run this AFTER adding initialized_at column to benchmark_configs table.
"""

from datetime import datetime, timezone
from utils.database_manager import get_supabase_client

def fix_existing_accounts():
    """Fix existing benchmark configs and clean up processed transactions."""
    supabase = get_supabase_client()
    
    print("🔧 Starting migration to fix existing benchmark configs...")
    
    # Step 1: Get all benchmark configs without initialized_at
    print("\n📋 Step 1: Checking benchmark configs...")
    configs = supabase.table('benchmark_configs').select('*').execute()
    
    if not configs.data:
        print("❌ No benchmark configs found!")
        return
        
    print(f"Found {len(configs.data)} benchmark configs")
    
    # Step 2: Set initialized_at for configs that don't have it
    current_time = datetime.now(timezone.utc).isoformat() + '+00:00'
    updated_count = 0
    
    for config in configs.data:
        account_id = config['account_id']
        
        if not config.get('initialized_at'):
            print(f"📝 Setting initialized_at for account {account_id}")
            
            # Update config with initialized_at
            update_response = supabase.table('benchmark_configs').update({
                'initialized_at': current_time
            }).eq('account_id', account_id).execute()
            
            if update_response.data:
                updated_count += 1
                print(f"✅ Updated account {account_id}")
            else:
                print(f"❌ Failed to update account {account_id}")
        else:
            print(f"⏩ Account {account_id} already has initialized_at")
    
    print(f"\n📊 Updated {updated_count} benchmark configs with initialized_at")
    
    # Step 3: Delete all processed transactions to prevent duplicates
    print("\n🗑️  Step 3: Cleaning up processed transactions...")
    
    # Get count before deletion
    count_response = supabase.table('processed_transactions').select('id', count='exact').execute()
    transaction_count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
    
    if transaction_count > 0:
        print(f"Found {transaction_count} processed transactions to delete")
        
        # Delete all processed transactions  
        delete_response = supabase.table('processed_transactions').delete().gt('id', 0).execute()
        
        print(f"✅ Deleted {len(delete_response.data)} processed transactions")
    else:
        print("✅ No processed transactions to delete")
    
    # Step 4: Verify benchmark values are reasonable
    print("\n🔍 Step 4: Verifying benchmark values...")
    
    # Get accounts with their latest NAV data
    accounts = supabase.table('binance_accounts').select('id, account_name').execute()
    
    for account in accounts.data:
        account_id = account['id']
        account_name = account['account_name']
        
        # Get latest NAV
        nav_data = supabase.table('nav_history').select('nav, benchmark_value').eq('account_id', account_id).order('timestamp', desc=True).limit(1).execute()
        
        if nav_data.data:
            nav = nav_data.data[0]['nav']
            benchmark = nav_data.data[0]['benchmark_value']
            
            if nav > 0 and benchmark > 0:
                ratio = benchmark / nav
                
                if 0.5 <= ratio <= 2.0:
                    print(f"✅ {account_name}: NAV=${nav:.2f}, Benchmark=${benchmark:.2f}, Ratio={ratio:.3f}x - OK")
                else:
                    print(f"⚠️  {account_name}: NAV=${nav:.2f}, Benchmark=${benchmark:.2f}, Ratio={ratio:.3f}x - SUSPICIOUS")
                    
                    if ratio > 2.0:
                        print(f"   🔧 Consider manually fixing benchmark for {account_name}")
            else:
                print(f"❓ {account_name}: No valid NAV/benchmark data")
        else:
            print(f"❓ {account_name}: No NAV history found")
    
    print("\n✅ Migration completed successfully!")
    print("\n📝 Next steps:")
    print("1. Run monitoring to test the fix: python -m api.index")
    print("2. Verify no duplicate transactions are processed")
    print("3. Check that benchmark ratios remain stable")

if __name__ == "__main__":
    fix_existing_accounts()