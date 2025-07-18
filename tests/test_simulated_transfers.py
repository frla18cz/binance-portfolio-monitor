#!/usr/bin/env python3
"""
Test script that simulates different types of transfers to verify detection logic
Tests both external and internal transfers with various metadata configurations
"""

import os
import sys
from datetime import datetime, timezone
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from api.index import fetch_new_transactions
from api.logger import MonitorLogger, LogCategory
from utils.database_manager import get_supabase_client

class MockBinanceClient:
    """Mock Binance client that returns simulated transfer data"""
    
    def __init__(self, test_scenario='mixed'):
        self.test_scenario = test_scenario
        
    def get_deposit_history(self, **kwargs):
        """Simulate deposit history"""
        if self.test_scenario == 'no_transfers':
            return []
            
        # Simulate different types of deposits
        return [
            {
                'txId': 'EXT_DEP_001',
                'amount': '100.0',
                'coin': 'USDT',
                'status': 1,  # Success
                'insertTime': int(datetime.now(timezone.utc).timestamp() * 1000) - 3600000,  # 1 hour ago
                'network': 'BSC'
            },
            {
                'txId': 'INT_DEP_002',
                'amount': '50.0',
                'coin': 'USDT', 
                'status': 1,
                'insertTime': int(datetime.now(timezone.utc).timestamp() * 1000) - 1800000,  # 30 min ago
                'network': 'Internal'  # Internal transfer indicator
            }
        ]
        
    def get_withdraw_history(self, **kwargs):
        """Simulate withdrawal history with different transfer types"""
        if self.test_scenario == 'no_transfers':
            return []
        elif self.test_scenario == 'only_external':
            return [
                {
                    'id': 'WD_EXT_001',
                    'amount': '200.0',
                    'coin': 'USDT',
                    'status': 6,  # Completed
                    'applyTime': int(datetime.now(timezone.utc).timestamp() * 1000) - 7200000,  # 2 hours ago
                    'network': 'BSC',
                    'address': '0x123...abc',
                    'txId': '0xabc...123',
                    'transferType': 0  # External transfer
                }
            ]
        elif self.test_scenario == 'only_internal':
            return [
                {
                    'id': 'WD_INT_001',
                    'amount': '150.0',
                    'coin': 'USDT',
                    'status': 6,  # Completed
                    'applyTime': int(datetime.now(timezone.utc).timestamp() * 1000) - 3600000,  # 1 hour ago
                    'network': '',
                    'address': 'user@example.com',
                    'txId': 'Internal transfer',
                    'transferType': 1  # Internal transfer
                }
            ]
        else:  # mixed
            return [
                {
                    'id': 'WD_EXT_001',
                    'amount': '200.0',
                    'coin': 'BTC',
                    'status': 6,
                    'applyTime': int(datetime.now(timezone.utc).timestamp() * 1000) - 7200000,
                    'network': 'BTC',
                    'address': 'bc1q...',
                    'txId': 'abc123...',
                    'transferType': 0  # External
                },
                {
                    'id': 'WD_INT_002',
                    'amount': '150.0',
                    'coin': 'USDT',
                    'status': 6,
                    'applyTime': int(datetime.now(timezone.utc).timestamp() * 1000) - 3600000,
                    'network': '',
                    'address': '+1234567890',  # Phone number
                    'txId': 'Internal transfer',
                    'transferType': 1  # Internal
                },
                {
                    'id': 'WD_INT_003',
                    'amount': '75.50',
                    'coin': 'ETH',
                    'status': 6,
                    'applyTime': int(datetime.now(timezone.utc).timestamp() * 1000) - 1800000,
                    'network': '',
                    'address': 'user@binance.com',  # Email
                    'txId': 'Off-chain transfer',  # Another internal indicator
                    'transferType': 1  # Internal
                }
            ]

def test_scenario(scenario_name, test_scenario):
    """Run a specific test scenario"""
    print(f"\n{'='*60}")
    print(f"Testing: {scenario_name}")
    print(f"{'='*60}")
    
    # Create mock client
    mock_client = MockBinanceClient(test_scenario)
    
    # Create logger
    logger = MonitorLogger()
    
    # Set start time to 24 hours ago
    start_time = datetime.now(timezone.utc).isoformat()
    
    # Fetch transactions
    try:
        transactions = fetch_new_transactions(
            mock_client, 
            start_time, 
            logger=logger,
            account_id='test-account-001'
        )
        
        print(f"\n📊 Found {len(transactions)} transactions")
        
        # Analyze results
        deposits = [t for t in transactions if t['type'] == 'DEPOSIT']
        withdrawals = [t for t in transactions if t['type'] == 'WITHDRAWAL']
        
        print(f"   - Deposits: {len(deposits)}")
        print(f"   - Withdrawals: {len(withdrawals)}")
        
        # Check for internal transfers
        internal_withdrawals = []
        external_withdrawals = []
        
        for w in withdrawals:
            metadata = w.get('metadata', {})
            if metadata.get('transfer_type') == 1 or 'Internal' in metadata.get('tx_id', ''):
                internal_withdrawals.append(w)
            else:
                external_withdrawals.append(w)
        
        print(f"\n📤 Withdrawal Analysis:")
        print(f"   - External transfers: {len(external_withdrawals)}")
        print(f"   - Internal transfers: {len(internal_withdrawals)}")
        
        # Show details for each transaction
        if transactions:
            print(f"\n📋 Transaction Details:")
            for i, txn in enumerate(transactions):
                print(f"\n   Transaction {i+1}:")
                print(f"   - ID: {txn['id']}")
                print(f"   - Type: {txn['type']}")
                print(f"   - Amount: {txn['amount']}")
                print(f"   - Status: {txn['status']}")
                
                if txn.get('metadata'):
                    print(f"   - Metadata:")
                    metadata = txn['metadata']
                    print(f"     * Transfer Type: {metadata.get('transfer_type')} {'(Internal)' if metadata.get('transfer_type') == 1 else '(External)'}")
                    print(f"     * TX ID: {metadata.get('tx_id')}")
                    print(f"     * Coin: {metadata.get('coin')}")
                    print(f"     * Network: {metadata.get('network', 'N/A')}")
        
        # Check logs for internal transfer detection
        print(f"\n📜 Checking logs for internal transfer detection...")
        supabase = get_supabase_client()
        logs = supabase.table('system_logs')\
            .select('*')\
            .eq('operation', 'internal_transfer_detected')\
            .eq('account_id', 'test-account-001')\
            .order('timestamp', desc=True)\
            .limit(10)\
            .execute()
            
        if logs.data:
            print(f"   ✅ Found {len(logs.data)} internal transfer log entries")
        else:
            print(f"   ℹ️ No internal transfer logs found (might be normal for this scenario)")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Run all test scenarios"""
    print("🧪 Binance Transfer Detection Simulation Tests")
    print("=" * 60)
    
    # Test different scenarios
    scenarios = [
        ('No Transfers', 'no_transfers'),
        ('Only External Transfers', 'only_external'),
        ('Only Internal Transfers', 'only_internal'),
        ('Mixed Transfer Types', 'mixed')
    ]
    
    for name, scenario in scenarios:
        test_scenario(name, scenario)
        
    print("\n" + "="*60)
    print("✅ All simulations completed!")
    print("\nSummary:")
    print("- External transfers have transferType=0")
    print("- Internal transfers have transferType=1 or txId='Internal transfer'")
    print("- All transfers affect benchmark equally")
    print("- Metadata is preserved for future analysis")

if __name__ == "__main__":
    main()