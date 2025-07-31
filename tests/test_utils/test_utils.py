"""
Comprehensive unit tests for utility functions.

Tests cover:
- Message handling functions
- Logging functionality
- Message conversion and validation
"""

import unittest
from unittest.mock import Mock, patch, call, MagicMock
import json
import sys
import os
import multiprocessing

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import functions directly and mock their dependencies
sys.modules['print_color'] = MagicMock()

# Now we can safely import the utils
from utils.handleMessage import sendMessage, convertMessage
from utils.log import log


class TestHandleMessage(unittest.TestCase):
    """Test cases for message handling functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_conn = Mock()

    def test_send_message_basic(self):
        """Test basic message sending functionality."""
        messageId = "test-123"
        status = "completed"
        reason = "Test successful"
        destination = ["TestWorker"]
        data = {"result": "success"}
        
        sendMessage(
            conn=self.mock_conn,
            messageId=messageId,
            status=status,
            reason=reason,
            destination=destination,
            data=data
        )
        
        # Verify message structure and sending
        expected_message = {
            "messageId": messageId,
            "status": status,
            "reason": reason,
            "destination": destination,
            "data": data
        }
        
        self.mock_conn.send.assert_called_once_with(json.dumps(expected_message))

    def test_send_message_default_parameters(self):
        """Test sendMessage with default parameters."""
        messageId = "test-456"
        status = "failed"
        
        sendMessage(
            conn=self.mock_conn,
            messageId=messageId,
            status=status
        )
        
        # Verify default values are used
        expected_message = {
            "messageId": messageId,
            "status": status,
            "reason": "",
            "destination": ["supervisor"],
            "data": []
        }
        
        self.mock_conn.send.assert_called_once_with(json.dumps(expected_message))

    def test_send_message_all_status_types(self):
        """Test sendMessage with all valid status types."""
        valid_statuses = ["completed", "failed", "healthy", "unhealthy"]
        
        for status in valid_statuses:
            with self.subTest(status=status):
                mock_conn = Mock()
                
                sendMessage(
                    conn=mock_conn,
                    messageId=f"test-{status}",
                    status=status
                )
                
                # Verify message was sent
                mock_conn.send.assert_called_once()
                sent_data = json.loads(mock_conn.send.call_args[0][0])
                self.assertEqual(sent_data["status"], status)

    def test_send_message_complex_data(self):
        """Test sendMessage with complex data structures."""
        complex_data = {
            "nested": {
                "list": [1, 2, 3],
                "dict": {"key": "value"},
                "none": None,
                "bool": True
            },
            "string": "test",
            "number": 42
        }
        
        sendMessage(
            conn=self.mock_conn,
            messageId="test-complex",
            status="completed",
            data=complex_data
        )
        
        # Verify complex data is properly serialized
        sent_message = json.loads(self.mock_conn.send.call_args[0][0])
        self.assertEqual(sent_message["data"], complex_data)

    def test_convert_message_json_string(self):
        """Test convertMessage with JSON string input."""
        message_dict = {
            "messageId": "test-123",
            "status": "completed",
            "data": {"test": "value"}
        }
        message_json = json.dumps(message_dict)
        
        result = convertMessage(message_json)
        
        self.assertEqual(result, message_dict)

    def test_convert_message_dict_input(self):
        """Test convertMessage with dictionary input."""
        message_dict = {
            "messageId": "test-456",
            "status": "failed",
            "reason": "Error occurred"
        }
        
        result = convertMessage(message_dict)
        
        self.assertEqual(result, message_dict)

    @patch('utils.handleMessage.log')
    def test_convert_message_invalid_json(self, mock_log):
        """Test convertMessage with invalid JSON string."""
        invalid_json = '{"invalid": json}'
        
        result = convertMessage(invalid_json)
        
        self.assertEqual(result, {})
        mock_log.assert_called_once()
        log_call = mock_log.call_args[0]
        self.assertIn("Failed to decode message", log_call[0])
        self.assertEqual(log_call[1], "error")

    @patch('utils.handleMessage.log')
    def test_convert_message_unsupported_type(self, mock_log):
        """Test convertMessage with unsupported input type."""
        unsupported_input = 12345  # Not string or dict
        
        result = convertMessage(unsupported_input)
        
        self.assertEqual(result, {})
        mock_log.assert_called_once()
        log_call = mock_log.call_args[0]
        self.assertIn("Unsupported message type", log_call[0])
        self.assertEqual(log_call[1], "error")

    def test_convert_message_empty_string(self):
        """Test convertMessage with empty string."""
        result = convertMessage("")
        
        self.assertEqual(result, {})

    def test_convert_message_empty_dict(self):
        """Test convertMessage with empty dictionary."""
        result = convertMessage({})
        
        self.assertEqual(result, {})

    def test_convert_message_nested_objects(self):
        """Test convertMessage with nested objects."""
        complex_message = {
            "messageId": "complex-test",
            "status": "completed",
            "data": {
                "nested": {
                    "deeply": {
                        "nested": "value"
                    }
                },
                "list": [{"item": 1}, {"item": 2}]
            }
        }
        
        json_string = json.dumps(complex_message)
        result = convertMessage(json_string)
        
        self.assertEqual(result, complex_message)


class TestLog(unittest.TestCase):
    """Test cases for logging functionality."""

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_info_level(self, mock_print, mock_datetime):
        """Test logging with info level."""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 10:30:45"
        
        log("Test info message", "info")
        
        mock_print.assert_called_once_with(
            "[2023-12-01 10:30:45] Test info message",
            tag="info",
            tag_color="blue",
            color="white"
        )

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_error_level(self, mock_print, mock_datetime):
        """Test logging with error level."""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 10:30:45"
        
        log("Test error message", "error")
        
        mock_print.assert_called_once_with(
            "[2023-12-01 10:30:45] Test error message",
            tag="error",
            tag_color="red",
            color="white"
        )

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_warning_level(self, mock_print, mock_datetime):
        """Test logging with warning level."""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 10:30:45"
        
        log("Test warning message", "warn")
        
        mock_print.assert_called_once_with(
            "[2023-12-01 10:30:45] Test warning message",
            tag="warn",
            tag_color="yellow",
            color="white"
        )

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_success_level(self, mock_print, mock_datetime):
        """Test logging with success level."""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 10:30:45"
        
        log("Test success message", "success")
        
        mock_print.assert_called_once_with(
            "[2023-12-01 10:30:45] Test success message",
            tag="success",
            tag_color="green",
            color="white"
        )

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_default_level(self, mock_print, mock_datetime):
        """Test logging with default level (info)."""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 10:30:45"
        
        log("Test default message")
        
        mock_print.assert_called_once_with(
            "[2023-12-01 10:30:45] Test default message",
            tag="info",
            tag_color="blue",
            color="white"
        )

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_unknown_level(self, mock_print, mock_datetime):
        """Test logging with unknown level."""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 10:30:45"
        
        log("Test unknown level", "unknown")
        
        mock_print.assert_called_once_with(
            "[2023-12-01 10:30:45] Test unknown level",
            tag="unknown",
            tag_color="white",
            color="white"
        )

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_timestamp_format(self, mock_print, mock_datetime):
        """Test that timestamp is properly formatted."""
        # Mock datetime to return a specific time
        mock_dt = Mock()
        mock_datetime.now.return_value = mock_dt
        mock_dt.strftime.return_value = "2023-12-01 15:45:30"
        
        log("Timestamp test")
        
        # Verify strftime was called with correct format
        mock_dt.strftime.assert_called_once_with('%Y-%m-%d %H:%M:%S')
        
        # Verify the formatted timestamp is used
        mock_print.assert_called_once_with(
            "[2023-12-01 15:45:30] Timestamp test",
            tag="info",
            tag_color="blue",
            color="white"
        )

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_all_color_mappings(self, mock_print, mock_datetime):
        """Test all color mappings for different log levels."""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 10:30:45"
        
        test_cases = [
            ("info", "blue"),
            ("warn", "yellow"),
            ("error", "red"),
            ("success", "green")
        ]
        
        for level, expected_color in test_cases:
            with self.subTest(level=level):
                mock_print.reset_mock()
                
                log(f"Test {level} message", level)
                
                mock_print.assert_called_once_with(
                    f"[2023-12-01 10:30:45] Test {level} message",
                    tag=level,
                    tag_color=expected_color,
                    color="white"
                )

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_long_message(self, mock_print, mock_datetime):
        """Test logging with very long message."""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 10:30:45"
        
        long_message = "A" * 1000  # Very long message
        
        log(long_message, "info")
        
        mock_print.assert_called_once_with(
            f"[2023-12-01 10:30:45] {long_message}",
            tag="info",
            tag_color="blue",
            color="white"
        )

    @patch('utils.log.datetime')
    @patch('utils.log.print')
    def test_log_special_characters(self, mock_print, mock_datetime):
        """Test logging with special characters and unicode."""
        mock_datetime.now.return_value.strftime.return_value = "2023-12-01 10:30:45"
        
        special_message = "Test message with special chars: @#$%^&*()[]{}|\\:;\"'<>,.?/~`"
        unicode_message = "Test with unicode: 中文 русский العربية"
        
        log(special_message, "info")
        log(unicode_message, "warn")
        
        self.assertEqual(mock_print.call_count, 2)
        
        # Verify special characters are handled correctly
        calls = mock_print.call_args_list
        self.assertIn(special_message, calls[0][1]['text'])
        self.assertIn(unicode_message, calls[1][1]['text'])


if __name__ == '__main__':
    unittest.main()