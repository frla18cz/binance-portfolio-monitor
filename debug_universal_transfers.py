#!/usr/bin/env python3
"""
Debug universal transfers (internal transfers between accounts)
"""

import requests
import time
import hmac
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlencode

def create_signature(query_string, secret):
    """Create HMAC SHA256 signature"""
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_universal_transfers(api_key, api_secret, transfer_type='MAIN_UMFUTURE'):
    """Get universal transfer history"""
    base_url = 'https://api.binance.com'
    endpoint = '/sapi/v1/asset/transfer'
    
    # Parameters
    params = {
        'type': transfer_type,
        'startTime': int((datetime.now() - timedelta(days=30)).timestamp() * 1000),
        'recvWindow': 60000,
        'timestamp': int(time.time() * 1000)
    }
    
    # Create signature
    query_string = urlencode(params)
    signature = create_signature(query_string, api_secret)
    params['signature'] = signature
    
    # Headers
    headers = {
        'X-MBX-APIKEY': api_key
    }
    
    # Make request
    url = f"{base_url}{endpoint}"
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('rows', [])
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []

def check_all_transfer_types(api_key, api_secret, account_name):
    """Check all possible transfer types"""
    transfer_types = [
        'MAIN_UMFUTURE', 'MAIN_CMFUTURE', 'MAIN_MARGIN', 'MAIN_FUNDING',
        'UMFUTURE_MAIN', 'CMFUTURE_MAIN', 'MARGIN_MAIN', 'FUNDING_MAIN',
        'MAIN_PORTFOLIO_MARGIN', 'PORTFOLIO_MARGIN_MAIN'
    ]
    
    print(f"\n{'='*60}")
    print(f"Checking universal transfers for: {account_name}")
    print(f"{'='*60}")
    
    all_transfers = []
    
    for transfer_type in transfer_types:
        transfers = get_universal_transfers(api_key, api_secret, transfer_type)
        if transfers:
            print(f"\n{transfer_type}: Found {len(transfers)} transfers")
            for t in transfers:
                print(f"  - Amount: {t.get('amount')} {t.get('asset')}")
                print(f"    Time: {datetime.fromtimestamp(t.get('timestamp', 0)/1000).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    Status: {t.get('status')}")
                print(f"    TranId: {t.get('tranId')}")
            all_transfers.extend(transfers)
    
    if not all_transfers:
        print("\nNo universal transfers found")
    
    return all_transfers

def check_sub_account_transfers(api_key, api_secret, account_name):
    """Check sub-account transfer history"""
    base_url = 'https://api.binance.com'
    endpoint = '/sapi/v1/sub-account/transfer/subUserHistory'
    
    params = {
        'startTime': int((datetime.now() - timedelta(days=30)).timestamp() * 1000),
        'endTime': int(datetime.now().timestamp() * 1000),
        'limit': 500,
        'recvWindow': 60000,
        'timestamp': int(time.time() * 1000)
    }
    
    # Create signature
    query_string = urlencode(params)
    signature = create_signature(query_string, api_secret)
    params['signature'] = signature
    
    # Headers
    headers = {
        'X-MBX-APIKEY': api_key
    }
    
    # Make request
    url = f"{base_url}{endpoint}"
    response = requests.get(url, headers=headers, params=params)
    
    print(f"\n{'='*60}")
    print(f"Checking sub-account transfers for: {account_name}")
    print(f"{'='*60}")
    
    if response.status_code == 200:
        data = response.json()
        transfers = data if isinstance(data, list) else []
        
        if transfers:
            print(f"Found {len(transfers)} sub-account transfers:")
            for t in transfers:
                print(f"\n  - Amount: {t.get('amount')} {t.get('asset')}")
                print(f"    From: {t.get('from')} -> To: {t.get('to')}")
                print(f"    Time: {datetime.fromtimestamp(t.get('time', 0)/1000).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    Type: {t.get('type')}")
                print(f"    Status: {t.get('status')}")
        else:
            print("No sub-account transfers found")
    else:
        print(f"Error: {response.status_code} - {response.text}")

def main():
    """Main function"""
    
    # Hardcoded credentials for debugging (temporary)
    sub_account_key = "1hAn2II2rpfNdNp7UdD7gYbEQf4Q6cBK8T9Iq81d9S70ovfhIgfxboR26f5pG7i6"
    sub_account_secret = "vrGp9ZmD7O5VkSPkQgvcLxdSiY5vdXmX4GJN5pfNwSzcFMKHmvc1q2Og8LstRTJj"
    
    # Main account credentials  
    main_account_key = "V1THp144mDOrsiKFJQSv414GwLydzQHJBauXDTydZvuc3rYw3sqt6ZWJJ43COASV"
    main_account_secret = "sWqSTJ97kBXpttJnffpsc7go3pEih2Ik5NQtY1f4G7k6ri8Ca66PW0zrgTssYL9D"
    
    # Check universal transfers for both accounts
    check_all_transfer_types(sub_account_key, sub_account_secret, "ondra_osobni_sub_acc1")
    check_all_transfer_types(main_account_key, main_account_secret, "Ondra(test)")
    
    # Check sub-account transfers from main account perspective
    check_sub_account_transfers(main_account_key, main_account_secret, "Ondra(test) - Main Account")

if __name__ == "__main__":
    main()