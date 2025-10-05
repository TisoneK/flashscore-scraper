"""Performance monitoring for the scraper."""
import time
import logging
import psutil
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

@dataclass
class MemoryMetrics:
    """Memory usage metrics."""
    current_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    system_memory_used_mb: float = 0.0
    system_memory_total_mb: float = 0.0
    system_memory_percent: float = 0.0
    memory_history: deque = field(default_factory=lambda: deque(maxlen=100))
    memory_warnings: int = 0
    memory_critical: int = 0
    last_cleanup_time: float = field(default_factory=time.time)

@dataclass
class CPUMetrics:
    """CPU usage metrics."""
    current_cpu_percent: float = 0.0
    average_cpu_percent: float = 0.0
    system_cpu_percent: float = 0.0
    cpu_history: deque = field(default_factory=lambda: deque(maxlen=100))
    cpu_warnings: int = 0

@dataclass
class BrowserMetrics:
    """Browser-specific metrics."""
    active_tabs: int = 0
    browser_processes: int = 0
    browser_memory_mb: float = 0.0
    browser_crashes: int = 0
    last_restart_time: float = field(default_factory=time.time)

@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    start_time: float = field(default_factory=time.time)
    total_matches: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    tab_processing_times: Dict[str, float] = field(default_factory=dict)
    match_processing_times: Dict[str, float] = field(default_factory=dict)
    batch_times: List[float] = field(default_factory=list)
    last_batch_time: Optional[float] = None
    memory_metrics: MemoryMetrics = field(default_factory=MemoryMetrics)
    cpu_metrics: CPUMetrics = field(default_factory=CPUMetrics)
    browser_metrics: BrowserMetrics = field(default_factory=BrowserMetrics)

