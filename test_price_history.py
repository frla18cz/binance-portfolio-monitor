#!/usr/bin/env python3
"""
Test the new price_history implementation.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, UTC

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.index import save_price_history
from config.settings import Settings
from utils.database_logger import DatabaseLogger
from supabase import create_client

def test_price_history():
    """Test saving prices to the new price_history table."""
    # Initialize settings and logger
    settings = Settings()
    
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        return False
    
    # Create Supabase client
    supabase = create_client(supabase_url, supabase_key)
    
    # Create logger (optional)
    logger = DatabaseLogger(supabase, "test_price_history")
    
    print("Testing new price_history implementation...")
    print()
    
    # Test data - simulate prices from Binance API
    test_prices = {
        'BTCUSDT': '98765.43',
        'ETHUSDT': '3456.78',
        'BNBUSDT': '234.56'  # This should be ignored
    }
    
    print(f"Test prices: {test_prices}")
    print()
    
    # Test saving prices
    print("Calling save_price_history()...")
    save_price_history(test_prices, logger)
    
    # Try to read the saved data
    try:
        print("\nQuerying price_history table...")
        result = supabase.table('price_history').select('*').order('timestamp', desc=True).limit(5).execute()
        
        if result.data:
            print(f"\nFound {len(result.data)} records:")
            for record in result.data:
                timestamp = record.get('timestamp', 'N/A')
                btc_price = record.get('btc_price', 'N/A')
                eth_price = record.get('eth_price', 'N/A')
                print(f"  Timestamp: {timestamp}")
                print(f"  BTC Price: ${btc_price}")
                print(f"  ETH Price: ${eth_price}")
                print()
        else:
            print("No records found in price_history table")
            
    except Exception as e:
        print(f"Error reading price_history: {str(e)}")
        print("This might be because the new table structure hasn't been applied yet.")
        print("Please run the migration first using the SQL in migrations/update_price_history_combined.sql")
    
    # Test with missing prices
    print("\nTesting with missing ETH price...")
    incomplete_prices = {
        'BTCUSDT': '98765.43'
        # Missing ETHUSDT
    }
    save_price_history(incomplete_prices, logger)
    print("Should have logged a warning about missing price data.")
    
    print("\nTest completed!")
    return True

if __name__ == "__main__":
    test_price_history()