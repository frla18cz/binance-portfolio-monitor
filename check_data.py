#!/usr/bin/env python3
"""
Database Check Script - Zkontroluje stav databáze a poslední data
"""

import os
import sys
from datetime import datetime, UTC
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
load_dotenv()

def main():
    """Check database state and recent data."""
    try:
        from supabase import create_client
        
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ SUPABASE_URL or SUPABASE_ANON_KEY not found in environment")
            return
        
        supabase = create_client(supabase_url, supabase_key)
        
        print("📊 Database Status Check")
        print("=" * 50)
        
        # Check accounts
        accounts = supabase.table('binance_accounts').select('*').execute()
        print(f"💼 Accounts: {len(accounts.data)}")
        for acc in accounts.data:
            print(f"   - {acc['account_name']} (ID: {acc['id']})")
        
        # Check recent NAV history
        nav_history = supabase.table('nav_history').select('*').order('timestamp', desc=True).limit(10).execute()
        print(f"\n📈 Recent NAV History ({len(nav_history.data)} records):")
        for row in nav_history.data:
            nav = float(row['nav'])
            benchmark = float(row['benchmark_value'])
            vs_benchmark = nav - benchmark
            vs_pct = (vs_benchmark / benchmark * 100) if benchmark > 0 else 0
            timestamp = row['timestamp'][:19]  # Remove microseconds
            print(f"   {timestamp}: NAV=${nav:,.2f} | Benchmark=${benchmark:,.2f} | vs Benchmark: ${vs_benchmark:+,.2f} ({vs_pct:+.2f}%)")
        
        # Check benchmark configs
        configs = supabase.table('benchmark_configs').select('*').execute()
        print(f"\n⚙️  Benchmark Configs: {len(configs.data)}")
        for config in configs.data:
            print(f"   - Account ID: {config['account_id']}")
            print(f"     BTC Units: {config.get('btc_units', 0):.6f}")
            print(f"     ETH Units: {config.get('eth_units', 0):.6f}")
            next_rebalance = config.get('next_rebalance_timestamp')
            if next_rebalance:
                print(f"     Next Rebalance: {next_rebalance}")
        
        # Check processed transactions (if table exists)
        try:
            transactions = supabase.table('processed_transactions').select('*').order('timestamp', desc=True).limit(5).execute()
            print(f"\n💰 Recent Transactions: {len(transactions.data)}")
            for txn in transactions.data:
                print(f"   - {txn['transaction_type']}: ${txn['amount']:.2f} at {txn['timestamp'][:19]}")
        except Exception as e:
            if 'does not exist' in str(e):
                print(f"\n💰 Recent Transactions: Table not found (this is normal for new setups)")
            else:
                print(f"\n💰 Recent Transactions: Error - {e}")
        
        print("\n✅ Database check completed!")
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()