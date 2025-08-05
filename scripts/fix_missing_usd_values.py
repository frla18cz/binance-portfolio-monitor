#!/usr/bin/env python3
"""
Fix missing USD values for sub-account transfers
Updates transactions that have null usd_value in metadata
"""

import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from binance.client import Client as BinanceClient
from api.logger import MonitorLogger, LogCategory
from utils.database_manager import get_supabase_client
from api.index import get_coin_usd_value

# Create logger instance
logger = MonitorLogger()

def main():
    """Main function to fix missing USD values"""
    db_client = get_supabase_client()
    
    # Create Binance client for price fetching
    binance_client = BinanceClient('', '')
    binance_client.API_URL = 'https://data-api.binance.vision/api'
    
    print("🔍 Looking for transactions with missing USD values...")
    
    # Find all transactions with missing USD values
    response = db_client.table('processed_transactions')\
        .select('*, binance_accounts!inner(account_name)')\
        .or_('metadata->usd_value.is.null,metadata->price_missing.eq.true')\
        .execute()
    
    if not response.data:
        print("✅ No transactions with missing USD values found!")
        return
        
    transactions = response.data
    print(f"\n📊 Found {len(transactions)} transactions with missing USD values")
    
    # Group by coin for efficiency
    by_coin = {}
    for txn in transactions:
        coin = txn.get('metadata', {}).get('coin', 'UNKNOWN')
        if coin not in by_coin:
            by_coin[coin] = []
        by_coin[coin].append(txn)
    
    # Process each coin
    updated_count = 0
    failed_count = 0
    
    for coin, coin_txns in by_coin.items():
        print(f"\n💰 Processing {len(coin_txns)} {coin} transactions...")
        
        # Get current price once for all transactions of this coin
        # Note: This uses current price, not historical price
        if coin and coin != 'UNKNOWN':
            # For demonstration, we'll use current prices
            # In production, you might want to use historical price APIs
            usd_value, coin_price, price_source = get_coin_usd_value(
                binance_client, coin, 1.0, logger=logger
            )
            
            if coin_price:
                print(f"   Current {coin} price: ${coin_price:.2f} (via {price_source})")
                
                for txn in coin_txns:
                    amount = float(txn['amount'])
                    txn_usd_value = amount * coin_price
                    
                    # Update metadata
                    metadata = txn.get('metadata', {})
                    metadata['usd_value'] = txn_usd_value
                    metadata['coin_price'] = coin_price
                    metadata['price_source'] = price_source
                    metadata['price_missing'] = False
                    metadata['price_updated_at'] = datetime.now(timezone.utc).isoformat()
                    
                    # Update in database
                    update_response = db_client.table('processed_transactions')\
                        .update({'metadata': metadata})\
                        .eq('id', txn['id'])\
                        .execute()
                    
                    if update_response.data:
                        account_name = txn['binance_accounts']['account_name']
                        print(f"   ✅ Updated: {txn['transaction_id']} - {amount} {coin} = ${txn_usd_value:.2f} ({account_name})")
                        updated_count += 1
                    else:
                        print(f"   ❌ Failed to update: {txn['transaction_id']}")
                        failed_count += 1
            else:
                print(f"   ⚠️ Could not get price for {coin}")
                failed_count += len(coin_txns)
        else:
            print(f"   ⚠️ Skipping unknown coin")
            failed_count += len(coin_txns)
    
    print(f"\n📈 Summary:")
    print(f"   ✅ Successfully updated: {updated_count} transactions")
    print(f"   ❌ Failed to update: {failed_count} transactions")
    print(f"   📊 Total processed: {len(transactions)} transactions")
    
    # Show sample of updated transactions
    if updated_count > 0:
        print(f"\n🔍 Verifying updates...")
        verify_response = db_client.table('processed_transactions')\
            .select('transaction_id, type, amount, metadata, binance_accounts!inner(account_name)')\
            .like('transaction_id', 'SUB_%')\
            .not_('metadata->usd_value', 'is', None)\
            .limit(5)\
            .execute()
        
        if verify_response.data:
            print(f"\n📋 Sample of updated transactions:")
            for txn in verify_response.data:
                metadata = txn.get('metadata', {})
                print(f"   - {txn['transaction_id']}: {txn['amount']} {metadata.get('coin')} = ${metadata.get('usd_value', 0):.2f} ({txn['binance_accounts']['account_name']})")

if __name__ == "__main__":
    main()