"""
Helper functions for handling Binance sub-account transfers
"""

import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode
from datetime import datetime
from api.logger import LogCategory

def create_signature(query_string, secret):
    """Create HMAC SHA256 signature for Binance API"""
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_sub_account_transfers(api_key, api_secret, email=None, start_time=None, end_time=None, logger=None, account_id=None, is_master=True, master_email=None):
    """
    Get sub-account transfer history
    
    Args:
        api_key: API key (master or sub-account)
        api_secret: API secret (master or sub-account)
        email: Sub-account email (optional for master accounts)
        start_time: Start timestamp in milliseconds
        end_time: End timestamp in milliseconds
        logger: Logger instance
        account_id: Account ID for logging
        is_master: True if calling from master account, False if from sub-account
        master_email: Master account email (needed for bidirectional search)
        
    Returns:
        List of transfer transactions
    """
    base_url = 'https://api.binance.com'
    
    # Use different endpoints based on account type
    if is_master:
        # Master account endpoint for querying internal transfers
        endpoint = '/sapi/v1/sub-account/sub/transfer/history'
    else:
        # Sub-account endpoint (can only see its own transfers)
        endpoint = '/sapi/v1/sub-account/transfer/subUserHistory'
    
    # Build parameters
    params = {
        'limit': 500,
        'recvWindow': 60000,
        'timestamp': int(time.time() * 1000)
    }
    
    # Note: Don't use email parameter for master accounts as it limits results
    # The API behaves differently when querying from master vs sub account
    if email and not is_master:
        params['email'] = email
    if start_time:
        params['startTime'] = start_time
    if end_time:
        params['endTime'] = end_time
    
    # Create signature
    query_string = urlencode(params)
    signature = create_signature(query_string, api_secret)
    params['signature'] = signature
    
    # Headers
    headers = {
        'X-MBX-APIKEY': api_key
    }
    
    try:
        # Make request
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Master endpoint behavior varies:
            # - Without email filter: returns list directly
            # - With email filter: returns list directly
            # The 'result' wrapper seems to be deprecated or not used consistently
            transfers = data if isinstance(data, list) else []
            
            if logger:
                logger.debug(LogCategory.API_CALL, 'sub_account_transfers_fetched', 
                           f"Fetched {len(transfers)} sub-account transfers (endpoint: {endpoint})",
                           account_id=account_id)
            
            # For master accounts, also fetch transfers in the opposite direction
            # Always try to get bidirectional transfers regardless of initial result
            if is_master and master_email:
                try:
                    # Build fresh params for each request to avoid mutation
                    base_params = {
                        'limit': 500,
                        'recvWindow': 60000,
                        'timestamp': int(time.time() * 1000)
                    }
                    if start_time:
                        base_params['startTime'] = start_time
                    if end_time:
                        base_params['endTime'] = end_time
                    
                    # Get transfers TO master (from sub-accounts)
                    params_to = base_params.copy()
                    params_to['toEmail'] = master_email
                    query_string_to = urlencode(params_to)
                    params_to['signature'] = create_signature(query_string_to, api_secret)
                    
                    response_to = requests.get(url, headers=headers, params=params_to)
                    transfers_to = []
                    if response_to.status_code == 200:
                        data_to = response_to.json()
                        transfers_to = data_to if isinstance(data_to, list) else []
                    
                    # Get transfers FROM master (to sub-accounts)
                    params_from = base_params.copy()
                    params_from['fromEmail'] = master_email
                    query_string_from = urlencode(params_from)
                    params_from['signature'] = create_signature(query_string_from, api_secret)
                    
                    response_from = requests.get(url, headers=headers, params=params_from)
                    transfers_from = []
                    if response_from.status_code == 200:
                        data_from = response_from.json()
                        transfers_from = data_from if isinstance(data_from, list) else []
                    
                    # Combine all transfers (including original ones without filter)
                    all_transfers = transfers + transfers_to + transfers_from
                    
                    # Remove duplicates based on tranId
                    seen = set()
                    unique_transfers = []
                    for t in all_transfers:
                        tran_id = t.get('tranId')
                        if tran_id and tran_id not in seen:
                            seen.add(tran_id)
                            unique_transfers.append(t)
                    
                    transfers = sorted(unique_transfers, key=lambda x: x.get('time', 0), reverse=True)
                    
                    if logger:
                        logger.debug(LogCategory.API_CALL, 'sub_account_transfers_bidirectional', 
                                   f"Bidirectional: {len(transfers_to)} TO + {len(transfers_from)} FROM = {len(transfers)} total unique",
                                   account_id=account_id)
                except Exception as e:
                    if logger:
                        logger.error(LogCategory.API_CALL, 'sub_account_transfers_bidirectional_error', 
                                   f"Error fetching bidirectional transfers: {str(e)}",
                                   account_id=account_id, error=str(e))
                    # Re-raise to see the actual error during debugging
                    raise
            
            return transfers
        else:
            error_msg = f"Sub-account transfer API error: {response.status_code} - {response.text}"
            if logger:
                logger.warning(LogCategory.API_CALL, 'sub_account_transfers_error', 
                             error_msg, account_id=account_id)
            return []
            
    except Exception as e:
        if logger:
            logger.error(LogCategory.API_CALL, 'sub_account_transfers_exception',
                        f"Error fetching sub-account transfers: {str(e)}",
                        account_id=account_id, error=str(e))
        return []

