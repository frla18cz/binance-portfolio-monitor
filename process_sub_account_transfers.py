#!/usr/bin/env python3
"""
Process sub-account transfers for all accounts
This script detects and records internal transfers between master and sub-accounts
"""

import sys
import os
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from binance.client import Client as BinanceClient
from api.sub_account_helper import get_sub_account_transfers, normalize_sub_account_transfers
from api.logger import MonitorLogger, LogCategory
from api.index import get_coin_usd_value

# Create logger instance
logger = MonitorLogger()
from utils.database_manager import get_supabase_client
from config import settings

def process_sub_account_transfers_for_all():
    """Process sub-account transfers for all master accounts"""
    db_client = get_supabase_client()
    
    # Create Binance client for price fetching
    binance_client = BinanceClient('', '')
    binance_client.API_URL = 'https://data-api.binance.vision/api'
    
    # Get all master accounts (not sub-accounts)
    response = db_client.table('binance_accounts')\
        .select('*')\
        .eq('is_sub_account', False)\
        .execute()
    
    if not response.data:
        logger.warning(LogCategory.SYSTEM, "no_master_accounts", "No master accounts found")
        return
        
    logger.info(LogCategory.SYSTEM, "found_master_accounts", 
               f"Found {len(response.data)} master accounts to check for sub-account transfers")
    
    # Process each master account
    for account in response.data:
        process_master_account_transfers(account, db_client, logger, binance_client)

def process_master_account_transfers(master_account, db_client, logger, binance_client):
    """Process sub-account transfers for a specific master account"""
    account_id = master_account['id']
    account_name = master_account['account_name']
    api_key = master_account['api_key']
    api_secret = master_account['api_secret']
    
    logger.info(LogCategory.TRANSACTION, "checking_sub_transfers",
               f"Checking sub-account transfers for master: {account_name}",
               account_id=account_id)
    
    try:
        # Get last processed time for this account
        last_processed_response = db_client.table('account_processing_status')\
            .select('last_processed_timestamp')\
            .eq('account_id', account_id)\
            .execute()
        
        if last_processed_response.data:
            last_processed = last_processed_response.data[0]['last_processed_timestamp']
            start_time = int(datetime.fromisoformat(last_processed.replace('Z', '+00:00')).timestamp() * 1000)
        else:
            # Default to 30 days ago
            start_time = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
        
        # Get sub-account transfers
        transfers = get_sub_account_transfers(
            api_key, api_secret, 
            start_time=start_time,
            logger=logger, 
            account_id=account_id
        )
        
        if not transfers:
            logger.info(LogCategory.TRANSACTION, "no_sub_transfers",
                       f"No sub-account transfers found for {account_name}",
                       account_id=account_id)
            return
            
        logger.info(LogCategory.TRANSACTION, "found_sub_transfers",
                   f"Found {len(transfers)} sub-account transfers for {account_name}",
                   account_id=account_id)
        
        # Get all sub-accounts of this master
        sub_accounts_response = db_client.table('binance_accounts')\
            .select('*')\
            .eq('master_account_id', account_id)\
            .execute()
        
        sub_accounts_by_email = {acc['email'].lower(): acc for acc in sub_accounts_response.data if acc.get('email')}
        
        # Process transfers
        for transfer in transfers:
            process_single_transfer(transfer, master_account, sub_accounts_by_email, db_client, logger, binance_client)
            
    except Exception as e:
        import traceback
        logger.error(LogCategory.TRANSACTION, "sub_transfer_error",
                    f"Error processing sub-account transfers for {account_name}: {str(e)}",
                    account_id=account_id, error=str(e))
        traceback.print_exc()

