#!/usr/bin/env python3
"""
Check current benchmark_configs table structure.
"""

import os
import sys
from datetime import datetime, UTC

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from utils.database_manager import get_supabase_client
from config import settings

def check_table_structure():
    """Check benchmark_configs table structure"""
    print("🔍 Checking benchmark_configs table structure...")
    
    supabase = get_supabase_client()
    
    try:
        # Get table structure by fetching all columns
        result = supabase.table('benchmark_configs').select('*').limit(1).execute()
        
        if result.data:
            record = result.data[0]
            print(f"📊 Current columns in benchmark_configs:")
            for column in sorted(record.keys()):
                value = record[column]
                print(f"   - {column}: {value} ({type(value).__name__})")
        else:
            print("⚠️  No data in benchmark_configs table")
            
        # Try to get table schema info
        print("\n🔍 Trying to get table schema...")
        
        # Use information_schema to get column info
        schema_query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'benchmark_configs'
        ORDER BY ordinal_position;
        """
        
        # This might not work with Supabase client, but let's try
        try:
            schema_result = supabase.rpc('execute_sql', {'sql': schema_query})
            print("✅ Schema query result:", schema_result)
        except Exception as e:
            print(f"❌ Cannot get schema info: {e}")
            
    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False
    
    return True

def main():
    """Main function"""
    check_table_structure()

if __name__ == "__main__":
    main()