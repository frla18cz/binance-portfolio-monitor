#!/usr/bin/env python3
"""
Get account information including email addresses
"""

import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode
import json

def create_signature(query_string, secret):
    """Create HMAC SHA256 signature"""
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_account_info(api_key, api_secret, account_name):
    """Get account information"""
    print(f"\n{'='*60}")
    print(f"Getting info for: {account_name}")
    print(f"{'='*60}")
    
    # Try account API info endpoint
    base_url = 'https://api.binance.com'
    endpoint = '/sapi/v3/account/info'
    
    params = {
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
    
    try:
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Account info retrieved successfully:")
            print(json.dumps(data, indent=2))
            
            # Try to find email
            if 'email' in data:
                print(f"\nEmail found: {data['email']}")
            else:
                print("\nNo email in response")
                
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        
    # Also try sub-account list if this is a master account
    print(f"\n--- Checking sub-accounts ---")
    endpoint = '/sapi/v1/sub-account/list'
    
    params = {
        'limit': 100,
        'recvWindow': 60000,
        'timestamp': int(time.time() * 1000)
    }
    
    # Create signature
    query_string = urlencode(params)
    signature = create_signature(query_string, api_secret)
    params['signature'] = signature
    
    try:
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            sub_accounts = data.get('subAccounts', [])
            
            if sub_accounts:
                print(f"Found {len(sub_accounts)} sub-accounts:")
                for sub in sub_accounts:
                    print(f"  - Email: {sub.get('email')}")
                    print(f"    Is Trading Enabled: {sub.get('isUserActive')}")
                    print(f"    Create Time: {sub.get('createTime')}")
            else:
                print("No sub-accounts found (this might be a sub-account itself)")
        else:
            print(f"Sub-account check error: {response.status_code}")
            if "sub account" in response.text.lower():
                print("This appears to be a sub-account (cannot list other sub-accounts)")
                
    except Exception as e:
        print(f"Sub-account check exception: {str(e)}")

def main():
    """Main function"""
    
    # Account credentials
    accounts = [
        {
            'name': 'ondra_osobni_sub_acc1',
            'key': '1hAn2II2rpfNdNp7UdD7gYbEQf4Q6cBK8T9Iq81d9S70ovfhIgfxboR26f5pG7i6',
            'secret': 'vrGp9ZmD7O5VkSPkQgvcLxdSiY5vdXmX4GJN5pfNwSzcFMKHmvc1q2Og8LstRTJj'
        },
        {
            'name': 'Ondra(test)',
            'key': 'V1THp144mDOrsiKFJQSv414GwLydzQHJBauXDTydZvuc3rYw3sqt6ZWJJ43COASV',
            'secret': 'sWqSTJ97kBXpttJnffpsc7go3pEih2Ik5NQtY1f4G7k6ri8Ca66PW0zrgTssYL9D'
        }
    ]
    
    for account in accounts:
        get_account_info(account['key'], account['secret'], account['name'])

if __name__ == "__main__":
    main()