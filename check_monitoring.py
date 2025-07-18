from utils.database_manager import get_supabase_client
from datetime import datetime, timezone

supabase = get_supabase_client()

# Check last monitoring run
logs = supabase.table('system_logs').select('*').eq('operation', 'monitoring_start').order('timestamp', desc=True).limit(5).execute()

print('Last 5 monitoring runs:')
for log in logs.data:
    print(f"  {log['timestamp']} - {log.get('message', '')}".strip())

# Check for any withdrawal processing logs
print('\nWithdrawal processing logs (last 24h):')
logs = supabase.table('system_logs').select('*').ilike('message', '%withdrawal%').order('timestamp', desc=True).limit(10).execute()
for log in logs.data:
    msg = log.get('message', '')[:150]
    print(f"  {log['timestamp']} - {log['operation']} - {msg}")

# Check NAV history to see if monitoring is running
print('\nLast NAV updates for Ondra(test):')
nav = supabase.table('nav_history').select('*').eq('account_name', 'Ondra(test)').order('timestamp', desc=True).limit(5).execute()
for n in nav.data:
    print(f"  {n['timestamp']} - NAV: ${n['nav']:.2f}")

# Check processed transactions
print('\nProcessed transactions for Ondra(test):')
account = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
if account.data:
    account_id = account.data[0]['id']
    txns = supabase.table('processed_transactions').select('*').eq('account_id', account_id).order('timestamp', desc=True).limit(5).execute()
    print(f"Total transactions: {len(txns.data)}")
    for t in txns.data:
        print(f"  {t['timestamp']} - {t['type']} - {t['amount']} {t['coin']} - TxID: {t['tx_id'][:30]}...")
