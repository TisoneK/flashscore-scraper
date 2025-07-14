"""Network monitoring for the scraper."""
import logging
import time
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from statistics import mean, stdev
from collections import deque
from ping3 import ping
import threading

@dataclass
class NetworkMetrics:
    """Network performance metrics."""
    response_times: deque = field(default_factory=lambda: deque(maxlen=50))
    success_rates: deque = field(default_factory=lambda: deque(maxlen=50))
    consecutive_failures: int = 0
    last_check_time: float = field(default_factory=time.time)
    is_healthy: bool = True

class NetworkMonitor:
    """
    Monitors network connectivity in real-time using ping.
    Implements singleton pattern to prevent multiple instances.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(NetworkMonitor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        self.monitoring = False
        self.monitor_thread = None
        self.connection_status = True  # Assume connected initially
        self.check_interval = 5  # Check every 5 seconds
        self.host = "8.8.8.8"  # Google DNS
        self.timeout = 3  # Ping timeout in seconds
        self.alert_callbacks = []
        self.connection_quality_metrics = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'average_response_time': 0.0,
            'last_response_time': 0.0
        }
        self.status_callback = None

    def is_connected(self) -> bool:
        """
        Check if network is currently connected.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            response_time = ping(self.host, timeout=self.timeout)
            if response_time is not None:
                self.connection_quality_metrics['last_response_time'] = response_time
                self.connection_quality_metrics['total_checks'] += 1
                self.connection_quality_metrics['successful_checks'] += 1
                # Update average response time
                total_checks = self.connection_quality_metrics['total_checks']
                current_avg = self.connection_quality_metrics['average_response_time']
                self.connection_quality_metrics['average_response_time'] = (
                    (current_avg * (total_checks - 1) + response_time) / total_checks
                )
                return True
            else:
                self.connection_quality_metrics['total_checks'] += 1
                self.connection_quality_metrics['failed_checks'] += 1
                return False
        except Exception as e:
            self.logger.debug(f"Ping failed: {e}")
            self.connection_quality_metrics['total_checks'] += 1
            self.connection_quality_metrics['failed_checks'] += 1
            return False

    def wait_for_connection(self, timeout: int = 60) -> bool:
        """
        Wait for network connection to be restored.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if connection restored, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_connected():
                return True
            time.sleep(1)
        return False

    def start_monitoring(self, status_callback: Optional[Callable[[str], None]] = None):
        """Start real-time network monitoring in background thread."""
        if self.monitoring:
            self.logger.debug("Network monitoring already started")
            if status_callback:
                status_callback("Network monitoring already started")
            return
            
        self.monitoring = True
        self.status_callback = status_callback
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("🔍 Started real-time connection monitoring")
        if status_callback:
            status_callback("🔍 Started real-time connection monitoring")

    def stop_monitoring(self):
        """Stop network monitoring."""
        if not self.monitoring:
            self.logger.debug("Network monitoring already stopped")
            if self.status_callback:
                self.status_callback("Network monitoring already stopped")
            return
            
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        self.logger.info("🛑 Stopped real-time connection monitoring")
        if self.status_callback:
            self.status_callback("🛑 Stopped real-time connection monitoring")

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            try:
                current_status = self.is_connected()
                
                # Detect status changes
                if current_status != self.connection_status:
                    if current_status:
                        msg = "✅ Network connection restored"
                        self.logger.info(msg)
                    else:
                        msg = "⚠️ Network connection lost"
                        self.logger.warning(msg)
                    
                    self.connection_status = current_status
                    
                    # Notify callbacks
                    for callback in self.alert_callbacks:
                        try:
                            callback(current_status)
                        except Exception as e:
                            self.logger.error(f"Error in network alert callback: {e}")
                    # Also notify status_callback
                    if self.status_callback:
                        self.status_callback(msg)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in network monitoring loop: {e}")
                if self.status_callback:
                    self.status_callback(f"Error in network monitoring loop: {e}")
                time.sleep(self.check_interval)

    def add_alert_callback(self, callback: Callable[[bool], None]):
        """
        Add a callback function to be called when connection status changes.
        
        Args:
            callback: Function that takes a boolean (connected status)
        """
        self.alert_callbacks.append(callback)

    def remove_alert_callback(self, callback: Callable[[bool], None]):
        """
        Remove a callback function.
        
        Args:
            callback: Function to remove
        """
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)

    def get_connection_quality(self) -> dict:
        """
        Get connection quality metrics.
        
        Returns:
            Dictionary with connection quality metrics
        """
        if self.connection_quality_metrics['total_checks'] == 0:
            return {
                'success_rate': 0.0,
                'average_response_time': 0.0,
                'last_response_time': 0.0,
                'total_checks': 0,
                'successful_checks': 0,
                'failed_checks': 0
            }
        
        success_rate = (
            self.connection_quality_metrics['successful_checks'] / 
            self.connection_quality_metrics['total_checks']
        )
        
        return {
            'success_rate': success_rate,
            'average_response_time': self.connection_quality_metrics['average_response_time'],
            'last_response_time': self.connection_quality_metrics['last_response_time'],
            'total_checks': self.connection_quality_metrics['total_checks'],
            'successful_checks': self.connection_quality_metrics['successful_checks'],
            'failed_checks': self.connection_quality_metrics['failed_checks']
        }

    def is_connection_degraded(self) -> bool:
        """
        Check if connection quality is degraded.
        
        Returns:
            True if connection is degraded, False otherwise
        """
        quality = self.get_connection_quality()
        return quality['success_rate'] < 0.8  # Less than 80% success rate

    def record_response_time(self, response_time: float) -> None:
        """Record a response time measurement.
        
        Args:
            response_time: Response time in seconds
        """
        self.connection_quality_metrics['last_response_time'] = response_time
        self.connection_quality_metrics['total_checks'] += 1
        self.connection_quality_metrics['successful_checks'] += 1
        # Update average response time
        total_checks = self.connection_quality_metrics['total_checks']
        current_avg = self.connection_quality_metrics['average_response_time']
        self.connection_quality_metrics['average_response_time'] = (
            (current_avg * (total_checks - 1) + response_time) / total_checks
        )

    def record_success_rate(self, success_rate: float) -> None:
        """Record a success rate measurement.
        
        Args:
            success_rate: Success rate as a float between 0 and 1
        """
        self.connection_quality_metrics['successful_checks'] = int(success_rate * self.connection_quality_metrics['total_checks'])
        self.connection_quality_metrics['failed_checks'] = self.connection_quality_metrics['total_checks'] - self.connection_quality_metrics['successful_checks']

    def record_failure(self) -> None:
        """Record a network failure."""
        self.connection_quality_metrics['failed_checks'] += 1
        self.connection_quality_metrics['successful_checks'] = 0

    def record_success(self) -> None:
        """Record a network success."""
        self.connection_quality_metrics['successful_checks'] = self.connection_quality_metrics['total_checks']
        self.connection_quality_metrics['failed_checks'] = 0

    def get_network_stats(self) -> Dict:
        """Get current network statistics.
        
        Returns:
            Dict containing network statistics
        """
        response_times = list(self.connection_quality_metrics.values())[:-2]
        success_rates = [self.connection_quality_metrics['successful_checks'] / self.connection_quality_metrics['total_checks']]
        
        stats = {
            'is_healthy': self.connection_quality_metrics['successful_checks'] > 0,
            'consecutive_failures': self.connection_quality_metrics['failed_checks'],
            'last_check_time': self.connection_quality_metrics['last_response_time']
        }
        
        if response_times:
            stats.update({
                'avg_response_time': mean(response_times),
                'max_response_time': max(response_times),
                'min_response_time': min(response_times),
                'response_time_stddev': stdev(response_times) if len(response_times) > 1 else 0
            })
        
        if success_rates:
            stats.update({
                'avg_success_rate': mean(success_rates),
                'min_success_rate': min(success_rates)
            })
        
        return stats

    def should_continue_processing(self) -> bool:
        """Determine if processing should continue based on network health.
        
        Returns:
            bool: True if processing should continue
        """
        if self.connection_quality_metrics['failed_checks'] > 0:
            self.logger.warning(
                f"Network unhealthy: {self.connection_quality_metrics['failed_checks']} "
                "consecutive failures"
            )
            return False
        return True

    def get_recommended_delay(self) -> float:
        """Get recommended delay before next request based on network conditions.
        
        Returns:
            float: Recommended delay in seconds
        """
        if self.connection_quality_metrics['failed_checks'] > 0:
            return 30.0  # Long delay if network is unhealthy
            
        response_times = list(self.connection_quality_metrics.values())[:-2]
        if response_times:
            avg_response = mean(response_times)
            if avg_response > 5.0:
                return avg_response * 2
                
        return 1.0  # Default delay

    def alert_connection_degradation(self, threshold_quality="fair"):
        """
        Alert when connection quality degrades below threshold.
        
        Args:
            threshold_quality: Minimum acceptable quality level
        """
        quality_levels = {"excellent": 4, "good": 3, "fair": 2, "poor": 1}
        current_quality = self.get_connection_quality()
        
        if (current_quality['success_rate'] > 0.0 and 
            quality_levels.get(current_quality['success_rate'], 0) < 
            quality_levels.get(threshold_quality, 0)):
            
            self.logger.warning(
                f"⚠️ Connection quality degraded: {current_quality['success_rate']:.1%} "
                f"(response time: {current_quality['average_response_time']:.3f}s)"
            )
            return True
        
        return False 