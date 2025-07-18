#!/usr/bin/env python3
"""
Check why the $10 USDT withdrawal isn't being detected
"""

from datetime import datetime, timezone, timedelta
from utils.database_manager import get_supabase_client
import json

# Current time
now = datetime.now(timezone.utc)
print(f"Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# User said withdrawal was made ~60 minutes before conversation started at 15:59 UTC
# So withdrawal was around 14:59 UTC
withdrawal_time = datetime(2025, 1, 18, 14, 59, 0, tzinfo=timezone.utc)
print(f"Expected withdrawal time: {withdrawal_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

supabase = get_supabase_client()

# Check for any withdrawals in the database
print("\n1. Checking processed_transactions for withdrawals:")
try:
    withdrawals = supabase.table('processed_transactions').select('*').eq('transaction_type', 'WITHDRAWAL').execute()
    print(f"   Total withdrawals in database: {len(withdrawals.data)}")
    
    # Check for recent ones
    recent_withdrawals = [w for w in withdrawals.data if 'T14:' in w['timestamp'] or 'T15:' in w['timestamp']]
    if recent_withdrawals:
        print(f"   Recent withdrawals (14:00-15:59 UTC):")
        for w in recent_withdrawals:
            print(f"     - {w['timestamp']}: {w['amount']} (account: {w['account_id'][:8]}...)")
    else:
        print("   No withdrawals found around 14:00-15:59 UTC today")
        
except Exception as e:
    print(f"   Error: {e}")

# Check system logs for withdrawal-related operations
print("\n2. Checking system_logs for withdrawal operations (last 2 hours):")
try:
    two_hours_ago = (now - timedelta(hours=2)).isoformat()
    logs = supabase.table('system_logs').select('*').gte('timestamp', two_hours_ago).or_(
        'operation.eq.fetch_new_transactions',
        'operation.eq.process_deposits_withdrawals',
        'operation.eq.withdrawal_detected',
        'operation.eq.internal_transfer_detected'
    ).order('timestamp', desc=True).execute()
    
    print(f"   Found {len(logs.data)} relevant log entries")
    
    # Group by operation
    operations = {}
    for log in logs.data:
        op = log['operation']
        if op not in operations:
            operations[op] = []
        operations[op].append(log)
    
    for op, entries in operations.items():
        print(f"\n   {op}: {len(entries)} entries")
        # Show last few entries
        for entry in entries[:3]:
            msg = entry.get('message', '')
            if 'withdrawal' in msg.lower() or 'transfer' in msg.lower():
                print(f"     - {entry['timestamp']}: {msg[:100]}...")
                
except Exception as e:
    print(f"   Error: {e}")

# Check when Ondra(test) account was last processed
print("\n3. Checking last processing for Ondra(test) account:")
try:
    # Get account ID
    accounts = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
    if accounts.data:
        account_id = accounts.data[0]['id']
        print(f"   Account ID: {account_id}")
        
        # Check benchmark config
        configs = supabase.table('benchmark_configs').select('*').eq('account_id', account_id).execute()
        if configs.data:
            config = configs.data[0]
            print(f"   Benchmark initialized at: {config.get('initialized_at', 'Not set')}")
            
        # Check recent NAV history
        nav_history = supabase.table('nav_history').select('*').eq('account_id', account_id).order('timestamp', desc=True).limit(3).execute()
        print(f"\n   Recent NAV history:")
        for nav in nav_history.data:
            print(f"     - {nav['timestamp']}: NAV=${nav['nav']:.2f}")
            
except Exception as e:
    print(f"   Error: {e}")

print("\n4. Testing direct API call for withdrawals:")
try:
    # Get account details
    accounts = supabase.table('binance_accounts').select('*').eq('account_name', 'Ondra(test)').execute()
    if accounts.data:
        account = accounts.data[0]
        
        # Import python-binance
        from binance.client import Client
        
        client = Client(account['api_key'], account['api_secret'])
        
        # Try to fetch withdrawal history
        print("   Fetching withdrawal history from Binance API...")
        
        # Calculate timestamps
        end_time = int(now.timestamp() * 1000)
        start_time = int((now - timedelta(days=1)).timestamp() * 1000)
        
        try:
            # Try the withdrawal history endpoint
            withdrawals = client.get_withdraw_history(startTime=start_time, endTime=end_time)
            print(f"   API returned {len(withdrawals)} withdrawals")
            
            if withdrawals:
                for w in withdrawals:
                    apply_time = datetime.fromtimestamp(w['applyTime'] / 1000, timezone.utc)
                    print(f"\n   Withdrawal found:")
                    print(f"     Time: {apply_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    print(f"     Amount: {w['amount']} {w['coin']}")
                    print(f"     Status: {w['status']}")
                    print(f"     Transfer Type: {w.get('transferType', 'N/A')} (0=external, 1=internal)")
                    print(f"     TX ID: {w.get('txId', 'N/A')}")
                    
        except Exception as api_error:
            print(f"   API Error: {api_error}")
            
            # Try alternative endpoint
            print("\n   Trying alternative withdraw endpoint...")
            try:
                # Some versions use withdraw instead of get_withdraw_history
                withdrawals = client.withdraw_history(startTime=start_time, endTime=end_time)
                print(f"   Alternative API returned: {withdrawals}")
            except:
                pass
                
except ImportError:
    print("   python-binance library not available")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "="*60)
print("SUMMARY:")
print("- If no withdrawals are found, it could be:")
print("  1. The withdrawal hasn't been processed by the monitoring system yet")
print("  2. The withdrawal is an internal transfer and needs special handling")
print("  3. API permissions might be blocking withdrawal history access")
print("  4. The withdrawal happened after the last monitoring run")