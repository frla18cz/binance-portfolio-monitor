#!/usr/bin/env python3
"""
Apply benchmark_configs table migrations.
Adds account_name column and rebalancing history columns.
"""

import os
import sys
from datetime import datetime, UTC

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from utils.database_manager import get_supabase_client
from config import settings

def apply_migration(supabase, migration_file, description):
    """Apply a single migration file"""
    print(f"📝 Applying migration: {description}")
    
    try:
        # Read migration file
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Execute migration
        result = supabase.rpc('execute_sql', {'sql': migration_sql})
        print(f"✅ Migration applied successfully: {description}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to apply migration {description}: {e}")
        return False

def apply_migrations():
    """Apply all benchmark_configs migrations"""
    print("🚀 Starting benchmark_configs migrations...\n")
    
    supabase = get_supabase_client()
    
    migrations = [
        {
            'file': 'migrations/add_account_name_to_benchmark_configs.sql',
            'description': 'Add account_name column to benchmark_configs'
        },
        {
            'file': 'migrations/add_rebalancing_history_to_benchmark_configs.sql',
            'description': 'Add rebalancing history columns to benchmark_configs'
        }
    ]
    
    success_count = 0
    total_count = len(migrations)
    
    for migration in migrations:
        if apply_migration(supabase, migration['file'], migration['description']):
            success_count += 1
        print()  # Empty line for readability
    
    print(f"📊 Migration Summary:")
    print(f"   - Applied: {success_count}/{total_count} migrations")
    
    if success_count == total_count:
        print("✅ All migrations applied successfully!")
        return True
    else:
        print("❌ Some migrations failed!")
        return False

def main():
    """Main function"""
    success = apply_migrations()
    
    if success:
        print("\n🎉 Benchmark migrations completed successfully!")
        print("🔄 You can now run test_benchmark_migrations.py to verify")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()