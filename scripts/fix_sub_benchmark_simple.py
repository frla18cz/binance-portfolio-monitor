#!/usr/bin/env python3
"""
Fix benchmark adjustments for SUB transactions that were not processed
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from utils.database_manager import get_supabase_client
from datetime import datetime

load_dotenv()

# Get database client
db_client = get_supabase_client()

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
    'BTC': float(price_result.data[0]['btc_price']),
    'ETH': float(price_result.data[0]['eth_price'])
}

print(f"\nCurrent prices: BTC=${prices['BTC']:,.2f}, ETH=${prices['ETH']:,.2f}")

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

# Start with current units
btc_units = float(config['btc_units'])
eth_units = float(config['eth_units'])

# Process transactions in chronological order
transactions_to_process = []
for txn in reversed(sub_txns.data):  # Reverse to get chronological order
    if txn['transaction_id'] not in existing_mod_ids:
        transactions_to_process.append(txn)

if not transactions_to_process:
    print("\nAll SUB transactions already have benchmark modifications!")
    exit(0)

print(f"\nFound {len(transactions_to_process)} SUB transactions without benchmark modifications")

# Process each transaction
for txn in transactions_to_process:
    # Calculate cashflow
    amount = float(txn['amount'])
    if txn['type'] == 'SUB_DEPOSIT':
        cashflow = amount
        mod_type = 'deposit'
    elif txn['type'] == 'SUB_WITHDRAWAL':
        cashflow = -amount
        mod_type = 'withdrawal'
    else:
        continue
    
    print(f"\nProcessing {txn['transaction_id']}:")
    print(f"  Type: {txn['type']}")
    print(f"  Amount: ${amount:.2f}")
    print(f"  Cashflow: ${cashflow:+.2f}")
    
    # Calculate new units
    btc_allocation = cashflow * 0.5  # 50% to BTC
    eth_allocation = cashflow * 0.5  # 50% to ETH
    
    btc_units_bought = btc_allocation / prices['BTC'] if cashflow > 0 else 0
    eth_units_bought = eth_allocation / prices['ETH'] if cashflow > 0 else 0
    
    # For withdrawals, calculate proportional reduction
    if cashflow < 0:
        total_value = btc_units * prices['BTC'] + eth_units * prices['ETH']
        if total_value > 0:
            withdrawal_ratio = abs(cashflow) / total_value
            btc_units_bought = -btc_units * withdrawal_ratio
            eth_units_bought = -eth_units * withdrawal_ratio
    
    new_btc_units = btc_units + btc_units_bought
    new_eth_units = eth_units + eth_units_bought
    
    # Create benchmark modification record
    modification = {
        'account_id': account_id,
        'account_name': account['account_name'],
        'modification_timestamp': txn['timestamp'],
        'modification_type': mod_type,
        'btc_units_before': btc_units,
        'eth_units_before': eth_units,
        'cashflow_amount': abs(cashflow),
        'btc_price': prices['BTC'],
        'eth_price': prices['ETH'],
        'btc_allocation': btc_allocation if cashflow > 0 else None,
        'eth_allocation': eth_allocation if cashflow > 0 else None,
        'btc_units_bought': btc_units_bought,
        'eth_units_bought': eth_units_bought,
        'btc_units_after': new_btc_units,
        'eth_units_after': new_eth_units,
        'transaction_id': txn['transaction_id'],
        'transaction_type': txn['type']
    }
    
    # Insert the modification
    result = db_client.table('benchmark_modifications').insert(modification).execute()
    if result.data:
        print(f"  ✓ Benchmark modification created")
        print(f"    BTC: {btc_units:.9f} -> {new_btc_units:.9f} ({btc_units_bought:+.9f})")
        print(f"    ETH: {eth_units:.9f} -> {new_eth_units:.9f} ({eth_units_bought:+.9f})")
        
        # Update for next iteration
        btc_units = new_btc_units
        eth_units = new_eth_units
    else:
        print(f"  ✗ Failed to create benchmark modification")

# Update the benchmark config with final units
update_result = db_client.table('benchmark_configs').update({
    'btc_units': btc_units,
    'eth_units': eth_units,
    'last_modification_type': 'deposit',
    'last_modification_timestamp': transactions_to_process[-1]['timestamp'],
    'last_modification_amount': float(transactions_to_process[-1]['amount'])
}).eq('account_id', account_id).execute()

if update_result.data:
    print(f"\n✓ Benchmark config updated successfully")
    print(f"  Final BTC units: {btc_units:.9f}")
    print(f"  Final ETH units: {eth_units:.9f}")
else:
    print(f"\n✗ Failed to update benchmark config")

print("\n=== Fix Complete ===")