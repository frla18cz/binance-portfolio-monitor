"""
Integration tests for complete account processing flow.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC

# Import main processing functions
from api.index import process_single_account, process_all_accounts
from api.demo_mode import DemoModeController
from api.logger import LogCategory


class TestAccountProcessingIntegration:
    """Test complete account processing integration."""

    @patch('api.index.get_demo_controller')
    @patch('api.index.save_history')
    @patch('api.index.process_deposits_withdrawals')
    @patch('api.index.supabase')  # Mock the global supabase client
    def test_complete_account_processing_flow(self, mock_supabase_global, mock_process_deposits, mock_save_history, mock_get_demo_controller,
                                            mock_supabase_client, sample_account, sample_prices):
        """Test complete account processing from start to finish."""

        # Mock a real DemoController instance that returns our mock client
        mock_demo_controller = DemoModeController()
        mock_binance_client = Mock()
        mock_demo_controller.get_binance_client = Mock(return_value=mock_binance_client)
        mock_get_demo_controller.return_value = mock_demo_controller

        # Mock get_prices function behavior
        def mock_get_symbol_ticker(symbol):
            prices = {
                'BTCUSDT': {'price': '65000.00'},
                'ETHUSDT': {'price': '3500.00'}
            }
            return prices.get(symbol, {'price': '0.00'})

        mock_binance_client.get_symbol_ticker.side_effect = mock_get_symbol_ticker

        # Mock futures_account response
        mock_binance_client.futures_account.return_value = {
            'totalWalletBalance': '10000.00',
            'totalUnrealizedProfit': '500.00'
        }

        # Mock process_deposits_withdrawals to return config unchanged
        mock_process_deposits.return_value = sample_account['benchmark_configs']

        # Mock save_history
        mock_save_history.return_value = None

        # Execute the complete processing flow
        process_single_account(sample_account)

        # Verify Binance client was created with correct credentials
        mock_demo_controller.get_binance_client.assert_called_once_with(
            sample_account['api_key'],
            sample_account['api_secret'],
            tld='com'
        )

        # Verify price fetching was called for both symbols
        assert mock_binance_client.get_symbol_ticker.call_count == 2
        mock_binance_client.get_symbol_ticker.assert_any_call(symbol='BTCUSDT')
        mock_binance_client.get_symbol_ticker.assert_any_call(symbol='ETHUSDT')

        # Verify NAV calculation was called
        mock_binance_client.futures_account.assert_called_once()

        # Verify deposit/withdrawal processing was called
        mock_process_deposits.assert_called_once()

        # Verify historical data was saved
        mock_save_history.assert_called_once()

        # Check the arguments passed to save_history
        save_args = mock_save_history.call_args[0]
        assert save_args[1] == sample_account['id']  # account_id
        assert save_args[2] == 10500.00  # nav (10000 + 500)

        # Benchmark value should be calculated from config
        expected_benchmark = (0.15384615 * 65000.00) + (1.42857143 * 3500.00)
        assert abs(save_args[3] - expected_benchmark) < 1.0  # benchmark_value (with tolerance)

    @patch('api.index.get_demo_controller')
    def test_account_processing_missing_config(self, mock_get_demo_controller, mock_supabase_client):
        """Test account processing with missing benchmark config."""

        mock_binance_client = Mock()
        mock_get_demo_controller.return_value.get_binance_client = Mock(return_value=mock_binance_client)

        account_without_config = {
            'id': 1,
            'account_name': 'Test Account',
            'api_key': 'test_api_key',
            'api_secret': 'test_api_secret',
            'benchmark_configs': None  # Missing config
        }

        # Should handle gracefully and exit early
        process_single_account(account_without_config)

        # Binance client should not be created
        mock_get_demo_controller.return_value.get_binance_client.assert_not_called()

    @patch('api.index.get_demo_controller')
    def test_account_processing_incomplete_data(self, mock_get_demo_controller, mock_supabase_client):
        """Test account processing with incomplete account data."""

        mock_binance_client = Mock()
        mock_get_demo_controller.return_value.get_binance_client = Mock(return_value=mock_binance_client)

        incomplete_account = {
            'id': 1,
            'account_name': 'Test Account',
            'api_key': None,  # Missing API key
            'api_secret': 'test_api_secret',
            'benchmark_configs': {'id': 1}
        }

        # Should handle gracefully and exit early
        process_single_account(incomplete_account)

        # Binance client should not be created
        mock_get_demo_controller.return_value.get_binance_client.assert_not_called()

    @patch('api.index.get_demo_controller')
    @patch('api.index.get_prices')
    def test_account_processing_api_failure(self, mock_get_prices, mock_get_demo_controller,
                                          mock_supabase_client, sample_account):
        """Test account processing with API failures."""

        mock_binance_client = Mock()
        mock_get_demo_controller.return_value.get_binance_client = Mock(return_value=mock_binance_client)

        # Mock API failure
        mock_get_prices.return_value = None

        # Should handle gracefully and exit early
        process_single_account(sample_account)

        # Should still create Binance client
        mock_get_demo_controller.return_value.get_binance_client.assert_called_once()

        # Should attempt to get prices
        mock_get_prices.assert_called_once()

    @patch('api.index.get_demo_controller')
    @patch('api.index.get_prices')
    @patch('api.index.get_futures_account_nav')
    def test_account_processing_nav_failure(self, mock_get_nav, mock_get_prices, mock_get_demo_controller,
                                          mock_supabase_client, sample_account, sample_prices):
        """Test account processing with NAV calculation failure."""

        mock_binance_client = Mock()
        mock_get_demo_controller.return_value.get_binance_client = Mock(return_value=mock_binance_client)

        # Mock successful price fetch but failed NAV
        mock_get_prices.return_value = sample_prices
        mock_get_nav.return_value = None

        # Should handle gracefully and exit early
        process_single_account(sample_account)

        # Should get prices and attempt NAV calculation
        mock_get_prices.assert_called_once()
        mock_get_nav.assert_called_once()

    @patch('api.index.get_logger')
    @patch('api.index.get_demo_controller')
    def test_process_all_accounts_no_accounts(self, mock_get_demo_controller, mock_get_logger):
        """Test process_all_accounts when no accounts are in the database."""
        # Arrange
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_db_client = Mock()
        mock_db_client.table().select().execute.return_value = Mock(data=[])
        
        mock_demo_controller = Mock()
        mock_demo_controller.get_supabase_client.return_value = mock_db_client
        mock_get_demo_controller.return_value = mock_demo_controller

        # Act
        process_all_accounts()

        # Assert
        mock_logger.warning.assert_called_once_with(
            LogCategory.SYSTEM, "no_accounts", "No accounts found in database"
        )

    @patch('api.index.get_logger')
    @patch('api.index.process_single_account')
    @patch('api.index.get_demo_controller')
    def test_process_all_accounts_single_account_failure(self, mock_get_demo_controller, mock_process_single, mock_get_logger, sample_account):
        """Test that process_all_accounts handles exceptions in process_single_account."""
        # Arrange
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_db_client = Mock()
        mock_db_client.table().select().execute.return_value = Mock(data=[sample_account])

        mock_demo_controller = Mock()
        mock_demo_controller.get_supabase_client.return_value = mock_db_client
        mock_get_demo_controller.return_value = mock_demo_controller

        error_message = "Test exception"
        mock_process_single.side_effect = Exception(error_message)

        # Act
        process_all_accounts()

        # Assert
        mock_process_single.assert_called_once_with(sample_account)
        mock_logger.error.assert_called_once_with(
            LogCategory.ACCOUNT_PROCESSING, 
            "process_error", 
            f"Failed to process account {sample_account['account_name']}: {error_message}",
            account_id=sample_account['id'], 
            account_name=sample_account['account_name'], 
            error=error_message
        )

    @patch('api.index.get_demo_controller')
    @patch('api.index.get_prices')
    def test_process_single_account_config_as_list(self, mock_get_prices, mock_get_demo_controller, sample_account):
        """Test that process_single_account handles config as a list."""
        # Arrange
        mock_binance_client = Mock()
        mock_demo_controller = Mock()
        mock_demo_controller.get_binance_client.return_value = mock_binance_client
        mock_get_demo_controller.return_value = mock_demo_controller

        account_with_list_config = sample_account.copy()
        account_with_list_config['benchmark_configs'] = [sample_account['benchmark_configs']]

        mock_get_prices.return_value = {'BTCUSDT': 65000.0, 'ETHUSDT': 3500.0}
        mock_binance_client.futures_account.return_value = {
            'totalWalletBalance': '10000.00',
            'totalUnrealizedProfit': '500.00'
        }

        # Act & Assert (should not raise an error)
        try:
            process_single_account(account_with_list_config)
        except Exception as e:
            pytest.fail(f"process_single_account raised an exception with list config: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])