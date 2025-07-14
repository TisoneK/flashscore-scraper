"""Resource management for the scraper."""
import time
import logging
import gc
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)

@dataclass
class ResourceMetrics:
    """Resource usage metrics."""
    active_tabs: int = 0
    memory_usage_mb: float = 0.0
    last_cleanup_time: float = field(default_factory=time.time)
    cleanup_count: int = 0
    browser_restarts: int = 0

class ResourceManager:
    """Manages browser resources, memory cleanup, and performance optimization."""
    
    def __init__(self, performance_monitor=None):
        """Initialize the resource manager."""
        self.performance_monitor = performance_monitor
        self.metrics = ResourceMetrics()
        self._cleanup_callbacks: List[Callable] = []
        self._monitoring_active = False
        self._monitoring_thread = None
        
        # Resource thresholds
        self.memory_cleanup_threshold = 800  # MB
        self.memory_critical_threshold = 1000  # MB
        self.max_active_tabs = 10
        self.cleanup_cooldown = 60  # seconds
        
        # Browser management
        self._current_driver: Optional[WebDriver] = None
        self._tab_handles: List[str] = []
        
        # Start monitoring
        self.start_monitoring()

    def start_monitoring(self):
        """Start background resource monitoring."""
        if self._monitoring_active:
            return
            
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self._monitoring_thread.start()
        logger.info("🔍 Started resource monitoring")

    def stop_monitoring(self):
        """Stop background resource monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=2)
        logger.info("🛑 Stopped resource monitoring")

    def _monitor_resources(self):
        """Background thread for monitoring resources."""
        while self._monitoring_active:
            try:
                # Check memory usage
                if self.performance_monitor:
                    memory_summary = self.performance_monitor.get_memory_summary()
                    current_memory = memory_summary['current_memory_mb']
                    
                    # Update metrics
                    self.metrics.memory_usage_mb = current_memory
                    
                    # Check if cleanup is needed
                    if current_memory > self.memory_cleanup_threshold:
                        self._trigger_cleanup()
                
                # Check tab count
                if self._current_driver:
                    try:
                        self._tab_handles = self._current_driver.window_handles
                        self.metrics.active_tabs = len(self._tab_handles)
                        
                        # Close excess tabs
                        if self.metrics.active_tabs > self.max_active_tabs:
                            self._cleanup_excess_tabs()
                    except Exception as e:
                        logger.debug(f"Error checking tabs: {e}")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                time.sleep(10)

    def _trigger_cleanup(self):
        """Trigger resource cleanup when thresholds are exceeded."""
        current_time = time.time()
        last_cleanup = self.metrics.last_cleanup_time
        
        # Only cleanup if enough time has passed since last cleanup
        if current_time - last_cleanup > self.cleanup_cooldown:
            logger.info("🧹 Triggering resource cleanup...")
            self.metrics.last_cleanup_time = current_time
            self.metrics.cleanup_count += 1
            
            # Perform cleanup
            self._perform_cleanup()

    def _perform_cleanup(self):
        """Perform comprehensive resource cleanup."""
        try:
            # 1. Force garbage collection
            logger.debug("Running garbage collection...")
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
            
            # 2. Clean up excess browser tabs
            if self._current_driver:
                self._cleanup_excess_tabs()
            
            # 3. Call registered cleanup callbacks
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in cleanup callback: {e}")
            
            logger.info("✅ Resource cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _cleanup_excess_tabs(self):
        """Close excess browser tabs to reduce memory usage."""
        if not self._current_driver:
            return
            
        try:
            handles = self._current_driver.window_handles
            if len(handles) > self.max_active_tabs:
                # Keep the first tab (main tab) and close the rest
                tabs_to_close = handles[1:self.max_active_tabs + 1]
                
                for handle in tabs_to_close:
                    try:
                        self._current_driver.switch_to.window(handle)
                        self._current_driver.close()
                        logger.debug(f"Closed tab: {handle}")
                    except Exception as e:
                        logger.debug(f"Error closing tab {handle}: {e}")
                
                # Switch back to the main tab
                if handles:
                    self._current_driver.switch_to.window(handles[0])
                
                logger.info(f"🧹 Closed {len(tabs_to_close)} excess tabs")
                
        except Exception as e:
            logger.error(f"Error cleaning up tabs: {e}")

    def register_driver(self, driver: WebDriver):
        """Register a WebDriver for resource management."""
        self._current_driver = driver
        logger.info("📝 Registered WebDriver for resource management")

    def unregister_driver(self):
        """Unregister the current WebDriver."""
        self._current_driver = None
        logger.info("📝 Unregistered WebDriver")

    def add_cleanup_callback(self, callback: Callable):
        """Add a cleanup callback function."""
        self._cleanup_callbacks.append(callback)
        logger.debug(f"Added cleanup callback: {callback.__name__}")

    def remove_cleanup_callback(self, callback: Callable):
        """Remove a cleanup callback function."""
        if callback in self._cleanup_callbacks:
            self._cleanup_callbacks.remove(callback)
            logger.debug(f"Removed cleanup callback: {callback.__name__}")

    def force_cleanup(self):
        """Force immediate resource cleanup."""
        logger.info("🧹 Forcing immediate resource cleanup...")
        self._perform_cleanup()

    def get_resource_summary(self) -> Dict[str, float]:
        """Get resource usage summary."""
        return {
            'active_tabs': self.metrics.active_tabs,
            'memory_usage_mb': self.metrics.memory_usage_mb,
            'cleanup_count': self.metrics.cleanup_count,
            'browser_restarts': self.metrics.browser_restarts,
            'last_cleanup_time': self.metrics.last_cleanup_time
        }

    def is_healthy(self) -> bool:
        """Check if resources are healthy."""
        return (
            self.metrics.memory_usage_mb < self.memory_cleanup_threshold and
            self.metrics.active_tabs <= self.max_active_tabs
        )

    def should_restart_browser(self) -> bool:
        """Check if browser should be restarted."""
        return (
            self.metrics.memory_usage_mb > self.memory_critical_threshold or
            self.metrics.active_tabs > self.max_active_tabs * 2
        )

    def restart_browser(self, driver_factory: Callable) -> Optional[WebDriver]:
        """Restart the browser with a new driver."""
        try:
            logger.warning("🔄 Restarting browser due to resource issues...")
            
            # Close current driver
            if self._current_driver:
                try:
                    self._current_driver.quit()
                except Exception as e:
                    logger.debug(f"Error closing driver: {e}")
            
            # Create new driver
            new_driver = driver_factory()
            self.register_driver(new_driver)
            
            self.metrics.browser_restarts += 1
            logger.info("✅ Browser restarted successfully")
            
            return new_driver
            
        except Exception as e:
            logger.error(f"❌ Failed to restart browser: {e}")
            return None

    def cleanup_tab_after_use(self, tab_handle: str):
        """Clean up a specific tab after use."""
        if not self._current_driver:
            return
            
        try:
            # Switch to the tab and close it
            self._current_driver.switch_to.window(tab_handle)
            self._current_driver.close()
            
            # Switch back to main tab
            handles = self._current_driver.window_handles
            if handles:
                self._current_driver.switch_to.window(handles[0])
            
            logger.debug(f"🧹 Cleaned up tab: {tab_handle}")
            
        except Exception as e:
            logger.debug(f"Error cleaning up tab {tab_handle}: {e}")

    def get_available_tab(self) -> Optional[str]:
        """Get an available tab handle or create a new one."""
        if not self._current_driver:
            return None
            
        try:
            handles = self._current_driver.window_handles
            
            # If we have fewer tabs than max, create a new one
            if len(handles) < self.max_active_tabs:
                self._current_driver.execute_script("window.open('');")
                new_handles = self._current_driver.window_handles
                new_tab = [h for h in new_handles if h not in handles][0]
                logger.debug(f"Created new tab: {new_tab}")
                return new_tab
            
            # Otherwise, return the first available tab
            return handles[0] if handles else None
            
        except Exception as e:
            logger.error(f"Error getting available tab: {e}")
            return None

    def __del__(self):
        """Cleanup when the manager is destroyed."""
        self.stop_monitoring() 