#!/usr/bin/env python3
"""
Script to fix metadata for existing BTC deposits
"""

import os
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.database_manager import get_supabase_client

def fix_deposit_metadata():
    """Fix metadata for existing deposits"""
    try:
        supabase = get_supabase_client()
        
        # Get the two specific BTC deposits
        deposits = supabase.table('processed_transactions')\
            .select('*')\
            .in_('transaction_id', [
                'DEP_c231bf4c64fea15e1cabfe920e40a70245c035768bc89ca666f7846f80b1f80b',
                'DEP_3f27985f16e76a399bc1ec00d224e296437fc7805c9663399ceea98f515742c6'
            ])\
            .execute()
        
        if not deposits.data:
            print("❌ Deposits not found")
            return
            
        print(f"✅ Found {len(deposits.data)} deposits to fix")
        
        # BTC price around July 25, 2025 was approximately 116,500 USD
        # We'll use this for the historical metadata fix
        btc_price = 116500.0
        
        for deposit in deposits.data:
            amount_btc = float(deposit['amount'])
            usd_value = amount_btc * btc_price
            
            # Create metadata
            metadata = {
                'coin': 'BTC',
                'network': 'BTC',
                'usd_value': usd_value,
                'coin_price': btc_price,
                'tx_id': deposit['transaction_id'].replace('DEP_', ''),
                'fixed_by_script': True,
                'fixed_at': datetime.utcnow().isoformat()
            }
            
            print(f"\n📝 Updating deposit: {deposit['transaction_id']}")
            print(f"   Amount: {amount_btc} BTC")
            print(f"   USD Value: ${usd_value:,.2f}")
            print(f"   Price Used: ${btc_price:,.2f}")
            
            # Update the deposit with metadata
            result = supabase.table('processed_transactions')\
                .update({'metadata': metadata})\
                .eq('transaction_id', deposit['transaction_id'])\
                .execute()
            
            if result.data:
                print(f"   ✅ Successfully updated metadata")
            else:
                print(f"   ❌ Failed to update metadata")
        
        # Verify the updates
        print("\n🔍 Verifying updates...")
        updated = supabase.table('processed_transactions')\
            .select('transaction_id, amount, metadata')\
            .in_('transaction_id', [
                'DEP_c231bf4c64fea15e1cabfe920e40a70245c035768bc89ca666f7846f80b1f80b',
                'DEP_3f27985f16e76a399bc1ec00d224e296437fc7805c9663399ceea98f515742c6'
            ])\
            .execute()
        
        for dep in updated.data:
            print(f"\n✅ {dep['transaction_id']}")
            print(f"   Amount: {dep['amount']} BTC")
            if dep['metadata']:
                print(f"   USD Value: ${dep['metadata']['usd_value']:,.2f}")
                print(f"   Coin: {dep['metadata']['coin']}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 Fixing Deposit Metadata")
    print("=" * 80)
    fix_deposit_metadata()