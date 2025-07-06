"""Network monitoring for the scraper."""
import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from statistics import mean, stdev
from collections import deque

@dataclass
class NetworkMetrics:
    """Network performance metrics."""
    response_times: deque = field(default_factory=lambda: deque(maxlen=50))
    success_rates: deque = field(default_factory=lambda: deque(maxlen=50))
    consecutive_failures: int = 0
    last_check_time: float = field(default_factory=time.time)
    is_healthy: bool = True

class NetworkMonitor:
    """Monitors network conditions and performance."""
    
    def __init__(self, 
                 response_time_threshold: float = 5.0,
                 success_rate_threshold: float = 0.8,
                 max_consecutive_failures: int = 3,
                 check_interval: float = 60.0):
        """Initialize the network monitor.
        
        Args:
            response_time_threshold: Maximum acceptable response time in seconds
            success_rate_threshold: Minimum acceptable success rate
            max_consecutive_failures: Maximum consecutive failures before marking unhealthy
            check_interval: Interval between network health checks in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.response_time_threshold = response_time_threshold
        self.success_rate_threshold = success_rate_threshold
        self.max_consecutive_failures = max_consecutive_failures
        self.check_interval = check_interval
        self.metrics = NetworkMetrics()

    def record_response_time(self, response_time: float) -> None:
        """Record a response time measurement.
        
        Args:
            response_time: Response time in seconds
        """
        self.metrics.response_times.append(response_time)
        self._check_network_health()

    def record_success_rate(self, success_rate: float) -> None:
        """Record a success rate measurement.
        
        Args:
            success_rate: Success rate as a float between 0 and 1
        """
        self.metrics.success_rates.append(success_rate)
        self._check_network_health()

    def record_failure(self) -> None:
        """Record a network failure."""
        self.metrics.consecutive_failures += 1
        self._check_network_health()

    def record_success(self) -> None:
        """Record a network success."""
        self.metrics.consecutive_failures = 0
        self._check_network_health()

    def get_network_stats(self) -> Dict:
        """Get current network statistics.
        
        Returns:
            Dict containing network statistics
        """
        response_times = list(self.metrics.response_times)
        success_rates = list(self.metrics.success_rates)
        
        stats = {
            'is_healthy': self.metrics.is_healthy,
            'consecutive_failures': self.metrics.consecutive_failures,
            'last_check_time': self.metrics.last_check_time
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
        if not self.metrics.is_healthy:
            self.logger.warning(
                f"Network unhealthy: {self.metrics.consecutive_failures} "
                "consecutive failures"
            )
            return False
        return True

    def get_recommended_delay(self) -> float:
        """Get recommended delay before next request based on network conditions.
        
        Returns:
            float: Recommended delay in seconds
        """
        if not self.metrics.is_healthy:
            return 30.0  # Long delay if network is unhealthy
            
        if self.metrics.consecutive_failures > 0:
            return 5.0 * (1.5 ** self.metrics.consecutive_failures)
            
        response_times = list(self.metrics.response_times)
        if response_times:
            avg_response = mean(response_times)
            if avg_response > self.response_time_threshold:
                return avg_response * 2
                
        return 1.0  # Default delay

    def _check_network_health(self) -> None:
        """Check and update network health status."""
        current_time = time.time()
        if current_time - self.metrics.last_check_time < self.check_interval:
            return
            
        self.metrics.last_check_time = current_time
        
        # Check consecutive failures
        if self.metrics.consecutive_failures >= self.max_consecutive_failures:
            self.metrics.is_healthy = False
            self.logger.warning(
                f"Network marked unhealthy: {self.metrics.consecutive_failures} "
                "consecutive failures"
            )
            return
            
        # Check response times
        response_times = list(self.metrics.response_times)
        if response_times:
            avg_response = mean(response_times)
            if avg_response > self.response_time_threshold:
                self.metrics.is_healthy = False
                self.logger.warning(
                    f"Network marked unhealthy: average response time "
                    f"{avg_response:.1f}s exceeds threshold {self.response_time_threshold}s"
                )
                return
                
        # Check success rates
        success_rates = list(self.metrics.success_rates)
        if success_rates:
            avg_success = mean(success_rates)
            if avg_success < self.success_rate_threshold:
                self.metrics.is_healthy = False
                self.logger.warning(
                    f"Network marked unhealthy: success rate {avg_success:.1%} "
                    f"below threshold {self.success_rate_threshold:.1%}"
                )
                return
                
        # If we get here, network is healthy
        self.metrics.is_healthy = True 