#!/usr/bin/env python3
"""
Test script for mixed transaction types (regular + pay transactions).
Tests that all transaction types are correctly processed together.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from unittest.mock import Mock
from api.index import fetch_new_transactions
from api.logger import LogCategory

def test_mixed_transactions():
    """Test that fetch_new_transactions correctly handles all transaction types together."""
    
    # Create mock logger
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    
    # Create mock Binance client
    mock_client = Mock()
    
    # Mock regular deposit history
    mock_client.get_deposit_history.return_value = [
        {
            "txId": "0x123456789abcdef",
            "amount": "1000.0",
            "coin": "USDT",
            "status": 1,  # Success
            "insertTime": 1719949467394,  # 2024-07-02 14:14:27
            "network": "TRC20"
        }
    ]
    
    # Mock regular withdrawal history
    mock_client.get_withdraw_history.return_value = [
        {
            "id": "withdrawal-id-123",
            "amount": "500.0",
            "coin": "USDT",
            "status": 6,  # Completed
            "applyTime": 1719949567394,  # 2024-07-02 14:16:07
            "network": "TRC20",
            "transferType": 0,  # External transfer
            "txId": "0xabcdef123456789"
        }
    ]
    
    # Mock Binance Pay transactions response
    mock_pay_response = {
        "code": "000000",
        "message": "success",
        "data": [
            {
                "orderType": "C2C",
                "transactionId": "P_A1UBSK9SJNN71115",
                "transactionTime": "1719949667394",  # 2024-07-02 14:17:47
                "amount": "2000",  # Positive = incoming
                "currency": "USDC",
                "walletType": "2",
                "payerInfo": {
                    "name": "User-Friend",
                    "binanceId": "38755365",
                    "email": "friend@example.com"
                }
            },
            {
                "orderType": "C2C",
                "transactionId": "P_A1UPBE6WV3H71113",
                "transactionTime": "1719949767394",  # 2024-07-02 14:19:27
                "amount": "-300",  # Negative = outgoing
                "currency": "USDC",
                "walletType": "2",
                "receiverInfo": {
                    "name": "User-Receiver",
                    "type": "USER",
                    "email": "receiver@example.com",
                    "accountId": "235656193"
                }
            }
        ],
        "success": True
    }
    
    # Mock the _request method for pay transactions
    mock_client._request.return_value = mock_pay_response
    
    # Test start time (before all transactions)
    start_time = "2024-07-01T00:00:00Z"
    
    # Call the function
    transactions = fetch_new_transactions(
        mock_client,
        start_time,
        logger=logger,
        account_id="test_account"
    )
    
    # Verify results
    print(f"Total transactions found: {len(transactions)}")
    
    # Check that we have all transaction types
    deposits = [t for t in transactions if t['type'] == 'DEPOSIT']
    withdrawals = [t for t in transactions if t['type'] == 'WITHDRAWAL']
    pay_deposits = [t for t in transactions if t['type'] == 'PAY_DEPOSIT']
    pay_withdrawals = [t for t in transactions if t['type'] == 'PAY_WITHDRAWAL']
    
    print(f"Regular deposits: {len(deposits)}")
    print(f"Regular withdrawals: {len(withdrawals)}")
    print(f"Pay deposits: {len(pay_deposits)}")
    print(f"Pay withdrawals: {len(pay_withdrawals)}")
    
    # Verify counts
    assert len(deposits) == 1, f"Expected 1 regular deposit, got {len(deposits)}"
    assert len(withdrawals) == 1, f"Expected 1 regular withdrawal, got {len(withdrawals)}"
    assert len(pay_deposits) == 1, f"Expected 1 pay deposit, got {len(pay_deposits)}"
    assert len(pay_withdrawals) == 1, f"Expected 1 pay withdrawal, got {len(pay_withdrawals)}"
    
    # Check that transactions are sorted by timestamp
    timestamps = [t['timestamp'] for t in transactions]
    assert timestamps == sorted(timestamps), "Transactions should be sorted by timestamp"
    
    # Verify specific transaction details
    deposit = deposits[0]
    assert deposit['id'] == 'DEP_0x123456789abcdef'
    assert deposit['amount'] == 1000.0
    
    withdrawal = withdrawals[0]
    assert withdrawal['id'] == 'WD_withdrawal-id-123'
    assert withdrawal['amount'] == 500.0
    assert withdrawal['metadata']['transfer_type'] == 0  # External transfer
    
    pay_deposit = pay_deposits[0]
    assert pay_deposit['id'] == 'PAY_P_A1UBSK9SJNN71115'
    assert pay_deposit['amount'] == 2000.0
    assert pay_deposit['currency'] == 'USDC'
    
    pay_withdrawal = pay_withdrawals[0]
    assert pay_withdrawal['id'] == 'PAY_P_A1UPBE6WV3H71113'
    assert pay_withdrawal['amount'] == 300.0  # Should be positive (abs value)
    assert pay_withdrawal['currency'] == 'USDC'
    
    print("✅ All tests passed!")
    
    # Print detailed results
    print("\n📊 Transaction Details:")
    for txn in transactions:
        print(f"  {txn['type']}: {txn['amount']} {txn.get('currency', 'N/A')} - {txn['timestamp']}")
        if 'metadata' in txn:
            if 'contact_info' in txn['metadata']:
                contact = txn['metadata']['contact_info']
                print(f"    Contact: {contact['name']} ({contact.get('email', 'no email')})")
            elif 'transfer_type' in txn['metadata']:
                print(f"    Transfer type: {txn['metadata']['transfer_type']}")
    
    # Calculate net flow as it would be calculated in the main processing
    net_flow = 0
    for txn in transactions:
        if txn['type'] in ['DEPOSIT', 'PAY_DEPOSIT']:
            net_flow += txn['amount']
        elif txn['type'] in ['WITHDRAWAL', 'PAY_WITHDRAWAL']:
            net_flow -= txn['amount']
    
    print(f"\n💰 Net flow: {net_flow} (should be 1000 + 2000 - 500 - 300 = 2200)")
    assert abs(net_flow - 2200) < 0.01, f"Expected net flow of 2200, got {net_flow}"
    
    print("✅ Net flow calculation verified!")
    
    return True

if __name__ == "__main__":
    test_mixed_transactions()