import unittest
from unittest.mock import patch, MagicMock
import time
from src.core.network_monitor import NetworkMonitor

class TestNetworkMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = NetworkMonitor(host="8.8.8.8", timeout=2)

    @patch('src.core.network_monitor.ping')
    def test_is_connected_success(self, mock_ping):
        mock_ping.return_value = 0.1
        self.assertTrue(self.monitor.is_connected())

    @patch('src.core.network_monitor.ping')
    def test_is_connected_failure(self, mock_ping):
        mock_ping.return_value = None
        self.assertFalse(self.monitor.is_connected())

    @patch('src.core.network_monitor.ping')
    def test_is_connected_exception(self, mock_ping):
        mock_ping.side_effect = Exception("Network error")
        self.assertFalse(self.monitor.is_connected())

    @patch('src.core.network_monitor.ping')
    def test_wait_for_connection_success(self, mock_ping):
        mock_ping.return_value = 0.1
        result = self.monitor.wait_for_connection(check_interval=0.1, max_wait=1)
        self.assertTrue(result)

    @patch('src.core.network_monitor.ping')
    def test_wait_for_connection_timeout(self, mock_ping):
        mock_ping.return_value = None
        result = self.monitor.wait_for_connection(check_interval=0.1, max_wait=0.5)
        self.assertFalse(result)

    def test_initialization(self):
        monitor = NetworkMonitor(host="google.com", timeout=5)
        self.assertEqual(monitor.host, "google.com")
        self.assertEqual(monitor.timeout, 5)

if __name__ == '__main__':
    unittest.main() 