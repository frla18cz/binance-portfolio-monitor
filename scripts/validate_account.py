#!/usr/bin/env python3
"""
Validate Binance Account API Credentials

This script tests API credentials for Binance accounts to ensure they work correctly.
"""

import sys
import os
from pathlib import Path
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database_manager import DatabaseManager


def test_binance_api(api_key: str, api_secret: str) -> tuple[bool, str]:
    """
    Test Binance API credentials by making a simple API call.
    
    Args:
        api_key: Binance API key
        api_secret: Binance API secret
    
    Returns:
        Tuple of (success, message)
    """
    try:
        base_url = 'https://api.binance.com'
        endpoint = '/api/v3/account'
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        query_string = urlencode(params)
        
        # Create signature
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params['signature'] = signature
        
        # Make request
        headers = {'X-MBX-APIKEY': api_key}
        response = requests.get(
            base_url + endpoint,
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, 'Connection successful'
        elif response.status_code == 401:
            return False, 'Invalid API credentials'
        elif response.status_code == 418:
            return False, 'IP not whitelisted for this API key'
        else:
            error_msg = response.json().get('msg', f'Unknown error')
            return False, f'API error (code {response.status_code}): {error_msg}'
            
    except requests.exceptions.Timeout:
        return False, 'Connection timeout'
    except requests.exceptions.ConnectionError:
        return False, 'Connection failed - check internet connection'
    except Exception as e:
        return False, f'Unexpected error: {str(e)}'


def test_account_settings(account_id: str) -> tuple[bool, str]:
    """
    Test API credentials for an account from the database.
    
    Args:
        account_id: Account ID from database
    
    Returns:
        Tuple of (success, message)
    """
    try:
        db = DatabaseManager()
        
        # Get account from database
        result = db._client.table('binance_accounts')\
            .select('*')\
            .eq('id', account_id)\
            .execute()
        
        if not result.data:
            return False, 'Account not found'
        
        account = result.data[0]
        
        # Test main API credentials
        api_key = account.get('api_key')
        api_secret = account.get('api_secret')
        
        if not api_key or not api_secret:
            return False, 'Missing API credentials'
        
        success, message = test_binance_api(api_key, api_secret)
        
        if not success:
            return False, f"Main API: {message}"
        
        # Test master API if it's a sub-account
        if account.get('is_sub_account'):
            master_api_key = account.get('master_api_key')
            master_api_secret = account.get('master_api_secret')
            
            if master_api_key and master_api_secret:
                master_success, master_message = test_binance_api(master_api_key, master_api_secret)
                if not master_success:
                    return False, f"Main API OK, Master API: {master_message}"
                return True, "Both main and master API credentials are valid"
            else:
                return True, "Main API valid (master API not configured)"
        
        return True, "API credentials are valid"
        
    except Exception as e:
        return False, f"Error testing account: {str(e)}"


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Binance account API credentials')
    parser.add_argument('account_id', help='Account ID to test')
    args = parser.parse_args()
    
    print(f"Testing account {args.account_id}...")
    success, message = test_account_settings(args.account_id)
    
    if success:
        print(f"✓ {message}")
        return 0
    else:
        print(f"✗ {message}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
