"""
Helper functions for handling Binance sub-account transfers
"""

from datetime import datetime
from api.logger import LogCategory

def get_sub_account_transfers(api_key, api_secret, email=None, start_time=None, end_time=None, logger=None, account_id=None, is_master=True, master_email=None):
    """
    Get sub-account transfer history using Binance client
    
    Args:
        api_key: API key (master or sub-account)
        api_secret: API secret (master or sub-account)
        email: Sub-account email (for filtering transfers)
        start_time: Start timestamp in milliseconds
        end_time: End timestamp in milliseconds
        logger: Logger instance
        account_id: Account ID for logging
        is_master: True if calling from master account, False if from sub-account
        master_email: Master account email (for filtering transfers)
        
    Returns:
        List of transfer transactions
    """
    from binance.client import Client
    
    try:
        # Create Binance client
        client = Client(api_key, api_secret)
        
        # Build parameters
        params = {}
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        all_transfers = []
        
        # For master accounts, we need to get transfers in both directions
        if is_master and master_email:
            # Get transfers FROM master account
            try:
                from_transfers = client.get_sub_account_transfer_history(
                    fromEmail=master_email,
                    **params
                )
                if from_transfers:
                    all_transfers.extend(from_transfers)
                    if logger:
                        logger.debug(LogCategory.API_CALL, 'sub_account_transfers_from_master', 
                                   f"Fetched {len(from_transfers)} transfers FROM master",
                                   account_id=account_id)
            except Exception as e:
                if logger:
                    logger.debug(LogCategory.API_CALL, 'sub_account_transfers_from_error', 
                               f"Error getting transfers FROM master: {str(e)}",
                               account_id=account_id)
            
            # Get transfers TO master account
            try:
                to_transfers = client.get_sub_account_transfer_history(
                    toEmail=master_email,
                    **params
                )
                if to_transfers:
                    all_transfers.extend(to_transfers)
                    if logger:
                        logger.debug(LogCategory.API_CALL, 'sub_account_transfers_to_master', 
                                   f"Fetched {len(to_transfers)} transfers TO master",
                                   account_id=account_id)
            except Exception as e:
                if logger:
                    logger.debug(LogCategory.API_CALL, 'sub_account_transfers_to_error', 
                               f"Error getting transfers TO master: {str(e)}",
                               account_id=account_id)
        
        # For sub-accounts (or if email is provided), get transfers for specific email
        elif email and not is_master:
            # Get transfers FROM this email
            try:
                from_transfers = client.get_sub_account_transfer_history(
                    fromEmail=email,
                    **params
                )
                if from_transfers:
                    all_transfers.extend(from_transfers)
                    if logger:
                        logger.debug(LogCategory.API_CALL, 'sub_account_transfers_from_sub', 
                                   f"Fetched {len(from_transfers)} transfers FROM {email}",
                                   account_id=account_id)
            except Exception as e:
                if logger:
                    logger.debug(LogCategory.API_CALL, 'sub_account_transfers_from_sub_error', 
                               f"Error getting transfers FROM {email}: {str(e)}",
                               account_id=account_id)
            
            # Get transfers TO this email
            try:
                to_transfers = client.get_sub_account_transfer_history(
                    toEmail=email,
                    **params
                )
                if to_transfers:
                    all_transfers.extend(to_transfers)
                    if logger:
                        logger.debug(LogCategory.API_CALL, 'sub_account_transfers_to_sub', 
                                   f"Fetched {len(to_transfers)} transfers TO {email}",
                                   account_id=account_id)
            except Exception as e:
                if logger:
                    logger.debug(LogCategory.API_CALL, 'sub_account_transfers_to_sub_error', 
                               f"Error getting transfers TO {email}: {str(e)}",
                               account_id=account_id)
        
        # If no specific email, get all transfers (master account without filtering)
        elif not email and is_master:
            try:
                all_transfers = client.get_sub_account_transfer_history(**params)
                if logger:
                    logger.debug(LogCategory.API_CALL, 'sub_account_transfers_all', 
                               f"Fetched {len(all_transfers) if all_transfers else 0} transfers (no filter)",
                               account_id=account_id)
            except Exception as e:
                if logger:
                    logger.debug(LogCategory.API_CALL, 'sub_account_transfers_all_error', 
                               f"Error getting all transfers: {str(e)}",
                               account_id=account_id)
        
        # Remove duplicates based on tranId
        if all_transfers:
            seen = set()
            unique_transfers = []
            for t in all_transfers:
                # Convert dict keys for compatibility
                if 'tranId' not in t and 'id' in t:
                    t['tranId'] = t['id']
                if 'qty' not in t and 'amount' in t:
                    t['qty'] = t['amount']
                    
                tran_id = t.get('tranId')
                if tran_id and tran_id not in seen:
                    seen.add(tran_id)
                    unique_transfers.append(t)
            
            transfers = sorted(unique_transfers, key=lambda x: x.get('time', 0), reverse=True)
            
            if logger:
                logger.info(LogCategory.API_CALL, 'sub_account_transfers_fetched', 
                           f"Total unique transfers: {len(transfers)}",
                           account_id=account_id)
            
            return transfers
        else:
            if logger:
                logger.debug(LogCategory.API_CALL, 'sub_account_transfers_none', 
                           "No transfers found",
                           account_id=account_id)
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
    # Note: Binance API doesn't provide a direct way to get account email
    # Email must be stored in database when creating the account
    return None