#!/usr/bin/env python3
"""
Live Mode Runner - Runs the Binance Portfolio Monitor in LIVE MODE
⚠️ WARNING: This connects to real Binance API and monitors real accounts!
"""

import os
import sys
from datetime import datetime, UTC

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from api.index import process_all_accounts


def print_live_warning():
    """Print a clear warning about live mode."""
    print("\n" + "🔴" * 30)
    print("⚠️  LIVE MODE - REAL ACCOUNT MONITORING ⚠️")
    print("🔴" * 30)
    print("• This will connect to real Binance API")
    print("• This will monitor your real account balance")
    print("• This will read real transaction history")
    print("• Make sure you have proper API keys configured")
    print("🔴" * 30)
    print()


def main():
    """Main live mode execution."""
    print_live_warning()
    
    print(f"🔧 Mode: LIVE")
    print(f"💰 Real Money: True")
    print(f"⚠️  Real account monitoring - real money at risk")
    
    print(f"\n🚀 Starting live monitoring at {datetime.now(UTC).isoformat()}")
    print("-" * 60)
    
    try:
        process_all_accounts()
        print("\n✅ Live monitoring process completed successfully!")
    except Exception as e:
        print(f"\n❌ Live monitoring failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🏁 Live monitoring finished at {datetime.now(UTC).isoformat()}")


if __name__ == "__main__":
    main()