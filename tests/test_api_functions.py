"""
Unit tests for API integration functions (Binance API, price fetching, NAV calculation).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from binance.exceptions import BinanceAPIException

# Import functions from our API
from api.index import (
    get_prices,
    get_futures_account_nav,
    fetch_new_transactions,
    process_deposits_withdrawals
)


class TestGetPrices:
    """Test the get_prices function."""
    
    def test_get_prices_success(self, mock_binance_client):
        """Test successful price fetching."""
        result = get_prices(mock_binance_client)
        
        expected = {
            'BTCUSDT': 65000.00,
            'ETHUSDT': 3500.00
        }
        
        assert result == expected
        
        # Verify API calls were made
        assert mock_binance_client.get_symbol_ticker.call_count == 2
        mock_binance_client.get_symbol_ticker.assert_any_call(symbol='BTCUSDT')
        mock_binance_client.get_symbol_ticker.assert_any_call(symbol='ETHUSDT')
    
    def test_get_prices_api_error(self):
        """Test price fetching with API error."""
        mock_client = Mock()
        
        # Create a proper mock response for BinanceAPIException
        mock_response = Mock()
        mock_response.text = '{"code": -1001, "msg": "Invalid symbol"}'
        
        mock_client.get_symbol_ticker.side_effect = BinanceAPIException(
            mock_response, -1001, '{"code": -1001, "msg": "Invalid symbol"}'
        )
        
        result = get_prices(mock_client)
        
        assert result is None
    
    def test_get_prices_network_error(self):
        """Test price fetching with network error."""
        mock_client = Mock()
        mock_client.get_symbol_ticker.side_effect = Exception("Network error")
        
        result = get_prices(mock_client)
        
        assert result is None


class TestGetFuturesAccountNav:
    """Test the get_futures_account_nav function."""
    
    def test_get_nav_success(self, mock_binance_client):
        """Test successful NAV calculation."""
        result = get_futures_account_nav(mock_binance_client)
        
        # Expected: 10000.00 + 500.00 = 10500.00
        assert result == 10500.00
        
        # Verify API call was made
        mock_binance_client.futures_account.assert_called_once()
    
    def test_get_nav_api_error(self):
        """Test NAV calculation with API error."""
        mock_client = Mock()
        
        # Create a proper mock response for BinanceAPIException
        mock_response = Mock()
        mock_response.text = '{"code": -1001, "msg": "Invalid API key"}'
        
        mock_client.futures_account.side_effect = BinanceAPIException(
            mock_response, -1001, '{"code": -1001, "msg": "Invalid API key"}'
        )
        
        result = get_futures_account_nav(mock_client)
        
        assert result is None
    
    def test_get_nav_zero_values(self):
        """Test NAV calculation with zero values."""
        mock_client = Mock()
        mock_client.futures_account.return_value = {
            'totalWalletBalance': '0.00',
            'totalUnrealizedProfit': '0.00'
        }
        
        result = get_futures_account_nav(mock_client)
        
        assert result == 0.0
    
    def test_get_nav_negative_unrealized(self):
        """Test NAV calculation with negative unrealized profit."""
        mock_client = Mock()
        mock_client.futures_account.return_value = {
            'totalWalletBalance': '10000.00',
            'totalUnrealizedProfit': '-1500.00'
        }
        
        result = get_futures_account_nav(mock_client)
        
        # Expected: 10000.00 + (-1500.00) = 8500.00
        assert result == 8500.00


class TestFetchNewTransactions:
    """Test the fetch_new_transactions function."""
    
    @patch('api.index.datetime')
    def test_fetch_transactions_success(self, mock_datetime):
        """Test successful transaction fetching."""
        # Mock datetime.fromisoformat to parse timestamps
        mock_datetime.fromisoformat.return_value = Mock()
        mock_datetime.fromisoformat.return_value.timestamp.return_value = 1719936000  # Mock timestamp
        mock_datetime.fromtimestamp.return_value = Mock()
        mock_datetime.fromtimestamp.return_value.isoformat.return_value = '2025-07-02T12:00:00+00:00'
        
        mock_client = Mock()
        
        # Mock deposit history
        mock_client.get_deposit_history.return_value = [
            {
                'txId': '12345',
                'amount': '1000.00',
                'insertTime': 1719936000000,  # Mock timestamp in milliseconds
                'status': 1  # Success
            }
        ]
        
        # Mock withdrawal history
        mock_client.get_withdraw_history.return_value = [
            {
                'id': '67890',
                'amount': '500.00',
                'applyTime': 1719936000000,  # Mock timestamp in milliseconds
                'status': 1  # Success
            }
        ]
        
        result = fetch_new_transactions(mock_client, '2025-07-01T12:00:00+00:00')
        
        assert len(result) == 2
        
        # Check deposit transaction
        deposit = next(t for t in result if t['type'] == 'DEPOSIT')
        assert deposit['id'] == 'DEP_12345'
        assert deposit['amount'] == '1000.00'
        assert deposit['status'] == 'SUCCESS'
        
        # Check withdrawal transaction
        withdrawal = next(t for t in result if t['type'] == 'WITHDRAWAL')
        assert withdrawal['id'] == 'WD_67890'
        assert withdrawal['amount'] == '500.00'
        assert withdrawal['status'] == 'SUCCESS'
    
    def test_fetch_transactions_api_error(self):
        """Test transaction fetching with API error."""
        mock_client = Mock()
        
        # Create a proper mock response for BinanceAPIException
        mock_response = Mock()
        mock_response.text = '{"code": -1001, "msg": "Invalid API key"}'
        
        mock_client.get_deposit_history.side_effect = BinanceAPIException(
            mock_response, -1001, '{"code": -1001, "msg": "Invalid API key"}'
        )
        
        result = fetch_new_transactions(mock_client, '2025-07-01T12:00:00+00:00')
        
        assert result == []
    
    def test_fetch_transactions_empty_response(self):
        """Test transaction fetching with empty response."""
        mock_client = Mock()
        mock_client.get_deposit_history.return_value = []
        mock_client.get_withdraw_history.return_value = []
        
        result = fetch_new_transactions(mock_client, '2025-07-01T12:00:00+00:00')
        
        assert result == []
    
    @patch('api.index.datetime')
    def test_fetch_transactions_filters_pending(self, mock_datetime):
        """Test that pending transactions are filtered out."""
        # Mock datetime functions
        mock_datetime.fromisoformat.return_value = Mock()
        mock_datetime.fromisoformat.return_value.timestamp.return_value = 1719936000
        mock_datetime.fromtimestamp.return_value = Mock()
        mock_datetime.fromtimestamp.return_value.isoformat.return_value = '2025-07-02T12:00:00+00:00'
        
        mock_client = Mock()
        
        # Mock deposit history with both success and pending
        mock_client.get_deposit_history.return_value = [
            {
                'txId': '12345',
                'amount': '1000.00',
                'insertTime': 1719936000000,
                'status': 1  # Success
            },
            {
                'txId': '12346',
                'amount': '2000.00',
                'insertTime': 1719936000000,
                'status': 0  # Pending
            }
        ]
        
        mock_client.get_withdraw_history.return_value = []
        
        result = fetch_new_transactions(mock_client, '2025-07-01T12:00:00+00:00')
        
        # Should only return the successful transaction
        assert len(result) == 1
        assert result[0]['id'] == 'DEP_12345'


class TestProcessDepositsWithdrawals:
    """Test the process_deposits_withdrawals function."""
    
    @patch('api.index.get_last_processed_time')
    @patch('api.index.fetch_new_transactions')
    @patch('api.index.adjust_benchmark_for_cashflow')
    def test_process_no_new_transactions(self, mock_adjust, mock_fetch, mock_get_time, 
                                       mock_supabase_client, mock_binance_client, benchmark_config):
        """Test processing when there are no new transactions."""
        mock_get_time.return_value = '2025-07-01T12:00:00+00:00'
        mock_fetch.return_value = []
        
        result = process_deposits_withdrawals(
            mock_supabase_client, mock_binance_client, 1, benchmark_config, {}
        )
        
        # Should return original config unchanged
        assert result == benchmark_config
        
        # adjust_benchmark_for_cashflow should not be called
        mock_adjust.assert_not_called()
    
    @patch('api.index.get_last_processed_time')
    @patch('api.index.fetch_new_transactions')
    @patch('api.index.adjust_benchmark_for_cashflow')
    def test_process_with_net_cashflow(self, mock_adjust, mock_fetch, mock_get_time,
                                     mock_supabase_client, mock_binance_client, 
                                     benchmark_config, sample_transactions):
        """Test processing with net cashflow changes."""
        mock_get_time.return_value = '2025-07-01T12:00:00+00:00'
        mock_fetch.return_value = sample_transactions
        
        updated_config = benchmark_config.copy()
        updated_config['btc_units'] = 0.2
        mock_adjust.return_value = updated_config
        
        result = process_deposits_withdrawals(
            mock_supabase_client, mock_binance_client, 1, benchmark_config, {}
        )
        
        # Should return updated config
        assert result == updated_config
        
        # adjust_benchmark_for_cashflow should be called with net flow of +500 (1000 - 500)
        mock_adjust.assert_called_once()
        call_args = mock_adjust.call_args[0]
        assert call_args[2] == 1  # account_id
        assert call_args[3] == 500.0  # net_flow (1000 deposit - 500 withdrawal)
    
    @patch('api.index.get_last_processed_time')
    @patch('api.index.fetch_new_transactions')
    def test_process_api_error_graceful_fallback(self, mock_fetch, mock_get_time,
                                               mock_supabase_client, mock_binance_client, 
                                               benchmark_config):
        """Test graceful handling of API errors."""
        mock_get_time.return_value = '2025-07-01T12:00:00+00:00'
        mock_fetch.side_effect = Exception("API Error")
        
        result = process_deposits_withdrawals(
            mock_supabase_client, mock_binance_client, 1, benchmark_config, {}
        )
        
        # Should return original config on error
        assert result == benchmark_config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])