class PerformanceMonitor:
    """Monitors and reports scraper performance metrics with memory and CPU tracking."""
    
    def __init__(self):
        """Initialize the performance monitor."""
        self.logger = logging.getLogger(__name__)
        self.metrics = PerformanceMetrics()
        self._start_time = time.time()
        self._monitoring_thread = None
        self._monitoring_active = False
        
        # Memory thresholds (in MB)
        self.memory_warning_threshold = 500  # 500MB
        self.memory_critical_threshold = 1000  # 1GB
        self.memory_cleanup_threshold = 800  # 800MB
        
        # CPU thresholds
        self.cpu_warning_threshold = 80  # 80%
        self.cpu_critical_threshold = 95  # 95%
        
        # Browser thresholds
        self.max_active_tabs = 10
        self.max_browser_memory_mb = 2000  # 2GB
        
        # Start monitoring
        self.start_resource_monitoring()

    def start_resource_monitoring(self):
        """Start background resource monitoring."""
        if self._monitoring_active:
            return
            
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self._monitoring_thread.start()
        self.logger.info("🔍 Started resource monitoring (memory, CPU, browser)")

    def stop_resource_monitoring(self):
        """Stop background resource monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=2)
        self.logger.info("🛑 Stopped resource monitoring")

    def _monitor_resources(self):
        """Background thread for monitoring system resources."""
        while self._monitoring_active:
            try:
                # Update memory metrics
                self._update_memory_metrics()
                
                # Update CPU metrics
                self._update_cpu_metrics()
                
                # Update browser metrics
                self._update_browser_metrics()
                
                # Check for warnings and cleanup
                self._check_resource_warnings()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                time.sleep(5)

    def _update_memory_metrics(self):
        """Update memory usage metrics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            current_memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            
            self.metrics.memory_metrics.current_memory_mb = current_memory_mb
            self.metrics.memory_metrics.memory_history.append(current_memory_mb)
            
            # Update peak memory
            if current_memory_mb > self.metrics.memory_metrics.peak_memory_mb:
                self.metrics.memory_metrics.peak_memory_mb = current_memory_mb

            # Update system-wide memory metrics
            try:
                vm = psutil.virtual_memory()
                self.metrics.memory_metrics.system_memory_used_mb = vm.used / 1024 / 1024
                self.metrics.memory_metrics.system_memory_total_mb = vm.total / 1024 / 1024
                self.metrics.memory_metrics.system_memory_percent = float(vm.percent)
            except Exception:
                pass
                
        except Exception as e:
            self.logger.debug(f"Error updating memory metrics: {e}")

    def _update_cpu_metrics(self):
        """Update CPU usage metrics."""
        try:
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=0.1)
            
            self.metrics.cpu_metrics.current_cpu_percent = cpu_percent
            self.metrics.cpu_metrics.cpu_history.append(cpu_percent)
            
            # Calculate average CPU usage
            if self.metrics.cpu_metrics.cpu_history:
                self.metrics.cpu_metrics.average_cpu_percent = sum(self.metrics.cpu_metrics.cpu_history) / len(self.metrics.cpu_metrics.cpu_history)

            # Update system-wide CPU usage
            try:
                self.metrics.cpu_metrics.system_cpu_percent = psutil.cpu_percent(interval=0.1)
            except Exception:
                pass
                
        except Exception as e:
            self.logger.debug(f"Error updating CPU metrics: {e}")

    def _update_browser_metrics(self):
        """Update browser-specific metrics."""
        try:
            # Count Chrome/Chromium processes
            browser_processes = 0
            browser_memory_mb = 0.0
            
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                        browser_processes += 1
                        if proc.info['memory_info']:
                            browser_memory_mb += proc.info['memory_info'].rss / 1024 / 1024
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            self.metrics.browser_metrics.browser_processes = browser_processes
            self.metrics.browser_metrics.browser_memory_mb = browser_memory_mb
            
        except Exception as e:
            self.logger.debug(f"Error updating browser metrics: {e}")

    def _check_resource_warnings(self):
        """Check for resource warnings and trigger cleanup if needed."""
        current_memory = self.metrics.memory_metrics.current_memory_mb
        current_cpu = self.metrics.cpu_metrics.current_cpu_percent
        
        # Memory warnings
        if current_memory > self.memory_critical_threshold:
            self.metrics.memory_metrics.memory_critical += 1
            self.logger.warning(f"🚨 CRITICAL: Memory usage {current_memory:.1f}MB exceeds {self.memory_critical_threshold}MB")
            self._trigger_memory_cleanup()
        elif current_memory > self.memory_warning_threshold:
            self.metrics.memory_metrics.memory_warnings += 1
            self.logger.warning(f"⚠️ WARNING: Memory usage {current_memory:.1f}MB exceeds {self.memory_warning_threshold}MB")
        
        # CPU warnings
        if current_cpu > self.cpu_critical_threshold:
            self.metrics.cpu_metrics.cpu_warnings += 1
            self.logger.warning(f"🚨 CRITICAL: CPU usage {current_cpu:.1f}% exceeds {self.cpu_critical_threshold}%")
        elif current_cpu > self.cpu_warning_threshold:
            self.metrics.cpu_metrics.cpu_warnings += 1
            self.logger.warning(f"⚠️ WARNING: CPU usage {current_cpu:.1f}% exceeds {self.cpu_warning_threshold}%")

    def _trigger_memory_cleanup(self):
        """Trigger memory cleanup when thresholds are exceeded."""
        current_time = time.time()
        last_cleanup = self.metrics.memory_metrics.last_cleanup_time
        
        # Only cleanup if enough time has passed since last cleanup
        if current_time - last_cleanup > 60:  # 1 minute cooldown
            self.logger.info("🧹 Triggering memory cleanup...")
            self.metrics.memory_metrics.last_cleanup_time = current_time
            # This will be handled by the resource manager

    def get_memory_summary(self) -> Dict[str, float]:
        """Get memory usage summary."""
        return {
            'current_memory_mb': self.metrics.memory_metrics.current_memory_mb,
            'peak_memory_mb': self.metrics.memory_metrics.peak_memory_mb,
            'system_memory_used_mb': self.metrics.memory_metrics.system_memory_used_mb,
            'system_memory_total_mb': self.metrics.memory_metrics.system_memory_total_mb,
            'system_memory_percent': self.metrics.memory_metrics.system_memory_percent,
            'memory_warnings': self.metrics.memory_metrics.memory_warnings,
            'memory_critical': self.metrics.memory_metrics.memory_critical
        }

    def get_cpu_summary(self) -> Dict[str, float]:
        """Get CPU usage summary."""
        return {
            'current_cpu_percent': self.metrics.cpu_metrics.current_cpu_percent,
            'average_cpu_percent': self.metrics.cpu_metrics.average_cpu_percent,
            'system_cpu_percent': self.metrics.cpu_metrics.system_cpu_percent,
            'cpu_warnings': self.metrics.cpu_metrics.cpu_warnings
        }

    def get_browser_summary(self) -> Dict[str, float]:
        """Get browser metrics summary."""
        return {
            'browser_processes': self.metrics.browser_metrics.browser_processes,
            'browser_memory_mb': self.metrics.browser_metrics.browser_memory_mb,
            'browser_crashes': self.metrics.browser_metrics.browser_crashes
        }

    def record_browser_crash(self):
        """Record a browser crash event."""
        self.metrics.browser_metrics.browser_crashes += 1
        self.logger.error("💥 Browser crash detected")

    def is_memory_healthy(self) -> bool:
        """Check if memory usage is healthy."""
        return self.metrics.memory_metrics.current_memory_mb < self.memory_warning_threshold

    def is_cpu_healthy(self) -> bool:
        """Check if CPU usage is healthy."""
        return self.metrics.cpu_metrics.current_cpu_percent < self.cpu_warning_threshold

    def should_trigger_cleanup(self) -> bool:
        """Check if cleanup should be triggered."""
        return (
            self.metrics.memory_metrics.current_memory_mb > self.memory_cleanup_threshold or
            self.metrics.cpu_metrics.current_cpu_percent > self.cpu_critical_threshold
        )

    def start_batch(self, batch_size: int) -> None:
        """Start timing a new batch."""
        self.metrics.last_batch_time = time.time()

    def end_batch(self, successful: int, failed: int) -> None:
        """End timing a batch and update metrics."""
        if self.metrics.last_batch_time:
            batch_time = time.time() - self.metrics.last_batch_time
            self.metrics.batch_times.append(batch_time)
            self.metrics.successful_matches += successful
            self.metrics.failed_matches += failed
            self.metrics.total_matches = self.metrics.successful_matches + self.metrics.failed_matches

    def record_tab_time(self, tab_key: str, processing_time: float) -> None:
        """Record processing time for a tab."""
        self.metrics.tab_processing_times[tab_key] = (
            self.metrics.tab_processing_times.get(tab_key, 0) + processing_time
        )

    def record_match_time(self, match_id: str, processing_time: float) -> None:
        """Record processing time for a match."""
        self.metrics.match_processing_times[match_id] = processing_time

    def get_average_batch_time(self) -> float:
        """Calculate average batch processing time."""
        if not self.metrics.batch_times:
            return 0.0
        return sum(self.metrics.batch_times) / len(self.metrics.batch_times)

    def get_average_match_time(self) -> float:
        """Calculate average match processing time."""
        if not self.metrics.match_processing_times:
            return 0.0
        return sum(self.metrics.match_processing_times.values()) / len(self.metrics.match_processing_times)

    def log_progress(self, current_batch_time: Optional[float] = None) -> None:
        """Log current progress and performance metrics."""
        total_processed = self.metrics.successful_matches + self.metrics.failed_matches
        if self.metrics.total_matches > 0:
            percentage = (total_processed / self.metrics.total_matches) * 100
            elapsed_time = time.time() - self._start_time
            avg_time_per_match = elapsed_time / total_processed if total_processed > 0 else 0
            
            progress_msg = (
                f"Progress: {total_processed}/{self.metrics.total_matches} matches "
                f"({percentage:.1f}%) - {self.metrics.successful_matches} successful, "
                f"{self.metrics.failed_matches} failed"
            )
            if current_batch_time:
                progress_msg += f" (Batch time: {current_batch_time:.1f}s, Avg: {avg_time_per_match:.1f}s/match)"
            self.logger.info(progress_msg)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        total_time = time.time() - self._start_time
        memory_summary = self.get_memory_summary()
        cpu_summary = self.get_cpu_summary()
        browser_summary = self.get_browser_summary()
        
        return {
            'total_time': total_time,
            'total_matches': self.metrics.total_matches,
            'successful_matches': self.metrics.successful_matches,
            'failed_matches': self.metrics.failed_matches,
            'success_rate': (self.metrics.successful_matches/self.metrics.total_matches*100) if self.metrics.total_matches > 0 else 0,
            'average_match_time': self.get_average_match_time(),
            'average_batch_time': self.get_average_batch_time(),
            'memory_usage': memory_summary['current_memory_mb'],
            'peak_memory_usage': memory_summary['peak_memory_mb'],
            'cpu_usage': cpu_summary['current_cpu_percent'],
            'system_cpu_percent': cpu_summary.get('system_cpu_percent', 0.0),
            'system_memory_percent': memory_summary.get('system_memory_percent', 0.0),
            'system_memory_used_mb': memory_summary.get('system_memory_used_mb', 0.0),
            'system_memory_total_mb': memory_summary.get('system_memory_total_mb', 0.0),
            'average_cpu_usage': cpu_summary['average_cpu_percent'],
            'browser_processes': browser_summary['browser_processes'],
            'browser_memory': browser_summary['browser_memory_mb'],
            'browser_crashes': browser_summary['browser_crashes']
        }

    def log_final_metrics(self) -> None:
        """Log final performance metrics."""
        total_time = time.time() - self._start_time
        self.logger.info("\nPerformance Metrics:")
        self.logger.info(f"Total processing time: {total_time:.1f}s")
        self.logger.info(f"Average time per match: {self.get_average_match_time():.1f}s")
        self.logger.info(f"Average batch time: {self.get_average_batch_time():.1f}s")
        self.logger.info(f"Success rate: {(self.metrics.successful_matches/self.metrics.total_matches*100):.1f}%")
        
        # Add resource metrics
        memory_summary = self.get_memory_summary()
        cpu_summary = self.get_cpu_summary()
        browser_summary = self.get_browser_summary()
        
        self.logger.info(f"Peak memory usage: {memory_summary['peak_memory_mb']:.1f}MB")
        self.logger.info(f"Average CPU usage: {cpu_summary['average_cpu_percent']:.1f}%")
        self.logger.info(f"Browser crashes: {browser_summary['browser_crashes']}")
        
        for tab_key, tab_time in sorted(self.metrics.tab_processing_times.items()):
            self.logger.info(f"{tab_key} total processing time: {tab_time:.1f}s")

    def __del__(self):
        """Cleanup when the monitor is destroyed."""
        self.stop_resource_monitoring() 