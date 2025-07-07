import unittest
from unittest.mock import patch, MagicMock
import time
import threading
from src.core.network_monitor import NetworkMonitor

class TestNetworkMonitorRealTimeMonitoring(unittest.TestCase):
    def setUp(self):
        self.monitor = NetworkMonitor(host="8.8.8.8", timeout=2)

    @patch('src.core.network_monitor.ping')
    def test_get_connection_quality_excellent(self, mock_ping):
        """Test connection quality measurement for excellent connection."""
        mock_ping.return_value = 0.05  # Fast response
        
        quality = self.monitor.get_connection_quality()
        
        self.assertEqual(quality["status"], "connected")
        self.assertEqual(quality["quality"], "excellent")
        self.assertIsInstance(quality["response_time"], float)
        self.assertEqual(quality["tests"], 3)

    @patch('src.core.network_monitor.ping')
    def test_get_connection_quality_poor(self, mock_ping):
        """Test connection quality measurement for poor connection."""
        mock_ping.return_value = 1.5  # Slow response
        
        quality = self.monitor.get_connection_quality()
        
        self.assertEqual(quality["status"], "connected")
        self.assertEqual(quality["quality"], "poor")
        self.assertIsInstance(quality["response_time"], float)

    @patch('src.core.network_monitor.ping')
    def test_get_connection_quality_disconnected(self, mock_ping):
        """Test connection quality measurement when disconnected."""
        mock_ping.return_value = None  # No response
        
        quality = self.monitor.get_connection_quality()
        
        self.assertEqual(quality["status"], "disconnected")
        self.assertEqual(quality["quality"], "poor")
        self.assertIsNone(quality["response_time"])

    @patch('src.core.network_monitor.ping')
    def test_alert_connection_degradation_triggered(self, mock_ping):
        """Test alert when connection quality degrades."""
        mock_ping.return_value = 1.2  # Poor quality
        
        alert_triggered = self.monitor.alert_connection_degradation(threshold_quality="good")
        
        self.assertTrue(alert_triggered)

    @patch('src.core.network_monitor.ping')
    def test_alert_connection_degradation_not_triggered(self, mock_ping):
        """Test no alert when connection quality is acceptable."""
        mock_ping.return_value = 0.2  # Good quality
        
        alert_triggered = self.monitor.alert_connection_degradation(threshold_quality="fair")
        
        self.assertFalse(alert_triggered)

    @patch('src.core.network_monitor.ping')
    def test_start_stop_monitoring(self, mock_ping):
        """Test starting and stopping real-time monitoring."""
        mock_ping.return_value = 0.1  # Connected
        
        # Start monitoring
        self.monitor.start_monitoring(check_interval=0.1)
        
        # Let it run for a short time
        time.sleep(0.3)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        
        # Verify monitoring was started and stopped
        self.assertTrue(hasattr(self.monitor, '_monitoring'))
        self.assertFalse(self.monitor._monitoring)

    @patch('src.core.network_monitor.ping')
    def test_monitoring_callback(self, mock_ping):
        """Test monitoring with callback function."""
        callback_called = []
        
        def test_callback(status):
            callback_called.append(status)
        
        mock_ping.return_value = 0.1  # Connected
        
        # Start monitoring with callback
        self.monitor.start_monitoring(callback=test_callback, check_interval=0.1)
        
        # Let it run for a short time
        time.sleep(0.3)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        
        # Verify callback was called
        self.assertGreater(len(callback_called), 0)
        self.assertTrue(all(isinstance(status, bool) for status in callback_called))

    @patch('src.core.network_monitor.ping')
    def test_monitoring_status_changes(self, mock_ping):
        """Test monitoring detects status changes."""
        # Simulate connection status changes
        mock_ping.side_effect = [0.1, None, 0.1]  # Connected -> Disconnected -> Connected
        
        status_changes = []
        
        def test_callback(status):
            status_changes.append(status)
        
        # Start monitoring
        self.monitor.start_monitoring(callback=test_callback, check_interval=0.1)
        
        # Let it run for a short time
        time.sleep(0.5)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        
        # Verify status changes were detected
        self.assertGreater(len(status_changes), 0)

    def test_quality_levels_comparison(self):
        """Test quality level comparison logic."""
        quality_levels = {"excellent": 4, "good": 3, "fair": 2, "poor": 1}
        
        # Test that higher quality levels have higher values
        self.assertGreater(quality_levels["excellent"], quality_levels["good"])
        self.assertGreater(quality_levels["good"], quality_levels["fair"])
        self.assertGreater(quality_levels["fair"], quality_levels["poor"])

if __name__ == '__main__':
    unittest.main() 