def process_single_transfer(transfer, master_account, sub_accounts_by_email, db_client, logger, binance_client):
    """Process a single sub-account transfer"""
    # Sub-account transfer API has different format:
    # - email: the sub-account email
    # - counterParty: "master" if transfer between sub and master
    # - type: 1=transfer in (to sub), 2=transfer out (from sub)
    
    sub_email = transfer.get('email', '').lower()
    counter_party = transfer.get('counterParty', '')
    transfer_type = transfer.get('type', 0)  # 1=in, 2=out
    amount = float(transfer.get('qty', 0))  # Note: it's 'qty' not 'amount'
    asset = transfer.get('asset', '')
    tran_id = transfer.get('tranId', '')
    timestamp = transfer.get('time', 0)
    
    # Check if this is a transfer with master account
    if counter_party != 'master':
        logger.warning(LogCategory.TRANSACTION, "non_master_transfer",
                      f"Non-master transfer detected: {counter_party}",
                      data={'transfer': transfer})
        return
        
    # Get sub-account from email
    sub_account = sub_accounts_by_email.get(sub_email)
    if not sub_account:
        logger.warning(LogCategory.TRANSACTION, "unknown_sub_account",
                      f"Unknown sub-account email: {sub_email}",
                      data={'transfer': transfer})
        return
        
    # Get USD value for the asset
    usd_value, coin_price, price_source = get_coin_usd_value(
        binance_client, asset, amount, logger=logger
    )
    
    # Process based on transfer type
    if transfer_type == 2:  # Transfer out from sub-account
        # Sub-account is sending (withdrawal) to master
        record_transaction(
            db_client, sub_account['id'], f"SUB_WD_{tran_id}",
            'WITHDRAWAL', amount, timestamp, asset, 
            {'transfer_type': 1, 'to': 'master', 'network': 'INTERNAL'},
            logger, usd_value, coin_price, price_source
        )
        # Master account is receiving (deposit) from sub
        record_transaction(
            db_client, master_account['id'], f"SUB_DEP_{tran_id}",
            'DEPOSIT', amount, timestamp, asset,
            {'transfer_type': 1, 'from_email': sub_email, 'network': 'INTERNAL'},
            logger, usd_value, coin_price, price_source
        )
    elif transfer_type == 1:  # Transfer in to sub-account
        # Master account is sending (withdrawal) to sub
        record_transaction(
            db_client, master_account['id'], f"SUB_WD_{tran_id}",
            'WITHDRAWAL', amount, timestamp, asset,
            {'transfer_type': 1, 'to_email': sub_email, 'network': 'INTERNAL'},
            logger, usd_value, coin_price, price_source
        )
        # Sub-account is receiving (deposit) from master
        record_transaction(
            db_client, sub_account['id'], f"SUB_DEP_{tran_id}",
            'DEPOSIT', amount, timestamp, asset,
            {'transfer_type': 1, 'from': 'master', 'network': 'INTERNAL'},
            logger, usd_value, coin_price, price_source
        )
    else:
        logger.warning(LogCategory.TRANSACTION, "unknown_transfer_type",
                      f"Unknown transfer type: {transfer_type}",
                      data={'transfer': transfer})

def record_transaction(db_client, account_id, transaction_id, transaction_type, 
                      amount, timestamp, coin, metadata, logger, usd_value=None, coin_price=None, price_source=None):
    """Record a transaction in the database with USD value"""
    try:
        # Check if already exists
        existing = db_client.table('processed_transactions')\
            .select('id')\
            .eq('account_id', account_id)\
            .eq('transaction_id', transaction_id)\
            .execute()
            
        if existing.data:
            logger.debug(LogCategory.TRANSACTION, "transaction_exists",
                        f"Transaction already processed: {transaction_id}",
                        account_id=account_id)
            return
            
        # Insert new transaction
        transaction_data = {
            'account_id': account_id,
            'transaction_id': transaction_id,
            'type': transaction_type,
            'amount': str(amount),
            'timestamp': datetime.fromtimestamp(timestamp/1000, timezone.utc).isoformat(),
            'status': 'SUCCESS',
            'metadata': {
                **metadata, 
                'coin': coin,
                'usd_value': usd_value,
                'coin_price': coin_price,
                'price_source': price_source,
                'price_missing': usd_value is None
            }
        }
        
        result = db_client.table('processed_transactions')\
            .insert(transaction_data)\
            .execute()
            
        if result.data:
            logger.info(LogCategory.TRANSACTION, "sub_transfer_recorded",
                       f"Recorded sub-account {transaction_type}: {amount} {coin}" + (f" (${usd_value:.2f})" if usd_value else " (no USD value)"),
                       account_id=account_id,
                       data={'transaction_id': transaction_id, 'metadata': transaction_data['metadata']})
        
    except Exception as e:
        logger.error(LogCategory.TRANSACTION, "record_transaction_error",
                    f"Error recording transaction: {str(e)}",
                    account_id=account_id, error=str(e))

if __name__ == "__main__":
    process_sub_account_transfers_for_all()