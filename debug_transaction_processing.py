from utils.database_manager import get_supabase_client
from datetime import datetime, timezone, timedelta

supabase = get_supabase_client()

# Get Ondra(test) account
account = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
if not account.data:
    print("Ondra(test) account not found")
    exit()

account_id = account.data[0]['id']
print(f"Account ID: {account_id}")

# Check logs for transaction processing
print("\nTransaction processing logs (last 24h):")
logs = supabase.table('system_logs').select('*').eq('account_id', account_id).in_('operation', [
    'transactions_fetched',
    'no_new_transactions', 
    'processing_transactions',
    'pre_init_filtered',
    'deposit_processed',
    'withdrawal_processed',
    'internal_transfer_detected'
]).order('timestamp', desc=True).limit(20).execute()

for log in logs.data:
    print(f"\n{log['timestamp']} - {log['operation']}")
    print(f"  {log.get('message', '')}")
    if log.get('data'):
        print(f"  Data: {log['data']}")

# Check benchmark config initialized_at
print("\n\nBenchmark config:")
config = supabase.table('benchmark_configs').select('*').eq('account_id', account_id).execute()
if config.data:
    cfg = config.data[0]
    print(f"  Initialized at: {cfg.get('initialized_at', 'Not set')}")
    print(f"  BTC units: {cfg.get('btc_units')}")
    print(f"  ETH units: {cfg.get('eth_units')}")
    
    # Check if transactions are being filtered
    if cfg.get('initialized_at'):
        init_time = datetime.fromisoformat(cfg['initialized_at'].replace('Z', '+00:00'))
        print(f"  Transactions before {init_time.strftime('%Y-%m-%d %H:%M:%S')} UTC will be filtered")
