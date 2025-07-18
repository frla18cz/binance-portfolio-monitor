#!/usr/bin/env python3
"""
Test CCXT withdrawal detection specifically for the user's case
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.database_manager import get_supabase_client

def test_ccxt_withdrawal_detection():
    """Test CCXT withdrawal detection for Ondra(test) account"""
    print("=" * 60)
    print("Testing CCXT Withdrawal Detection")
    print("=" * 60)
    
    try:
        # Import CCXT
        import ccxt
        print("✅ CCXT library imported successfully")
        
        # Get Ondra(test) account
        supabase = get_supabase_client()
        accounts = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
        
        if not accounts.data:
            print("❌ Ondra(test) account not found")
            return
            
        account = accounts.data[0]
        print(f"✅ Found account: {account['account_name']}")
        
        # Initialize CCXT exchange
        exchange = ccxt.binance({
            'apiKey': account['api_key'],
            'secret': account['api_secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
        print("✅ CCXT Binance exchange initialized")
        
        # Check last 7 days for withdrawals
        since = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000)
        
        print(f"\n📤 Fetching withdrawals from last 7 days...")
        try:
            withdrawals = exchange.fetch_withdrawals(since=since)
            print(f"✅ CCXT successfully fetched {len(withdrawals)} withdrawals")
            
            if withdrawals:
                print("\n🔍 Withdrawal details:")
                for i, w in enumerate(withdrawals):
                    print(f"\n--- Withdrawal {i+1} ---")
                    print(f"ID: {w.get('id')}")
                    print(f"Amount: {w.get('amount')} {w.get('currency')}")
                    print(f"Status: {w.get('status')}")
                    print(f"Timestamp: {datetime.fromtimestamp(w.get('timestamp', 0)/1000, timezone.utc).isoformat()}")
                    
                    # Check original Binance data
                    info = w.get('info', {})
                    if info:
                        print(f"Transfer Type: {info.get('transferType')} (0=external, 1=internal)")
                        print(f"Network: {info.get('network', 'N/A')}")
                        print(f"Address: {info.get('address', 'N/A')}")
                        print(f"TX ID: {info.get('txId', 'N/A')}")
                        
                        # Check if internal transfer
                        if info.get('transferType') == 1 or 'Internal' in str(info.get('txId', '')):
                            print("🔄 THIS IS AN INTERNAL TRANSFER!")
            else:
                print("\n⚠️ No withdrawals found in the last 7 days")
                
        except Exception as e:
            print(f"\n❌ Error fetching withdrawals: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            
            # Check if it's a permission error
            if 'permissions' in str(e).lower() or 'not allowed' in str(e).lower():
                print("\n⚠️ This might be a permission issue, but CCXT should work with read-only!")
                
        # Also check deposits for comparison
        print(f"\n📥 Fetching deposits from last 7 days...")
        try:
            deposits = exchange.fetch_deposits(since=since)
            print(f"✅ CCXT successfully fetched {len(deposits)} deposits")
        except Exception as e:
            print(f"❌ Error fetching deposits: {str(e)}")
            
    except ImportError:
        print("❌ CCXT library not installed")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ccxt_withdrawal_detection()