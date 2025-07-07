#!/usr/bin/env python3
"""
Database Setup Script - Automaticky vytvoří všechny potřebné tabulky v Supabase
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import settings
from supabase import create_client

def create_system_logs_table():
    """Vytvoří system_logs tabulku v Supabase."""
    
    print("🔧 Připojuji se k Supabase...")
    
    # Create Supabase client
    supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
    
    # SQL for creating system_logs table
    create_table_sql = """
    -- Create system_logs table for storing application logs
    CREATE TABLE IF NOT EXISTS system_logs (
        id BIGSERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        level VARCHAR(20) NOT NULL,
        category VARCHAR(50) NOT NULL,
        account_id INTEGER,
        account_name VARCHAR(255),
        operation VARCHAR(100) NOT NULL,
        message TEXT NOT NULL,
        data JSONB,
        duration_ms DECIMAL(10,2),
        session_id VARCHAR(100) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    
    # SQL for creating indexes
    create_indexes_sql = """
    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
    CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
    CREATE INDEX IF NOT EXISTS idx_system_logs_category ON system_logs(category);
    CREATE INDEX IF NOT EXISTS idx_system_logs_account_id ON system_logs(account_id);
    CREATE INDEX IF NOT EXISTS idx_system_logs_session_id ON system_logs(session_id);
    CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);
    CREATE INDEX IF NOT EXISTS idx_system_logs_recent ON system_logs(created_at DESC, level, category);
    """
    
    # SQL for cleanup function
    cleanup_function_sql = """
    -- Create function to automatically cleanup old logs
    CREATE OR REPLACE FUNCTION cleanup_old_system_logs()
    RETURNS void AS $$
    BEGIN
        DELETE FROM system_logs 
        WHERE created_at < NOW() - INTERVAL '365 days';
    END;
    $$ LANGUAGE plpgsql;
    """
    
    try:
        print("📋 Vytvářím system_logs tabulku...")
        
        # Execute table creation
        result = supabase.rpc('exec_sql', {'sql': create_table_sql})
        print("✅ Tabulka system_logs vytvořena")
        
        # Execute index creation
        print("🔍 Vytvářím indexy...")
        result = supabase.rpc('exec_sql', {'sql': create_indexes_sql})
        print("✅ Indexy vytvořeny")
        
        # Execute cleanup function
        print("🧹 Vytvářím cleanup funkci...")
        result = supabase.rpc('exec_sql', {'sql': cleanup_function_sql})
        print("✅ Cleanup funkce vytvořena")
        
        # Test the table by inserting a sample log
        print("🧪 Testuji tabulku...")
        test_log = {
            'timestamp': '2025-01-07T10:00:00Z',
            'level': 'INFO',
            'category': 'system',
            'operation': 'database_setup',
            'message': 'Database setup completed successfully',
            'session_id': 'setup_test'
        }
        
        result = supabase.table('system_logs').insert(test_log).execute()
        print("✅ Test log vložen úspěšně")
        
        # Clean up test log
        supabase.table('system_logs').delete().eq('session_id', 'setup_test').execute()
        print("🧹 Test log odstraněn")
        
        print("\n🎉 Database setup dokončen úspěšně!")
        print(f"📊 System logy se budou ukládat do tabulky: {settings.logging.database_logging.get('table_name', 'system_logs')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Chyba při vytváření databáze: {e}")
        
        # Fallback: Try using direct SQL execution if RPC doesn't work
        try:
            print("🔄 Zkouším alternativní metodu...")
            
            # Try direct table creation using raw SQL
            from supabase.client import SupabaseException
            
            # This might not work depending on Supabase configuration
            # Some instances don't allow direct SQL execution via Python client
            print("⚠️  Přímé SQL execution nemusí být povoleno")
            print("🔧 Prosím, spusťte SQL manuálně v Supabase Dashboard:")
            print("\n" + "="*60)
            print(create_table_sql)
            print(create_indexes_sql)
            print(cleanup_function_sql)
            print("="*60)
            
            return False
            
        except Exception as e2:
            print(f"❌ Alternativní metoda také selhala: {e2}")
            return False

def check_existing_tables():
    """Zkontroluje existující tabulky."""
    try:
        supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
        
        print("🔍 Kontroluji existující tabulky...")
        
        # Try to query system_logs table to see if it exists
        try:
            result = supabase.table('system_logs').select('count').limit(1).execute()
            print("✅ Tabulka system_logs již existuje")
            return True
        except Exception:
            print("❌ Tabulka system_logs neexistuje")
            return False
            
    except Exception as e:
        print(f"❌ Chyba při kontrole tabulek: {e}")
        return False

def main():
    """Hlavní funkce pro setup databáze."""
    print("🗄️  Binance Portfolio Monitor - Database Setup")
    print("=" * 60)
    
    # Validate configuration
    try:
        settings.validate()
        print("✅ Konfigurace validní")
    except Exception as e:
        print(f"❌ Chyba v konfiguraci: {e}")
        return
    
    # Check if table already exists
    if check_existing_tables():
        print("ℹ️  Database setup už byl proveden")
        
        response = input("🔄 Chcete znovu vytvořit tabulky? (y/N): ")
        if response.lower() != 'y':
            print("⏭️  Přeskakuji setup")
            return
    
    # Create tables
    success = create_system_logs_table()
    
    if success:
        print("\n🎯 Next steps:")
        print("1. Deploy na Vercel")
        print("2. Logy se automaticky ukládají do databáze")
        print("3. Sledovat logy: SELECT * FROM system_logs ORDER BY created_at DESC;")
    else:
        print("\n🔧 Manual setup potřebný:")
        print("1. Otevřete Supabase Dashboard")
        print("2. Jděte do SQL Editor")
        print("3. Spusťte SQL z souboru: sql/create_system_logs_table.sql")

if __name__ == "__main__":
    main()