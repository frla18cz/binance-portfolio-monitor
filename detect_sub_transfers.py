#!/usr/bin/env python3
"""
Detect and record sub-account transfers using the sub-account API
"""

import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.sub_account_helper import get_sub_account_transfers
from api.logger import MonitorLogger, LogCategory
from utils.database_manager import get_supabase_client

# Create logger instance
logger = MonitorLogger()

def main():
    """Main function to detect sub-account transfers"""
    db_client = get_supabase_client()
    
    # Get sub-account credentials directly
    sub_account = {
        'id': '657dd8b7-bfc3-4ccc-a899-ba8ce648d203',
        'name': 'ondra_osobni_sub_acc1',
        'key': '1hAn2II2rpfNdNp7UdD7gYbEQf4Q6cBK8T9Iq81d9S70ovfhIgfxboR26f5pG7i6',
        'secret': 'vrGp9ZmD7O5VkSPkQgvcLxdSiY5vdXmX4GJN5pfNwSzcFMKHmvc1q2Og8LstRTJj',
        'email': 'frla188cz@gmail.com'
    }
    
    # Get master account info
    master_account = {
        'id': '6236a826-b352-4696-83ad-7cb1f8be1556',
        'name': 'Ondra(test)'
    }
    
    print(f"Checking transfers for sub-account: {sub_account['name']}")
    
    # Get transfers from sub-account perspective (it can see its own transfers)
    transfers = get_sub_account_transfers(
        sub_account['key'], 
        sub_account['secret'],
        logger=logger,
        account_id=sub_account['id']
    )
    
    if not transfers:
        print("No transfers found")
        return
        
    print(f"\nFound {len(transfers)} transfers:")
    
    for transfer in transfers:
        print(f"\n--- Transfer ---")
        print(f"Type: {transfer.get('type')} (1=in, 2=out)")
        print(f"Amount: {transfer.get('qty')} {transfer.get('asset')}")
        print(f"Time: {datetime.fromtimestamp(transfer.get('time', 0)/1000, timezone.utc).isoformat()}")
        print(f"Status: {transfer.get('status')}")
        print(f"TranId: {transfer.get('tranId')}")
        print(f"CounterParty: {transfer.get('counterParty')}")
        print(f"Email: {transfer.get('email')}")
        
        # Record the transfer
        if transfer.get('counterParty') == 'master' and transfer.get('status') == 'SUCCESS':
            transfer_type = transfer.get('type', 0)
            amount = float(transfer.get('qty', 0))
            asset = transfer.get('asset', '')
            tran_id = transfer.get('tranId', '')
            timestamp = transfer.get('time', 0)
            
            # Type 2 = transfer out from sub to master
            if transfer_type == 2:
                print("\n→ Recording as withdrawal from sub-account")
                record_transaction(
                    db_client, sub_account['id'], f"SUB_WD_{tran_id}",
                    'WITHDRAWAL', amount, timestamp, asset,
                    {'transfer_type': 1, 'to': 'master', 'network': 'INTERNAL'},
                    logger
                )
                
                print("→ Recording as deposit to master account")
                record_transaction(
                    db_client, master_account['id'], f"SUB_DEP_{tran_id}",
                    'DEPOSIT', amount, timestamp, asset,
                    {'transfer_type': 1, 'from_email': sub_account['email'], 'network': 'INTERNAL'},
                    logger
                )
            
            # Type 1 = transfer in from master to sub
            elif transfer_type == 1:
                print("\n→ Recording as withdrawal from master account")
                record_transaction(
                    db_client, master_account['id'], f"SUB_WD_{tran_id}",
                    'WITHDRAWAL', amount, timestamp, asset,
                    {'transfer_type': 1, 'to_email': sub_account['email'], 'network': 'INTERNAL'},
                    logger
                )
                
                print("→ Recording as deposit to sub-account")
                record_transaction(
                    db_client, sub_account['id'], f"SUB_DEP_{tran_id}",
                    'DEPOSIT', amount, timestamp, asset,
                    {'transfer_type': 1, 'from': 'master', 'network': 'INTERNAL'},
                    logger
                )

def record_transaction(db_client, account_id, transaction_id, transaction_type, 
                      amount, timestamp, coin, metadata, logger):
    """Record a transaction in the database"""
    try:
        # Check if already exists
        existing = db_client.table('processed_transactions')\
            .select('id')\
            .eq('account_id', account_id)\
            .eq('transaction_id', transaction_id)\
            .execute()
            
        if existing.data:
            print(f"   ⚠️ Transaction already exists: {transaction_id}")
            return
            
        # Insert new transaction
        transaction_data = {
            'account_id': account_id,
            'transaction_id': transaction_id,
            'type': transaction_type,
            'amount': str(amount),
            'timestamp': datetime.fromtimestamp(timestamp/1000, timezone.utc).isoformat(),
            'status': 'SUCCESS',
            'metadata': {**metadata, 'coin': coin}
        }
        
        result = db_client.table('processed_transactions')\
            .insert(transaction_data)\
            .execute()
            
        if result.data:
            print(f"   ✅ Transaction recorded: {transaction_type} {amount} {coin}")
            logger.info(LogCategory.TRANSACTION, "sub_transfer_recorded",
                       f"Recorded sub-account {transaction_type}: {amount} {coin}",
                       account_id=account_id,
                       data={'transaction_id': transaction_id, 'metadata': metadata})
        
    except Exception as e:
        print(f"   ❌ Error recording transaction: {str(e)}")
        logger.error(LogCategory.TRANSACTION, "record_transaction_error",
                    f"Error recording transaction: {str(e)}",
                    account_id=account_id, error=str(e))

if __name__ == "__main__":
    main()