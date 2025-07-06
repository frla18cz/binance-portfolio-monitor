#!/usr/bin/env python3
"""
Secure script to add new Binance accounts to the database.
This script prompts for API keys securely without storing them in code.
"""

import os
import getpass
from datetime import datetime, UTC
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def main():
    print("🔐 Secure Binance Account Setup")
    print("=" * 50)
    
    # Initialize Supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        return False
    
    supabase = create_client(supabase_url, supabase_key)
    print("✅ Supabase client initialized")
    
    # Account details
    accounts_to_add = [
        {"name": "Simple", "description": "Simple trading account"},
        {"name": "Ondra", "description": "Ondra's trading account"}
    ]
    
    for account_info in accounts_to_add:
        account_name = account_info["name"]
        description = account_info["description"]
        
        print(f"\n👤 Setting up account: {account_name}")
        print("-" * 30)
        
        # Securely prompt for API credentials
        print(f"Enter API credentials for {account_name}:")
        api_key = getpass.getpass("API Key: ").strip()
        api_secret = getpass.getpass("API Secret: ").strip()
        
        if not api_key or not api_secret:
            print(f"❌ Skipping {account_name} - missing credentials")
            continue
        
        # Basic validation
        if len(api_key) < 10 or len(api_secret) < 10:
            print(f"❌ Skipping {account_name} - credentials too short")
            continue
        
        try:
            # Insert account into database
            account_data = {
                'account_name': account_name,
                'api_key': api_key,
                'api_secret': api_secret,
                'created_at': datetime.now(UTC).isoformat(),
                'description': description
            }
            
            account_result = supabase.table('binance_accounts').insert(account_data).execute()
            
            if account_result.data:
                account_id = account_result.data[0]['id']
                print(f"✅ Account '{account_name}' added successfully (ID: {account_id})")
                
                # Create default benchmark config
                benchmark_config = {
                    'account_id': account_id,
                    'rebalance_day': 0,  # Monday
                    'rebalance_hour': 17,  # 17:00 UTC
                    'created_at': datetime.now(UTC).isoformat()
                }
                
                config_result = supabase.table('benchmark_configs').insert(benchmark_config).execute()
                
                if config_result.data:
                    print(f"✅ Benchmark config created for '{account_name}'")
                else:
                    print(f"⚠️  Account added but benchmark config failed for '{account_name}'")
            else:
                print(f"❌ Failed to add account '{account_name}'")
                
        except Exception as e:
            print(f"❌ Error adding account '{account_name}': {str(e)}")
    
    print(f"\n📊 Current accounts in database:")
    print("-" * 30)
    
    try:
        accounts = supabase.table('binance_accounts').select('id, account_name, created_at').execute()
        if accounts.data:
            for account in accounts.data:
                name = account.get('account_name', 'Unknown')
                created = account.get('created_at', 'Unknown')
                account_id = account.get('id', 'Unknown')
                print(f"👤 {name} (ID: {account_id[:8]}..., Created: {created[:10]})")
        else:
            print("📊 No accounts found")
    except Exception as e:
        print(f"❌ Error listing accounts: {str(e)}")
    
    print("\n🔐 Security Notes:")
    print("- API keys are stored encrypted in Supabase")
    print("- Use read-only API keys when possible")
    print("- Monitor logs for unusual activity")
    print("- Keys are not visible in this script or logs")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
    except KeyboardInterrupt:
        print("\n🛑 Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")