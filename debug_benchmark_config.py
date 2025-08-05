#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from utils.database_manager import get_supabase_client
import json

load_dotenv()

db_client = get_supabase_client()

# Get the master account
account_result = db_client.table('binance_accounts').select('*, benchmark_configs(*)').eq(
    'account_name', 'Ondra(test)'
).execute()

print("Raw result:")
print(json.dumps(account_result.data, indent=2))