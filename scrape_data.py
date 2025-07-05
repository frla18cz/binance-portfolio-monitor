#!/usr/bin/env python3
"""
Data Scraping Script - Jen sbírá data z Binance API a ukládá do databáze
Použijte pro pravidelné krmení databáze daty bez dashboardu.
"""

import os
import sys
from datetime import datetime, UTC

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Live mode only

def main():
    """Main data scraping execution."""
    
    print(f"📊 Data Scraping Mode: LIVE")
    print(f"🕐 Started at: {datetime.now(UTC).isoformat()}")
    print("🔴 Running in LIVE mode - using real Binance API")
    
    try:
        # Import and run the main processing function
        from api.index import process_all_accounts
        process_all_accounts()
        
        print("✅ Data scraping completed successfully!")
        print(f"🕐 Finished at: {datetime.now(UTC).isoformat()}")
        
    except Exception as e:
        print(f"❌ Data scraping failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()