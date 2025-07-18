from utils.database_manager import get_supabase_client

supabase = get_supabase_client()

# Get table structure by querying one row
print("Checking processed_transactions table structure...")
sample = supabase.table('processed_transactions').select('*').limit(1).execute()

if sample.data:
    print("\nTable columns:")
    for key in sample.data[0].keys():
        print(f"  - {key}")
    print(f"\nSample row:")
    for key, value in sample.data[0].items():
        print(f"  {key}: {value}")
else:
    print("No data in processed_transactions table")

# Try to get all transactions for Ondra(test)
account = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
if account.data:
    account_id = account.data[0]['id']
    txns = supabase.table('processed_transactions').select('*').eq('account_id', account_id).execute()
    print(f"\nTotal transactions for Ondra(test): {len(txns.data)}")
    
    if txns.data:
        print("\nTransaction IDs:")
        for t in txns.data:
            print(f"  {t['transaction_id']}")
