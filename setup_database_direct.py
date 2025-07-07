#!/usr/bin/env python3
"""
Database Setup Script - Vytvoří tabulku přes Supabase REST API
"""

import os
import sys
import requests
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from config import settings

def create_system_logs_table_via_api():
    """Pokusí se vytvořit tabulku pomocí Supabase REST API."""
    
    print("🔧 Zkouším vytvořit tabulku přes REST API...")
    
    # Supabase REST API endpoint
    base_url = settings.database.supabase_url
    api_key = settings.database.supabase_key
    
    headers = {
        'apikey': api_key,
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Try to create a test record first to see if we can access the table
    test_url = f"{base_url}/rest/v1/system_logs"
    
    try:
        # Try to query the table (this will fail if table doesn't exist)
        response = requests.get(f"{test_url}?limit=1", headers=headers)
        
        if response.status_code == 200:
            print("✅ Tabulka system_logs již existuje!")
            return True
        elif response.status_code == 404:
            print("❌ Tabulka system_logs neexistuje")
        else:
            print(f"⚠️  Neočekávaná odpověď: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Chyba při kontrole tabulky: {e}")
    
    # REST API obvykle neumožňuje CREATE TABLE
    print("❌ REST API neumožňuje vytváření tabulek")
    return False

def create_table_with_curl():
    """Vygeneruje curl příkaz pro vytvoření tabulky."""
    
    sql_content = """
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

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_category ON system_logs(category);
CREATE INDEX IF NOT EXISTS idx_system_logs_account_id ON system_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_session_id ON system_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_system_logs_recent ON system_logs(created_at DESC, level, category);
"""
    
    print("\n" + "="*60)
    print("📋 SQL pro vytvoření tabulky:")
    print("="*60)
    print(sql_content)
    print("="*60)
    
    return sql_content

def test_database_connection():
    """Otestuje připojení k databázi."""
    
    print("🔍 Testuji připojení k Supabase...")
    
    try:
        from supabase import create_client
        supabase = create_client(settings.database.supabase_url, settings.database.supabase_key)
        
        # Try to query existing tables
        try:
            # Query nav_history table (should exist)
            result = supabase.table('nav_history').select('count').limit(1).execute()
            print("✅ Připojení k databázi funguje")
            print(f"✅ Tabulka nav_history existuje")
            return True
        except Exception as e:
            print(f"⚠️  Problém s dotazem: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Chyba připojení: {e}")
        return False

def main():
    """Hlavní funkce."""
    print("🗄️  Binance Portfolio Monitor - Direct Database Setup")
    print("=" * 60)
    
    # Test database connection
    if not test_database_connection():
        print("❌ Nelze se připojit k databázi")
        return
    
    # Try API approach
    if create_system_logs_table_via_api():
        print("🎉 Tabulka je připravena!")
        return
    
    # Generate SQL for manual execution
    print("\n🔧 Automatické vytvoření se nezdařilo")
    print("📋 Použijte tento SQL v Supabase Dashboard:")
    
    sql = create_table_with_curl()
    
    print("\n📖 Instrukce:")
    print("1. Otevřete https://supabase.com/dashboard")
    print("2. Vyberte váš projekt")
    print("3. Jděte do 'SQL Editor'")
    print("4. Vytvořte nový query")
    print("5. Vložte SQL kód výše")
    print("6. Klikněte 'Run'")
    
    print("\n✅ Po vytvoření tabulky bude logging fungovat automaticky!")

if __name__ == "__main__":
    main()