#!/usr/bin/env python3
"""
Find which account is the real master account
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

def test_account_type(api_key, api_secret, account_name):
    """Test if account is master or sub-account"""
    print(f"\nTesting: {account_name}")
    print("="*50)
    
    # Test 1: Try sub-account list endpoint (only works for master)
    base_url = 'https://api.binance.com'
    endpoint = '/sapi/v1/sub-account/list'
    
    params = {
        'limit': 1,
        'recvWindow': 60000,
        'timestamp': int(time.time() * 1000)
    }
    
    query_string = urlencode(params)
    signature = create_signature(query_string, api_secret)
    params['signature'] = signature
    
    headers = {
        'X-MBX-APIKEY': api_key
    }
    
    try:
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            print("✅ This is a MASTER account (can list sub-accounts)")
            data = response.json()
            if data.get('subAccounts'):
                print("   Sub-accounts found:")
                for sub in data['subAccounts']:
                    print(f"   - {sub.get('email')}")
        else:
            error_data = response.json() if response.text else {}
            if error_data.get('code') == -12022:
                print("❌ This is a SUB-ACCOUNT (cannot list sub-accounts)")
            else:
                print(f"❓ Unclear status: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"Error: {str(e)}")
        
    # Test 2: Try sub-account transfer history (for sub-accounts)
    endpoint = '/sapi/v1/sub-account/transfer/subUserHistory'
    
    params = {
        'limit': 1,
        'recvWindow': 60000,
        'timestamp': int(time.time() * 1000)
    }
    
    query_string = urlencode(params)
    signature = create_signature(query_string, api_secret)
    params['signature'] = signature
    
    try:
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            print("✅ Can access sub-account transfer history")
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                print(f"   Found {len(data)} transfers")
        else:
            error_data = response.json() if response.text else {}
            if error_data.get('code') == -12022:
                print("❌ Cannot access sub-account transfer history (master account endpoint)")
            else:
                print(f"   Transfer history status: {response.status_code}")
                
    except Exception as e:
        print(f"   Transfer history error: {str(e)}")

def main():
    """Main function"""
    
    accounts = [
        {
            'name': 'Ondra(test)',
            'key': 'V1THp144mDOrsiKFJQSv414GwLydzQHJBauXDTydZvuc3rYw3sqt6ZWJJ43COASV',
            'secret': 'sWqSTJ97kBXpttJnffpsc7go3pEih2Ik5NQtY1f4G7k6ri8Ca66PW0zrgTssYL9D'
        },
        {
            'name': 'ondra_osobni_sub_acc1',
            'key': '1hAn2II2rpfNdNp7UdD7gYbEQf4Q6cBK8T9Iq81d9S70ovfhIgfxboR26f5pG7i6',
            'secret': 'vrGp9ZmD7O5VkSPkQgvcLxdSiY5vdXmX4GJN5pfNwSzcFMKHmvc1q2Og8LstRTJj'
        }
    ]
    
    for account in accounts:
        test_account_type(account['key'], account['secret'], account['name'])
        
    # Also check other accounts for comparison
    print("\n\nChecking other accounts for comparison:")
    
    other_accounts = [
        {
            'name': 'Simple',
            'key': '9wyLwq1HK1ZkGO0eYpbIIEVT9eOB3u0SZrTKR1VtjN5BUrRLYUYmyYlmDljoUdqB',
            'secret': '4u2Gm1uPKZz17cRvEECaolLE2NeB6KKfaAZ8SCmPf5PTv8lSx5gBUnvUYNQlqFxP'
        }
    ]
    
    for account in other_accounts:
        test_account_type(account['key'], account['secret'], account['name'])

if __name__ == "__main__":
    main()