import unittest
from unittest.mock import patch, MagicMock
import time
from src.core.retry_manager import RetryManager, NetworkRetryManager

class TestRetryManager(unittest.TestCase):
    def setUp(self):
        self.retry_manager = RetryManager(max_attempts=3, base_delay=1.0)

    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff calculation."""
        delays = [
            self.retry_manager.calculate_delay(0),  # 1s base
            self.retry_manager.calculate_delay(1),  # 2s
            self.retry_manager.calculate_delay(2),  # 4s
        ]
        
        # Should be approximately exponential (with jitter)
        self.assertGreater(delays[1], delays[0])
        self.assertGreater(delays[2], delays[1])
        
        # All delays should be positive
        for delay in delays:
            self.assertGreaterEqual(delay, 0)

    def test_retry_operation_success_first_attempt(self):
        """Test successful operation on first attempt."""
        mock_operation = MagicMock(return_value="success")
        
        result = self.retry_manager.retry_operation(mock_operation)
        
        self.assertEqual(result, "success")
        mock_operation.assert_called_once()

    def test_retry_operation_success_after_retries(self):
        """Test successful operation after some failures."""
        mock_operation = MagicMock()
        mock_operation.side_effect = [Exception("fail"), Exception("fail"), "success"]
        
        result = self.retry_manager.retry_operation(mock_operation)
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_operation.call_count, 3)

    def test_retry_operation_failure_after_all_attempts(self):
        """Test operation fails after all retry attempts."""
        mock_operation = MagicMock()
        mock_operation.side_effect = Exception("persistent failure")
        
        with self.assertRaises(Exception) as context:
            self.retry_manager.retry_operation(mock_operation)
        
        self.assertEqual(str(context.exception), "persistent failure")
        self.assertEqual(mock_operation.call_count, 3)

    def test_retry_operation_with_custom_exceptions(self):
        """Test retry with custom exception types."""
        mock_operation = MagicMock()
        mock_operation.side_effect = [ValueError("custom error"), "success"]
        
        result = self.retry_manager.retry_operation(
            mock_operation, 
            retryable_exceptions=(ValueError,)
        )
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_operation.call_count, 2)

    def test_retry_decorator(self):
        """Test retry decorator functionality."""
        call_count = 0
        
        @self.retry_manager.retry_decorator(max_attempts=2)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("fail")
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)

class TestNetworkRetryManager(unittest.TestCase):
    def setUp(self):
        self.network_retry_manager = NetworkRetryManager(max_attempts=2)

    def test_network_retry_operation(self):
        """Test network-specific retry operation."""
        mock_operation = MagicMock()
        mock_operation.side_effect = [ConnectionError("network error"), "success"]
        
        result = self.network_retry_manager.retry_network_operation(mock_operation)
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_operation.call_count, 2)

    def test_network_exceptions_configured(self):
        """Test that network exceptions are properly configured."""
        expected_exceptions = (ConnectionError, TimeoutError, OSError)
        self.assertEqual(self.network_retry_manager.network_exceptions, expected_exceptions)

if __name__ == '__main__':
    unittest.main() 