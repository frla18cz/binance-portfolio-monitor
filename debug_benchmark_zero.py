#!/usr/bin/env python3
"""
Debug why benchmark value is showing as 0
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from utils.database_manager import get_supabase_client
from api.index import calculate_benchmark_value, process_single_account

load_dotenv()

# Get the accounts
db_client = get_supabase_client()
accounts = db_client.table('binance_accounts').select('*, benchmark_configs(*)').in_(
    'account_name', ['Ondra(test)', 'ondra_osobni_sub_acc1']
).execute()

if not accounts.data:
    print("No accounts found!")
    exit(1)

# Get current prices
from binance.client import Client
temp_client = Client("", "")  # Public API doesn't need keys
prices = {
    'BTCUSDT': float(temp_client.get_symbol_ticker(symbol='BTCUSDT')['price']),
    'ETHUSDT': float(temp_client.get_symbol_ticker(symbol='ETHUSDT')['price'])
}

print(f"Current prices: BTC=${prices['BTCUSDT']:,.2f}, ETH=${prices['ETHUSDT']:,.2f}")
print("=" * 60)

for account in accounts.data:
    print(f"\nAccount: {account['account_name']}")
    config = account.get('benchmark_configs')
    
    if not config:
        print("  No benchmark config!")
        continue
        
    print(f"  Config type: {type(config)}")
    print(f"  BTC units: {config.get('btc_units')}")
    print(f"  ETH units: {config.get('eth_units')}")
    
    # Calculate benchmark manually
    btc_val = float(config.get('btc_units', 0)) * prices['BTCUSDT']
    eth_val = float(config.get('eth_units', 0)) * prices['ETHUSDT']
    manual_benchmark = btc_val + eth_val
    print(f"  Manual benchmark calculation: ${manual_benchmark:.2f}")
    
    # Use the function from api.index
    func_benchmark = calculate_benchmark_value(config, prices)
    print(f"  Function benchmark value: ${func_benchmark:.2f}")
    
    # Try processing the account
    print(f"\n  Processing account {account['account_name']}...")
    try:
        process_single_account(account, prices)
        print("  ✓ Processing completed")
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("Checking latest NAV history...")

# Check the latest NAV history
nav_history = db_client.table('nav_history').select('*').in_(
    'account_name', ['Ondra(test)', 'ondra_osobni_sub_acc1']
).order('timestamp', desc=True).limit(4).execute()

for record in nav_history.data:
    print(f"\n{record['account_name']} at {record['timestamp'][:19]}")
    print(f"  NAV: ${float(record['nav']):.2f}")
    print(f"  Benchmark: ${float(record['benchmark_value']):.2f}")
    print(f"  BTC price: ${float(record['btc_price']):.2f}")
    print(f"  ETH price: ${float(record['eth_price']):.2f}")