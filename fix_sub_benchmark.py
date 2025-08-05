#!/usr/bin/env python3
"""
Fix benchmark adjustments for SUB transactions that were not processed
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from utils.database_manager import get_supabase_client
from api.index import adjust_benchmark_for_cashflow
from api.logger import get_logger
from datetime import datetime

load_dotenv()

# Get database client
db_client = get_supabase_client()
logger = get_logger()

# Get the master account
account_result = db_client.table('binance_accounts').select('*, benchmark_configs(*)').eq(
    'account_name', 'Ondra(test)'
).execute()

if not account_result.data:
    print("Account not found!")
    exit(1)

account = account_result.data[0]
account_id = account['id']
config = account.get('benchmark_configs')

if not config:
    print("No benchmark config found!")
    exit(1)

print(f"\n=== Fixing Benchmark for SUB Transactions ===")
print(f"Account: {account['account_name']}")
print(f"Current BTC units: {config['btc_units']}")
print(f"Current ETH units: {config['eth_units']}")

# Get recent prices
price_result = db_client.table('price_history').select('btc_price, eth_price').order(
    'timestamp', desc=True
).limit(1).execute()

if not price_result.data:
    print("No price history found!")
    exit(1)

prices = {
    'BTCUSDT': float(price_result.data[0]['btc_price']),
    'ETHUSDT': float(price_result.data[0]['eth_price'])
}

print(f"\nCurrent prices: BTC=${prices['BTCUSDT']:,.2f}, ETH=${prices['ETHUSDT']:,.2f}")

# Get the SUB transactions that need benchmark adjustment
sub_txns = db_client.table('processed_transactions').select('*').eq(
    'account_id', account_id
).like('transaction_id', 'SUB_%').order('timestamp', desc=True).execute()

if not sub_txns.data:
    print("No SUB transactions found!")
    exit(1)

# Check which ones already have benchmark modifications
existing_mods = db_client.table('benchmark_modifications').select('transaction_id').eq(
    'account_id', account_id
).like('transaction_id', 'SUB_%').execute()

existing_mod_ids = {mod['transaction_id'] for mod in existing_mods.data}

# Process only the ones without modifications
for txn in sub_txns.data:
    if txn['transaction_id'] in existing_mod_ids:
        print(f"\nSkipping {txn['transaction_id']} - already has benchmark modification")
        continue
    
    # Calculate cashflow
    amount = float(txn['amount'])
    if txn['type'] == 'SUB_DEPOSIT':
        cashflow = amount
    elif txn['type'] == 'SUB_WITHDRAWAL':
        cashflow = -amount
    else:
        continue
    
    print(f"\nProcessing {txn['transaction_id']}:")
    print(f"  Type: {txn['type']}")
    print(f"  Amount: ${amount:.2f}")
    print(f"  Cashflow: ${cashflow:+.2f}")
    
    # Create the transaction object in the format expected by adjust_benchmark_for_cashflow
    transaction = {
        'id': txn['transaction_id'],
        'type': txn['type'].replace('SUB_', ''),  # Convert SUB_DEPOSIT to DEPOSIT
        'amount': amount,
        'timestamp': int(datetime.fromisoformat(txn['timestamp'].replace('Z', '+00:00')).timestamp() * 1000),
        'metadata': txn.get('metadata', {})
    }
    
    # Adjust benchmark
    print(f"  Adjusting benchmark...")
    updated_config = adjust_benchmark_for_cashflow(
        db_client, config, account_id, cashflow, prices, 
        [transaction], logger
    )
    
    if updated_config:
        config = updated_config  # Update for next iteration
        print(f"  ✓ Benchmark adjusted successfully")
        print(f"    New BTC units: {config['btc_units']}")
        print(f"    New ETH units: {config['eth_units']}")
    else:
        print(f"  ✗ Failed to adjust benchmark")

print("\n=== Fix Complete ===")