#!/usr/bin/env python3
"""
Debug internal transfers between sub accounts
"""

import os
from datetime import datetime, timedelta
from binance.client import Client as BinanceClient
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def check_account_withdrawals(account_name, api_key, api_secret):
    """Check withdrawals for a specific account"""
    print(f"\n{'='*60}")
    print(f"Checking withdrawals for: {account_name}")
    print(f"{'='*60}")
    
    try:
        # Initialize Binance client
        client = BinanceClient(api_key, api_secret)
        
        # Get withdrawals from last 30 days
        start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        
        withdrawals = client.get_withdraw_history(startTime=start_time)
        
        if not withdrawals:
            print("No withdrawals found in last 30 days")
            return
            
        print(f"Found {len(withdrawals)} withdrawals:")
        
        for w in withdrawals:
            print(f"\n  Withdrawal ID: {w.get('id')}")
            print(f"  Amount: {w.get('amount')} {w.get('coin')}")
            print(f"  Transfer Type: {w.get('transferType')} (0=external, 1=internal)")
            print(f"  TX ID: {w.get('txId')}")
            print(f"  Network: {w.get('network')}")
            print(f"  Status: {w.get('status')}")
            print(f"  Apply Time: {datetime.fromtimestamp(w.get('applyTime', 0)/1000).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Info: {w.get('info')}")
            print(f"  Address: {w.get('address')}")
            
            # Show full details for internal transfers
            if w.get('transferType') == 1 or 'Internal transfer' in str(w.get('txId', '')):
                print("  >>> INTERNAL TRANSFER DETECTED <<<")
                print(f"  Full details: {json.dumps(w, indent=4)}")
                
    except Exception as e:
        print(f"Error checking withdrawals: {str(e)}")
        import traceback
        traceback.print_exc()

def check_account_deposits(account_name, api_key, api_secret):
    """Check deposits for a specific account"""
    print(f"\n{'='*60}")
    print(f"Checking deposits for: {account_name}")
    print(f"{'='*60}")
    
    try:
        # Initialize Binance client
        client = BinanceClient(api_key, api_secret)
        
        # Get deposits from last 30 days
        start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        
        deposits = client.get_deposit_history(startTime=start_time)
        
        if not deposits:
            print("No deposits found in last 30 days")
            return
            
        print(f"Found {len(deposits)} deposits:")
        
        for d in deposits:
            print(f"\n  TX ID: {d.get('txId')}")
            print(f"  Amount: {d.get('amount')} {d.get('coin')}")
            print(f"  Network: {d.get('network')}")
            print(f"  Status: {d.get('status')}")
            print(f"  Insert Time: {datetime.fromtimestamp(d.get('insertTime', 0)/1000).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Address: {d.get('address')}")
            
            # Check if it's from internal transfer
            if 'Internal transfer' in str(d.get('txId', '')):
                print("  >>> INTERNAL TRANSFER DEPOSIT <<<")
                
    except Exception as e:
        print(f"Error checking deposits: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    
    # Hardcoded credentials for debugging (temporary)
    sub_account_key = "1hAn2II2rpfNdNp7UdD7gYbEQf4Q6cBK8T9Iq81d9S70ovfhIgfxboR26f5pG7i6"
    sub_account_secret = "vrGp9ZmD7O5VkSPkQgvcLxdSiY5vdXmX4GJN5pfNwSzcFMKHmvc1q2Og8LstRTJj"
    
    # Main account credentials  
    main_account_key = "V1THp144mDOrsiKFJQSv414GwLydzQHJBauXDTydZvuc3rYw3sqt6ZWJJ43COASV"
    main_account_secret = "sWqSTJ97kBXpttJnffpsc7go3pEih2Ik5NQtY1f4G7k6ri8Ca66PW0zrgTssYL9D"
    
    if sub_account_key and sub_account_secret:
        check_account_withdrawals("ondra_osobni_sub_acc1", sub_account_key, sub_account_secret)
        check_account_deposits("ondra_osobni_sub_acc1", sub_account_key, sub_account_secret)
    else:
        print("Sub account credentials not found")
    
    if main_account_key and main_account_secret:
        check_account_withdrawals("Ondra(test)", main_account_key, main_account_secret)
        check_account_deposits("Ondra(test)", main_account_key, main_account_secret)
    else:
        print("Main account credentials not found")

if __name__ == "__main__":
    main()