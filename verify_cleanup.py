
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database_manager import get_supabase_client

def verify_previous_state():
    db = get_supabase_client()
    account_name = 'Habitanti'
    cleanup_start_date = datetime.fromisoformat('2025-05-08T00:00:00+00:00')

    # First, get account ID from name
    account_response = db.table('binance_accounts').select('id').eq('account_name', account_name).execute()
    if not account_response.data:
        print(f"ERROR: Account '{account_name}' not found.")
        return

    account_id = account_response.data[0]['id']
    print(f"Found account '{account_name}' with ID: {account_id}")
    print(f"Checking for last benchmark modification before {cleanup_start_date.isoformat()}...")

    # This is the exact logic from cleanup_nav_data.py
    last_valid_mod = db.table('benchmark_modifications') \
        .select('btc_units_after, eth_units_after, modification_timestamp') \
        .eq('account_id', account_id) \
        .lt('modification_timestamp', cleanup_start_date.isoformat()) \
        .order('modification_timestamp', desc=True) \
        .limit(1) \
        .execute()

    if last_valid_mod.data:
        print("\n--- VERIFICATION SUCCESSFUL ---")
        print("Found a valid benchmark state to restore from:")
        print(f"  Timestamp: {last_valid_mod.data[0]['modification_timestamp']}")
        print(f"  BTC Units: {last_valid_mod.data[0]['btc_units_after']}")
        print(f"  ETH Units: {last_valid_mod.data[0]['eth_units_after']}")
        print("\nThis means the cleanup script will work correctly.")
    else:
        print("\n--- VERIFICATION FAILED ---")
        print("Could not find any benchmark modification record before the cleanup date.")
        print("This is why the benchmark was reset to 0 last time.")
        print("We should NOT proceed with the cleanup until this is resolved.")

if __name__ == "__main__":
    verify_previous_state()

