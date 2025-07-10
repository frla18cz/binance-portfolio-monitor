#!/usr/bin/env python3
"""
Apply Migration Script - Clears tables and adds account_name to nav_history
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import settings
from supabase import create_client

def apply_migration():
    """Apply the migration to clear tables and add account_name column."""
    
    print("🔧 Connecting to Supabase...")
    supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
    
    # Read migration SQL
    migration_file = Path("migrations/clear_tables_add_account_name.sql")
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print("\n" + "="*60)
    print("📋 Migration to apply:")
    print("="*60)
    print(migration_sql)
    print("="*60)
    
    # Get confirmation
    print("\n⚠️  WARNING: This migration will:")
    print("   - DELETE ALL DATA from: system_metadata, system_logs, processed_transactions")
    print("   - DELETE ALL DATA from: price_history, nav_history")
    print("   - Add account_name column to nav_history table")
    print("   - Create trigger to auto-populate account_name")
    
    response = input("\n❓ Are you sure you want to proceed? (yes/N): ")
    if response.lower() != 'yes':
        print("❌ Migration cancelled")
        return False
    
    # Check current record counts
    print("\n📊 Current record counts:")
    tables = ['system_metadata', 'system_logs', 'processed_transactions', 'price_history', 'nav_history']
    
    for table in tables:
        try:
            result = supabase.table(table).select('count', count='exact').execute()
            count = result.count if hasattr(result, 'count') else 0
            print(f"   - {table}: {count} records")
        except Exception as e:
            print(f"   - {table}: Error getting count ({str(e)})")
    
    print("\n🚀 Applying migration...")
    print("⚠️  This migration must be run manually in Supabase SQL Editor")
    print("\n📖 Instructions:")
    print("1. Open https://supabase.com/dashboard")
    print("2. Select your project")
    print("3. Go to 'SQL Editor'")
    print("4. Create a new query")
    print("5. Copy and paste the migration SQL from:")
    print(f"   {migration_file.absolute()}")
    print("6. Click 'Run'")
    
    # Save backup information
    backup_info = {
        'timestamp': datetime.now().isoformat(),
        'migration': 'clear_tables_add_account_name',
        'tables_affected': tables
    }
    
    print(f"\n💾 Migration timestamp: {backup_info['timestamp']}")
    print("✅ Migration file ready for manual execution")
    
    return True

def verify_migration():
    """Verify the migration was applied successfully."""
    
    print("\n🔍 Verifying migration...")
    supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
    
    # Check if tables are empty
    print("\n📊 Post-migration record counts:")
    tables = ['system_metadata', 'system_logs', 'processed_transactions', 'price_history', 'nav_history']
    
    all_empty = True
    for table in tables:
        try:
            result = supabase.table(table).select('count', count='exact').execute()
            count = result.count if hasattr(result, 'count') else 0
            print(f"   - {table}: {count} records")
            if count > 0:
                all_empty = False
        except Exception as e:
            print(f"   - {table}: Error ({str(e)})")
    
    # Check if account_name column exists in nav_history
    try:
        print("\n🔍 Checking nav_history structure...")
        # Try to select the account_name column
        result = supabase.table('nav_history').select('account_name').limit(1).execute()
        print("✅ account_name column exists in nav_history")
    except Exception as e:
        print(f"❌ account_name column not found: {str(e)}")
    
    if all_empty:
        print("\n✅ All tables successfully cleared")
    else:
        print("\n⚠️  Some tables still contain data")
    
    return True

def main():
    """Main function."""
    print("🗄️  Binance Portfolio Monitor - Database Migration")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'verify':
        verify_migration()
    else:
        apply_migration()

if __name__ == "__main__":
    main()