from datetime import datetime, timezone
from utils.database_manager import get_supabase_client

# Current time
now = datetime.now(timezone.utc)
print(f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Current timestamp: {int(now.timestamp() * 1000)}")

# Check last monitoring runs
supabase = get_supabase_client()
nav_history = supabase.table('nav_history').select('*').eq('account_name', 'Ondra(test)').order('timestamp', desc=True).limit(5).execute()

print("\nLast 5 monitoring runs for Ondra(test):")
for nav in nav_history.data:
    ts = datetime.fromisoformat(nav['timestamp'].replace('Z', '+00:00'))
    minutes_ago = (now - ts).total_seconds() / 60
    print(f"  {ts.strftime('%Y-%m-%d %H:%M:%S')} UTC ({minutes_ago:.1f} minutes ago)")

print("\nWhen did you make the $10 USDT withdrawal?")
print("The system runs hourly, so if you made it in the last hour,")
print("it might be captured in the next run.")

# Check if there are ANY withdrawals in the database
all_withdrawals = supabase.table('processed_transactions').select('*').eq('type', 'WITHDRAWAL').execute()
print(f"\nTotal withdrawals in database across all accounts: {len(all_withdrawals.data)}")
if all_withdrawals.data:
    print("Sample withdrawal:")
    w = all_withdrawals.data[0]
    print(f"  Account: {w['account_id']}")
    print(f"  Amount: {w['amount']} {w['coin']}")
    print(f"  Timestamp: {w['timestamp']}")
