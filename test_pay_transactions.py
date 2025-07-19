#!/usr/bin/env python3
"""
Test script for Binance Pay transaction detection.
Tests the enhanced fetch_new_transactions function with pay transactions.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from api.index import fetch_new_transactions
from api.logger import LogCategory

def test_pay_transactions():
    """Test that fetch_new_transactions correctly handles Binance Pay transactions."""
    
    # Create mock logger
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    
    # Create mock Binance client
    mock_client = Mock()
    
    # Mock regular withdrawal/deposit history (empty for this test)
    mock_client.get_deposit_history.return_value = []
    mock_client.get_withdraw_history.return_value = []
    
    # Mock Binance Pay transactions response
    mock_pay_response = {
        "code": "000000",
        "message": "success",
        "data": [
            {
                "orderType": "C2C",
                "transactionId": "P_A1UBSK9SJNN71115",
                "transactionTime": "1719949467394",  # 2024-07-02 14:14:27
                "amount": "6000",  # Positive = incoming
                "currency": "USDC",
                "walletType": "2",
                "payerInfo": {
                    "name": "User-19af8",
                    "binanceId": "38755365",
                    "email": "sender@example.com"
                }
            },
            {
                "orderType": "C2C",
                "transactionId": "P_A1UPBE6WV3H71113",
                "transactionTime": "1721327863518",  # 2024-07-18 14:37:43
                "amount": "-10",  # Negative = outgoing
                "currency": "USDC",
                "walletType": "2",
                "receiverInfo": {
                    "name": "User-Tomas_",
                    "type": "USER",
                    "email": "rozirozi@seznam.cz",
                    "accountId": "235656193"
                }
            }
        ],
        "success": True
    }
    
    # Mock the _request method for pay transactions
    mock_client._request.return_value = mock_pay_response
    
    # Test start time (before both transactions)
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
    
    # Check that we have 2 pay transactions
    pay_deposits = [t for t in transactions if t['type'] == 'PAY_DEPOSIT']
    pay_withdrawals = [t for t in transactions if t['type'] == 'PAY_WITHDRAWAL']
    
    print(f"Pay deposits: {len(pay_deposits)}")
    print(f"Pay withdrawals: {len(pay_withdrawals)}")
    
    assert len(pay_deposits) == 1, f"Expected 1 pay deposit, got {len(pay_deposits)}"
    assert len(pay_withdrawals) == 1, f"Expected 1 pay withdrawal, got {len(pay_withdrawals)}"
    
    # Check deposit details
    deposit = pay_deposits[0]
    assert deposit['id'] == 'PAY_P_A1UBSK9SJNN71115'
    assert deposit['amount'] == 6000.0
    assert deposit['currency'] == 'USDC'
    assert deposit['metadata']['contact_info']['name'] == 'User-19af8'
    assert deposit['metadata']['contact_info']['email'] == 'sender@example.com'
    
    # Check withdrawal details
    withdrawal = pay_withdrawals[0]
    assert withdrawal['id'] == 'PAY_P_A1UPBE6WV3H71113'
    assert withdrawal['amount'] == 10.0  # Should be positive (abs value)
    assert withdrawal['currency'] == 'USDC'
    assert withdrawal['metadata']['contact_info']['name'] == 'User-Tomas_'
    assert withdrawal['metadata']['contact_info']['email'] == 'rozirozi@seznam.cz'
    
    print("✅ All tests passed!")
    
    # Print detailed results
    print("\n📊 Transaction Details:")
    for txn in transactions:
        print(f"  {txn['type']}: {txn['amount']} {txn['currency']}")
        if 'metadata' in txn and 'contact_info' in txn['metadata']:
            contact = txn['metadata']['contact_info']
            print(f"    Contact: {contact['name']} ({contact.get('email', 'no email')})")
    
    # Verify API calls were made
    mock_client.get_deposit_history.assert_called_once()
    mock_client.get_withdraw_history.assert_called_once()
    mock_client._request.assert_called_once_with('GET', 'sapi/v1/pay/transactions', True, {})
    
    print("\n✅ All API calls verified!")
    
    return True

if __name__ == "__main__":
    test_pay_transactions()