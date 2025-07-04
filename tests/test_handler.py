"""
Unit tests for the Vercel handler (api/index.py).
"""
import pytest
from unittest.mock import Mock, patch
from http.server import BaseHTTPRequestHandler
from io import BytesIO

# Import the handler class and LogCategory
from api.index import handler, process_all_accounts
from api.logger import LogCategory


class TestVercelHandler:
    """Test the Vercel handler class (api/index.py)."""

    @patch('api.index.get_logger')
    @patch('api.index.process_all_accounts')
    def test_do_get_success(self, mock_process_all_accounts, mock_get_logger):
        """Test successful execution of do_GET method."""
        # Arrange
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Mock the BaseHTTPRequestHandler methods
        mock_request_handler = Mock(spec=BaseHTTPRequestHandler)
        mock_request_handler.wfile = BytesIO() # Simulate wfile as a byte stream

        # Act
        handler.do_GET(mock_request_handler)

        # Assert
        mock_process_all_accounts.assert_called_once() # process_all_accounts should be called

        # Verify logger calls
        mock_logger.info.assert_any_call(LogCategory.SYSTEM, "cron_trigger", "Cron job triggered - starting monitoring process")
        mock_logger.info.assert_any_call(LogCategory.SYSTEM, "cron_complete", "Monitoring process completed successfully")

        # Verify HTTP response
        mock_request_handler.send_response.assert_called_once_with(200)
        mock_request_handler.send_header.assert_any_call('Content-type','text/plain')
        mock_request_handler.end_headers.assert_called_once()
        assert mock_request_handler.wfile.getvalue() == b'Monitoring process completed successfully.'

    @patch('api.index.get_logger')
    @patch('api.index.process_all_accounts')
    @patch('api.index.traceback.print_exc')
    def test_do_get_failure(self, mock_print_exc, mock_process_all_accounts, mock_get_logger):
        """Test do_GET method when process_all_accounts raises an exception."""
        # Arrange
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        error_message = "Simulated processing error"
        mock_process_all_accounts.side_effect = Exception(error_message)

        # Mock the BaseHTTPRequestHandler methods
        mock_request_handler = Mock(spec=BaseHTTPRequestHandler)
        mock_request_handler.wfile = BytesIO() # Simulate wfile as a byte stream

        # Act
        handler.do_GET(mock_request_handler)

        # Assert
        mock_process_all_accounts.assert_called_once() # process_all_accounts should still be called

        # Verify logger calls
        mock_logger.info.assert_any_call(LogCategory.SYSTEM, "cron_trigger", "Cron job triggered - starting monitoring process")
        mock_logger.error.assert_called_once_with(
            LogCategory.SYSTEM, "cron_error", f"Main process failed: {error_message}", error=error_message
        )
        mock_print_exc.assert_called_once() # traceback.print_exc should be called

        # Verify HTTP response
        mock_request_handler.send_response.assert_called_once_with(500)
        mock_request_handler.send_header.assert_any_call('Content-type','text/plain')
        mock_request_handler.end_headers.assert_called_once()
        assert mock_request_handler.wfile.getvalue() == f'Error: {error_message}'.encode('utf-8')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
