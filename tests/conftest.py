"""
Pytest configuration and shared fixtures for Binance Portfolio Monitor tests.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, UTC
import os
import sys

# Add the project root to Python path so we can import from api/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing database operations."""
    mock_client = Mock()
    mock_table = Mock()
    mock_client.table.return_value = mock_table
    
    # Mock common database operations
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.upsert.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = Mock(data=[])
    
    return mock_client

@pytest.fixture
def mock_binance_client():
    """Mock Binance client for testing API operations."""
    mock_client = Mock()
    
    # Mock futures account response
    mock_client.futures_account.return_value = {
        'totalWalletBalance': '10000.00',
        'totalUnrealizedProfit': '500.00'
    }
    
    # Mock price ticker responses
    def mock_get_symbol_ticker(symbol):
        prices = {
            'BTCUSDT': {'price': '65000.00'},
            'ETHUSDT': {'price': '3500.00'}
        }
        return prices.get(symbol, {'price': '0.00'})
    
    mock_client.get_symbol_ticker.side_effect = mock_get_symbol_ticker
    
    # Mock deposit/withdrawal history
    mock_client.get_deposit_history.return_value = []
    mock_client.get_withdraw_history.return_value = []
    
    return mock_client

@pytest.fixture
def sample_account():
    """Sample account data for testing."""
    return {
        'id': 1,
        'account_name': 'Test Account',
        'api_key': 'test_api_key',
        'api_secret': 'test_api_secret',
        'benchmark_configs': {
            'id': 1,
            'account_id': 1,
            'btc_units': 0.15384615,  # 10000 / 2 / 65000
            'eth_units': 1.42857143,  # 10000 / 2 / 3500
            'rebalance_day': 0,
            'rebalance_hour': 12,
            'next_rebalance_timestamp': '2025-07-07T12:00:00+00:00'
        }
    }

@pytest.fixture
def sample_prices():
    """Sample price data for testing."""
    return {
        'BTCUSDT': 65000.00,
        'ETHUSDT': 3500.00
    }

@pytest.fixture
def sample_transactions():
    """Sample transaction data for testing."""
    return [
        {
            'id': 'DEP_12345',
            'type': 'DEPOSIT',
            'amount': 1000.0,
            'timestamp': '2025-07-02T10:00:00+00:00',
            'status': 'SUCCESS'
        },
        {
            'id': 'WD_67890',
            'type': 'WITHDRAWAL',
            'amount': 500.0,
            'timestamp': '2025-07-02T11:00:00+00:00',
            'status': 'SUCCESS'
        }
    ]

@pytest.fixture
def benchmark_config():
    """Sample benchmark configuration for testing."""
    return {
        'id': 1,
        'account_id': 1,
        'btc_units': 0.15384615,
        'eth_units': 1.42857143,
        'rebalance_day': 0,
        'rebalance_hour': 12,
        'next_rebalance_timestamp': '2025-07-07T12:00:00+00:00'
    }

@pytest.fixture
def current_time():
    """Fixed current time for testing."""
    return datetime(2025, 7, 2, 12, 0, 0, tzinfo=UTC)