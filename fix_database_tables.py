#!/usr/bin/env python3
"""
Database Fix Script - Creates missing tables needed for transaction processing
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import settings
from supabase import create_client

def create_missing_tables():
    """Create the missing tables that are causing 404 errors."""
    
    print("🔧 Connecting to Supabase...")
    
    # Create Supabase client
    supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
    
    # Check if binance_accounts uses UUID or INTEGER
    check_id_type_sql = """
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'binance_accounts' 
    AND column_name = 'id';
    """
    
    try:
        # First, check the ID type
        print("🔍 Checking binance_accounts ID type...")
        result = supabase.table('binance_accounts').select('id').limit(1).execute()
        
        # Determine ID type based on the result
        if result.data and len(result.data) > 0:
            sample_id = result.data[0]['id']
            if isinstance(sample_id, str) and '-' in sample_id:
                id_type = "UUID"
                id_column_def = "UUID"
            else:
                id_type = "INTEGER"
                id_column_def = "INTEGER"
        else:
            # Default to UUID if no data
            id_type = "UUID"
            id_column_def = "UUID"
            
        print(f"✅ Detected ID type: {id_type}")
        
    except Exception as e:
        print(f"⚠️  Could not determine ID type, defaulting to UUID: {e}")
        id_type = "UUID"
        id_column_def = "UUID"
    
    # SQL for creating missing tables with proper ID type
    create_tables_sql = f"""
    -- Create missing tables for transaction processing
    
    -- 1. Transaction processing tracking (prevents duplicates)
    CREATE TABLE IF NOT EXISTS processed_transactions (
        id SERIAL PRIMARY KEY,
        account_id {id_column_def} REFERENCES binance_accounts(id),
        transaction_id VARCHAR(50) UNIQUE NOT NULL,
        transaction_type VARCHAR(20) NOT NULL,
        amount DECIMAL(20,8) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        status VARCHAR(20) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    -- 2. Processing status per account
    CREATE TABLE IF NOT EXISTS account_processing_status (
        account_id {id_column_def} PRIMARY KEY REFERENCES binance_accounts(id),
        last_processed_timestamp TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    -- 3. Price history table (optional but useful)
    CREATE TABLE IF NOT EXISTS price_history (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ NOT NULL,
        asset VARCHAR(10) NOT NULL,
        price DECIMAL(20,8) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    
    # SQL for creating indexes
    create_indexes_sql = """
    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_processed_transactions_account_id ON processed_transactions(account_id);
    CREATE INDEX IF NOT EXISTS idx_processed_transactions_timestamp ON processed_transactions(timestamp);
    CREATE INDEX IF NOT EXISTS idx_processed_transactions_transaction_id ON processed_transactions(transaction_id);
    
    CREATE INDEX IF NOT EXISTS idx_account_processing_status_account_id ON account_processing_status(account_id);
    CREATE INDEX IF NOT EXISTS idx_account_processing_status_updated_at ON account_processing_status(updated_at);
    
    CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp);
    CREATE INDEX IF NOT EXISTS idx_price_history_asset ON price_history(asset);
    """
    
    # SQL for adding comments
    add_comments_sql = """
    -- Add comments for documentation
    COMMENT ON TABLE processed_transactions IS 'Tracks all processed deposit/withdrawal transactions to prevent duplicate processing';
    COMMENT ON TABLE account_processing_status IS 'Stores the last processed timestamp for each account to track transaction processing state';
    COMMENT ON TABLE price_history IS 'Historical price data for BTC and ETH used for benchmark calculations';
    """
    
    print("\n📋 SQL to create missing tables:")
    print("="*60)
    print(create_tables_sql)
    print(create_indexes_sql)
    print(add_comments_sql)
    print("="*60)
    
    # Try to test if tables exist
    tables_to_check = ['processed_transactions', 'account_processing_status', 'price_history']
    existing_tables = []
    missing_tables = []
    
    for table_name in tables_to_check:
        try:
            result = supabase.table(table_name).select('count').limit(1).execute()
            existing_tables.append(table_name)
            print(f"✅ Table '{table_name}' already exists")
        except Exception:
            missing_tables.append(table_name)
            print(f"❌ Table '{table_name}' is missing")
    
    if missing_tables:
        print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
        print("\n🔧 Manual setup required:")
        print("1. Open Supabase Dashboard: https://supabase.com/dashboard")
        print("2. Select your project")
        print("3. Go to 'SQL Editor'")
        print("4. Create a new query")
        print("5. Copy and paste the SQL above")
        print("6. Click 'Run'")
        
        # Save SQL to file for convenience
        sql_file_path = Path("sql/fix_missing_tables.sql")
        sql_file_path.parent.mkdir(exist_ok=True)
        
        with open(sql_file_path, 'w') as f:
            f.write(create_tables_sql)
            f.write("\n\n")
            f.write(create_indexes_sql)
            f.write("\n\n")
            f.write(add_comments_sql)
        
        print(f"\n💾 SQL saved to: {sql_file_path}")
        print("   You can also run: psql $DATABASE_URL < sql/fix_missing_tables.sql")
    else:
        print("\n✅ All required tables exist!")
    
    return len(missing_tables) == 0

def verify_database_setup():
    """Verify all required tables exist and have correct structure."""
    
    print("\n🔍 Verifying database setup...")
    
    required_tables = {
        'binance_accounts': ['id', 'account_name', 'api_key', 'api_secret'],
        'benchmark_configs': ['id', 'account_id', 'btc_units', 'eth_units'],
        'nav_history': ['id', 'account_id', 'timestamp', 'nav', 'benchmark_value'],
        'processed_transactions': ['id', 'account_id', 'transaction_id', 'amount'],
        'account_processing_status': ['account_id', 'last_processed_timestamp'],
        'price_history': ['id', 'timestamp', 'asset', 'price'],
        'system_logs': ['id', 'timestamp', 'level', 'category', 'message']
    }
    
    supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
    
    all_good = True
    
    for table_name, required_columns in required_tables.items():
        try:
            # Try to query the table
            result = supabase.table(table_name).select('*').limit(1).execute()
            print(f"✅ Table '{table_name}' exists")
            
            # If we got data, check columns
            if result.data and len(result.data) > 0:
                sample_row = result.data[0]
                for column in required_columns:
                    if column not in sample_row:
                        print(f"   ⚠️  Missing column '{column}'")
                        all_good = False
                        
        except Exception as e:
            print(f"❌ Table '{table_name}' is missing or inaccessible: {str(e)}")
            all_good = False
    
    return all_good

def main():
    """Main function to fix database issues."""
    print("🗄️  Binance Portfolio Monitor - Database Fix")
    print("=" * 60)
    
    # Validate configuration
    try:
        settings.validate()
        print("✅ Configuration valid")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return
    
    # Create missing tables
    tables_created = create_missing_tables()
    
    # Verify setup
    setup_valid = verify_database_setup()
    
    if tables_created and setup_valid:
        print("\n🎉 Database setup complete!")
        print("✅ All required tables are present")
        print("✅ Transaction processing should now work correctly")
    else:
        print("\n⚠️  Database setup incomplete")
        print("Please follow the manual steps above to complete setup")
        
    print("\n📖 Next steps:")
    print("1. If tables were missing, run the SQL in Supabase Dashboard")
    print("2. Run 'python api/index.py' to test transaction processing")
    print("3. Check logs for any remaining errors")

if __name__ == "__main__":
    main()