#!/usr/bin/env python3
"""
Script to update deposits that have missing prices
"""

import os
import sys
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from binance.client import Client
from utils.database_manager import get_supabase_client
from api.index import get_coin_usd_value, get_prices
from api.logger import get_logger

def update_missing_prices():
    """Update deposits with missing prices"""
    logger = get_logger()
    
    try:
        supabase = get_supabase_client()
        
        # Find deposits with missing prices
        print("🔍 Finding deposits with missing prices...")
        
        # Query for deposits where metadata indicates price_missing or no usd_value
        query = supabase.table('processed_transactions')\
            .select('*')\
            .eq('type', 'DEPOSIT')
        
        result = query.execute()
        
        if not result.data:
            print("✅ No deposits found")
            return
        
        # Filter for deposits with missing prices
        deposits_missing_price = []
        for txn in result.data:
            metadata = txn.get('metadata', {})
            if metadata:
                # Check if price is missing
                if metadata.get('price_missing') or metadata.get('usd_value') is None:
                    deposits_missing_price.append(txn)
            elif txn['amount']:  # Old deposits without metadata
                deposits_missing_price.append(txn)
        
        if not deposits_missing_price:
            print("✅ All deposits have prices")
            return
        
        print(f"⚠️  Found {len(deposits_missing_price)} deposits with missing prices")
        
        # Create client for price fetching
        client = Client('', '')
        client.API_URL = 'https://data-api.binance.vision/api'
        
        # Get current prices
        print("\n📊 Fetching current prices...")
        prices = get_prices(client, logger)
        btc_price = prices.get('BTCUSDT') if prices else None
        
        if not btc_price:
            print("❌ Failed to fetch BTC price")
            return
        
        print(f"✅ BTC Price: ${btc_price:,.2f}")
        
        # Update each deposit
        updated_count = 0
        failed_count = 0
        
        print(f"\n🔄 Updating {len(deposits_missing_price)} deposits...")
        
        for deposit in deposits_missing_price:
            metadata = deposit.get('metadata', {})
            coin = metadata.get('coin', '')
            amount = float(deposit['amount'])
            
            if not coin:
                print(f"\n⚠️  Skipping {deposit['transaction_id']} - no coin info")
                failed_count += 1
                continue
            
            print(f"\n📝 Updating: {deposit['transaction_id']}")
            print(f"   Coin: {coin}")
            print(f"   Amount: {amount}")
            
            # Get USD value
            usd_value, coin_price, price_source = get_coin_usd_value(
                client, coin, amount, btc_price, logger
            )
            
            if usd_value is not None:
                # Update metadata
                new_metadata = metadata.copy()
                new_metadata.update({
                    'usd_value': usd_value,
                    'coin_price': coin_price,
                    'price_source': price_source,
                    'price_missing': False,
                    'price_updated_at': datetime.now(timezone.utc).isoformat(),
                    'price_updated_by': 'update_missing_prices_script'
                })
                
                # Update in database
                update_result = supabase.table('processed_transactions')\
                    .update({'metadata': new_metadata})\
                    .eq('id', deposit['id'])\
                    .execute()
                
                if update_result.data:
                    print(f"   ✅ Updated: ${usd_value:,.2f} @ ${coin_price:,.6f} ({price_source})")
                    updated_count += 1
                else:
                    print(f"   ❌ Failed to update database")
                    failed_count += 1
            else:
                print(f"   ❌ Still cannot determine price for {coin}")
                failed_count += 1
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"✅ Successfully updated: {updated_count}")
        print(f"❌ Failed to update: {failed_count}")
        print(f"📊 Total processed: {len(deposits_missing_price)}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("💰 Update Missing Deposit Prices")
    print("=" * 80)
    update_missing_prices()