def normalize_sub_account_transfers(transfers, account_email, logger=None, account_id=None):
    """
    Normalize sub-account transfers to match our transaction format
    
    Args:
        transfers: Raw transfers from API
        account_email: Email of the current account (to determine direction)
        logger: Logger instance
        account_id: Account ID for logging
        
    Returns:
        List of normalized transactions
    """
    normalized = []
    
    for transfer in transfers:
        try:
            # Determine if this is a deposit or withdrawal for current account
            from_email = transfer.get('from', '').lower()
            to_email = transfer.get('to', '').lower()
            current_email = account_email.lower() if account_email else ''
            
            # Skip if we can't determine direction
            if not from_email or not to_email:
                continue
                
            # Determine transaction type based on direction
            if from_email == current_email:
                # This account sent funds - it's a withdrawal
                transaction_type = 'WITHDRAWAL'
                direction = 'outgoing'
            elif to_email == current_email:
                # This account received funds - it's a deposit
                transaction_type = 'DEPOSIT'
                direction = 'incoming'
            else:
                # Not related to this account, skip
                continue
            
            # Create normalized transaction
            transaction = {
                'id': f"SUB_{transfer.get('tranId', '')}",
                'type': transaction_type,
                'amount': float(transfer.get('qty', transfer.get('amount', 0))),  # Master uses 'qty', sub uses 'amount'
                'timestamp': transfer.get('time', 0),
                'status': 1 if transfer.get('status', '').upper() == 'SUCCESS' else 0,
                # Metadata
                'coin': transfer.get('asset', ''),
                'transfer_type': 1,  # Always internal for sub-account transfers
                'tx_id': f"Sub-account transfer {transfer.get('tranId', '')}",
                'from_email': from_email,
                'to_email': to_email,
                'direction': direction,
                'sub_account_type': transfer.get('type', ''),  # 1=transfer in, 2=transfer out
                'network': 'INTERNAL'
            }
            
            normalized.append(transaction)
            
            if logger:
                logger.info(LogCategory.TRANSACTION, 'sub_account_transfer_normalized',
                           f"Sub-account {direction} transfer: {transaction['amount']} {transaction['coin']} "
                           f"({'from ' + from_email if direction == 'incoming' else 'to ' + to_email})",
                           account_id=account_id,
                           data={
                               'tran_id': transfer.get('tranId'),
                               'direction': direction,
                               'amount': transaction['amount'],
                               'coin': transaction['coin']
                           })
                           
        except Exception as e:
            if logger:
                logger.warning(LogCategory.TRANSACTION, 'sub_account_normalization_error',
                             f"Error normalizing sub-account transfer: {str(e)}",
                             account_id=account_id, error=str(e))
            continue
            
    return normalized

def get_account_email_from_api_key(api_key, api_secret, logger=None):
    """
    Get account information including email address
    
    Returns:
        Account email or None if not available
    """
    base_url = 'https://api.binance.com'
    endpoint = '/sapi/v1/account/status'
    
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
            # Try to get account info with email
            # Note: This endpoint might not return email, in which case
            # we'd need to use a different approach or store emails in DB
            return None
        else:
            return None
    except:
        return None