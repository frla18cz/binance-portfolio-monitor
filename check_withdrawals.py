from utils.database_manager import get_supabase_client
from datetime import datetime, timezone, timedelta

supabase = get_supabase_client()

# Check withdrawal-related logs from the last monitoring run
print('Withdrawal-related logs from recent monitoring runs:')
logs = supabase.table('system_logs').select('*').in_('operation', ['withdrawals_fetched', 'internal_transfer_detected', 'withdrawals_fetch_failed', 'transactions_fetched']).order('timestamp', desc=True).limit(20).execute()

for log in logs.data:
    if 'Ondra' in log.get('account_id', '') or 'Ondra' in log.get('message', ''):
        print(f"\n{log['timestamp']} - {log['operation']}")
        print(f"  Account ID: {log.get('account_id', 'N/A')}")
        print(f"  Message: {log.get('message', 'N/A')}")
        if log.get('data'):
            print(f"  Data: {log['data']}")

# Check if API is actually being called for withdrawals
print('\n\nChecking all transaction fetch logs for Ondra(test):')
account = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
if account.data:
    account_id = account.data[0]['id']
    logs = supabase.table('system_logs').select('*').eq('account_id', account_id).ilike('operation', '%transaction%').order('timestamp', desc=True).limit(10).execute()
    
    for log in logs.data:
        print(f"\n{log['timestamp']} - {log['operation']}")
        print(f"  Message: {log.get('message', 'N/A')}")
        if log.get('data'):
            print(f"  Data: {log['data']}")
