#!/usr/bin/env python3
"""
Apply migration to add PAY transaction types to database
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.database_manager import get_supabase_client

def apply_migration():
    """Apply the PAY transaction types migration"""
    
    print("🚀 Applying PAY transaction types migration...")
    
    # Read migration SQL
    migration_file = Path(__file__).parent / "migrations" / "add_pay_transaction_types.sql"
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    try:
        # Execute the migration
        # Note: Supabase doesn't have a direct SQL execution method in the Python client
        # We'll need to use the database URL directly or apply via Supabase dashboard
        
        print("\n⚠️  Please apply this migration manually in Supabase SQL editor:")
        print("=" * 60)
        print(sql)
        print("=" * 60)
        print("\n✅ After applying, PAY_DEPOSIT and PAY_WITHDRAWAL types will be supported")
        
        # Alternative: Check current constraint
        result = supabase.table('processed_transactions').select('transaction_type').limit(1).execute()
        print(f"\n📊 Current table accessible: {bool(result.data is not None)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    apply_migration()