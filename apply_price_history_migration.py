#!/usr/bin/env python3
"""
Apply the price_history table migration to combine BTC and ETH prices on the same row.
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from supabase import create_client

def apply_migration():
    """Apply the price_history table migration."""
    # Get Supabase credentials from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        return False
    
    # Create Supabase client
    supabase = create_client(supabase_url, supabase_key)
    
    try:
        # Read the migration SQL
        migration_file = project_root / "migrations" / "update_price_history_combined.sql"
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("Applying price_history migration...")
        print("This will:")
        print("1. Drop the existing price_history table (it's unused)")
        print("2. Create new table with btc_price and eth_price columns")
        print("3. Add appropriate indexes")
        print()
        
        # Confirm with user
        response = input("Do you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return False
        
        # Execute the migration
        # Note: Supabase Python client doesn't support raw SQL execution directly,
        # so we need to use the REST API
        print("\nMigration SQL has been generated. Please run this SQL in Supabase SQL Editor:")
        print("-" * 80)
        print(migration_sql)
        print("-" * 80)
        print("\nTo apply this migration:")
        print("1. Go to your Supabase project")
        print("2. Navigate to SQL Editor")
        print("3. Paste the SQL above")
        print("4. Click 'Run'")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)