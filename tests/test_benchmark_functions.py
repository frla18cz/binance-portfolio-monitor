"""
Unit tests for benchmark calculation and management functions.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, UTC

# Import functions from our API
from api.index import (
    calculate_benchmark_value,
    initialize_benchmark,
    rebalance_benchmark,
    calculate_next_rebalance_time,
    adjust_benchmark_for_cashflow
)


class TestCalculateBenchmarkValue:
    """Test the calculate_benchmark_value function."""
    
    def test_calculate_benchmark_value_basic(self, sample_prices):
        """Test basic benchmark value calculation."""
        config = {
            'btc_units': 0.1,  # 0.1 BTC
            'eth_units': 1.0   # 1.0 ETH
        }
        
        expected_value = (0.1 * 65000.00) + (1.0 * 3500.00)  # 6500 + 3500 = 10000
        result = calculate_benchmark_value(config, sample_prices)
        
        assert result == expected_value
        assert result == 10000.0
    
    def test_calculate_benchmark_value_zero_units(self, sample_prices):
        """Test benchmark calculation with zero units."""
        config = {
            'btc_units': 0.0,
            'eth_units': 0.0
        }
        
        result = calculate_benchmark_value(config, sample_prices)
        assert result == 0.0
    
    def test_calculate_benchmark_value_missing_units(self, sample_prices):
        """Test benchmark calculation with missing unit values."""
        config = {}  # No btc_units or eth_units
        
        result = calculate_benchmark_value(config, sample_prices)
        assert result == 0.0
    
    def test_calculate_benchmark_value_string_units(self, sample_prices):
        """Test benchmark calculation with string unit values."""
        config = {
            'btc_units': '0.5',
            'eth_units': '2.0'
        }
        
        expected_value = (0.5 * 65000.00) + (2.0 * 3500.00)  # 32500 + 7000 = 39500
        result = calculate_benchmark_value(config, sample_prices)
        
        assert result == expected_value
        assert result == 39500.0


class TestInitializeBenchmark:
    """Test the initialize_benchmark function."""
    
    @patch('api.index.datetime')
    def test_initialize_benchmark_basic(self, mock_datetime, mock_supabase_client, sample_prices, current_time):
        """Test basic benchmark initialization."""
        # Mock datetime.now(UTC) to return our fixed time
        mock_datetime.now.return_value = current_time
        mock_datetime.combine = datetime.combine
        mock_datetime.min = datetime.min
        
        # Mock database response
        mock_supabase_client.table().update().eq().execute.return_value = Mock(
            data=[{
                'btc_units': 0.07692308,  # 5000 / 65000
                'eth_units': 1.42857143,  # 5000 / 3500
                'next_rebalance_timestamp': '2025-07-07T12:00:00+00:00'
            }]
        )
        
        config = {
            'rebalance_day': 0,  # Monday
            'rebalance_hour': 12
        }
        
        result = initialize_benchmark(mock_supabase_client, config, 1, 10000.0, sample_prices)
        
        # Verify database update was called with correct values
        mock_supabase_client.table.assert_called_with('benchmark_configs')
        update_call = mock_supabase_client.table().update.call_args[0][0]
        
        # Check BTC units calculation: 5000 / 65000 = 0.07692308
        assert abs(update_call['btc_units'] - 0.07692308) < 0.000001
        
        # Check ETH units calculation: 5000 / 3500 = 1.42857143
        assert abs(update_call['eth_units'] - 1.42857143) < 0.000001
        
        # Verify next rebalance timestamp is set
        assert 'next_rebalance_timestamp' in update_call
        
        # Verify account_id filter
        mock_supabase_client.table().update().eq.assert_called_with('account_id', 1)


class TestCalculateNextRebalanceTime:
    """Test the calculate_next_rebalance_time function."""
    
    def test_calculate_next_rebalance_same_day_before_hour(self):
        """Test rebalance calculation for same day before rebalance hour."""
        # Tuesday at 10 AM, rebalance at 12 PM
        now = datetime(2025, 7, 1, 10, 0, 0, tzinfo=UTC)  # Tuesday
        rebalance_day = 1  # Tuesday
        rebalance_hour = 12
        
        result = calculate_next_rebalance_time(now, rebalance_day, rebalance_hour)
        
        # Should be same day at 12 PM
        expected = datetime(2025, 7, 1, 12, 0, 0, tzinfo=UTC)
        assert result.replace(tzinfo=UTC) == expected
    
    def test_calculate_next_rebalance_same_day_after_hour(self):
        """Test rebalance calculation for same day after rebalance hour."""
        # Tuesday at 2 PM, rebalance at 12 PM
        now = datetime(2025, 7, 1, 14, 0, 0, tzinfo=UTC)  # Tuesday
        rebalance_day = 1  # Tuesday  
        rebalance_hour = 12
        
        result = calculate_next_rebalance_time(now, rebalance_day, rebalance_hour)
        
        # Should be next Tuesday at 12 PM
        expected = datetime(2025, 7, 8, 12, 0, 0, tzinfo=UTC)
        assert result.replace(tzinfo=UTC) == expected
    
    def test_calculate_next_rebalance_different_day(self):
        """Test rebalance calculation for different day."""
        # Wednesday, rebalance on Monday
        now = datetime(2025, 7, 2, 10, 0, 0, tzinfo=UTC)  # Wednesday
        rebalance_day = 0  # Monday
        rebalance_hour = 12
        
        result = calculate_next_rebalance_time(now, rebalance_day, rebalance_hour)
        
        # Should be next Monday at 12 PM
        expected = datetime(2025, 7, 7, 12, 0, 0, tzinfo=UTC)
        assert result.replace(tzinfo=UTC) == expected


class TestAdjustBenchmarkForCashflow:
    """Test the adjust_benchmark_for_cashflow function."""
    
    def test_adjust_benchmark_deposit(self, mock_supabase_client, sample_prices):
        """Test benchmark adjustment for deposits."""
        config = {
            'btc_units': 0.1,
            'eth_units': 1.0
        }
        
        # Mock successful database operations
        mock_supabase_client.table().update().eq().execute.return_value = Mock()
        mock_supabase_client.table().insert().execute.return_value = Mock()
        
        processed_txns = [
            {
                'account_id': 1,
                'transaction_id': 'DEP_12345',
                'transaction_type': 'DEPOSIT',
                'amount': 1000.0,
                'timestamp': '2025-07-02T10:00:00+00:00',
                'status': 'SUCCESS'
            }
        ]
        
        result = adjust_benchmark_for_cashflow(
            mock_supabase_client, config, 1, 1000.0, sample_prices, processed_txns
        )
        
        # For $1000 deposit, should add $500 to BTC and $500 to ETH
        # BTC: 0.1 + (500/65000) = 0.1 + 0.00769231 = 0.10769231
        # ETH: 1.0 + (500/3500) = 1.0 + 0.14285714 = 1.14285714
        
        expected_btc = 0.1 + (500.0 / 65000.0)
        expected_eth = 1.0 + (500.0 / 3500.0)
        
        assert abs(result['btc_units'] - expected_btc) < 0.000001
        assert abs(result['eth_units'] - expected_eth) < 0.000001
    
    def test_adjust_benchmark_withdrawal(self, mock_supabase_client, sample_prices):
        """Test benchmark adjustment for withdrawals."""
        config = {
            'btc_units': 0.1,      # Worth $6500
            'eth_units': 1.0       # Worth $3500
        }
        # Total benchmark value: $10000
        
        # Mock successful database operations  
        mock_supabase_client.table().update().eq().execute.return_value = Mock()
        mock_supabase_client.table().insert().execute.return_value = Mock()
        
        processed_txns = [
            {
                'account_id': 1,
                'transaction_id': 'WD_67890',
                'transaction_type': 'WITHDRAWAL',
                'amount': 1000.0,
                'timestamp': '2025-07-02T11:00:00+00:00',
                'status': 'SUCCESS'
            }
        ]
        
        result = adjust_benchmark_for_cashflow(
            mock_supabase_client, config, 1, -1000.0, sample_prices, processed_txns
        )
        
        # For $1000 withdrawal from $10000 portfolio (10% reduction)
        # BTC: 0.1 * (1 - 0.1) = 0.09
        # ETH: 1.0 * (1 - 0.1) = 0.9
        
        assert abs(result['btc_units'] - 0.09) < 0.000001
        assert abs(result['eth_units'] - 0.9) < 0.000001
    
    def test_adjust_benchmark_zero_cashflow(self, mock_supabase_client, sample_prices):
        """Test benchmark adjustment with zero net cashflow."""
        config = {
            'btc_units': 0.1,
            'eth_units': 1.0
        }
        
        result = adjust_benchmark_for_cashflow(
            mock_supabase_client, config, 1, 0.0, sample_prices, []
        )
        
        # No change expected
        assert result['btc_units'] == 0.1
        assert result['eth_units'] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])