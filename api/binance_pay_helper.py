"""
Helper module for Binance Pay API calls.
Works around python-binance bug with Pay API endpoint.
"""

import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from typing import List, Dict, Any, Optional
from api.logger import LogCategory


def create_signature(params: Dict[str, Any], secret: str) -> str:
    """Create HMAC SHA256 signature for Binance API"""
    query_string = urlencode(params)
    signature = hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def get_pay_transactions(api_key: str, api_secret: str, logger=None, account_id=None) -> List[Dict[str, Any]]:
    """
    Get Binance Pay transactions using direct API call.
    
    This is a workaround for python-binance bug with /sapi/v1/pay/transactions endpoint.
    
    Returns:
        List of pay transaction dictionaries
    """
    try:
        base_url = "https://api.binance.com"
        endpoint = "/sapi/v1/pay/transactions"
        
        # Create request parameters
        params = {
            'timestamp': int(time.time() * 1000)
        }
        
        # Add signature
        params['signature'] = create_signature(params, api_secret)
        
        # Headers
        headers = {
            'X-MBX-APIKEY': api_key
        }
        
        # Make request
        response = requests.get(
            base_url + endpoint,
            headers=headers,
            params=params,
            timeout=30
        )
        
        # Check response status
        if response.status_code != 200:
            if logger:
                logger.warning(LogCategory.API_CALL, "pay_api_error", 
                             f"Pay API returned status {response.status_code}: {response.text}",
                             account_id=account_id)
            return []
        
        # Parse response
        data = response.json()
        
        # Handle response structure
        if isinstance(data, dict):
            if data.get('code') == '000000' and 'data' in data:
                return data['data'] if isinstance(data['data'], list) else []
            else:
                # API error response
                if logger:
                    logger.warning(LogCategory.API_CALL, "pay_api_response_error",
                                 f"Pay API error: code={data.get('code')}, message={data.get('message')}",
                                 account_id=account_id)
                return []
        elif isinstance(data, list):
            # Direct list response (shouldn't happen based on docs, but just in case)
            return data
        else:
            if logger:
                logger.warning(LogCategory.API_CALL, "pay_api_unexpected_type",
                             f"Unexpected Pay API response type: {type(data)}",
                             account_id=account_id)
            return []
            
    except requests.exceptions.RequestException as e:
        if logger:
            logger.error(LogCategory.API_CALL, "pay_api_request_error",
                        f"Pay API request failed: {str(e)}",
                        account_id=account_id)
        return []
    except Exception as e:
        if logger:
            logger.error(LogCategory.API_CALL, "pay_api_unexpected_error",
                        f"Unexpected error in Pay API: {str(e)}",
                        account_id=account_id)
        return []