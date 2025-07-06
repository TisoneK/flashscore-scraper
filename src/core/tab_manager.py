"""Tab management for the scraper."""
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException, TimeoutException, StaleElementReferenceException
)
import threading

logger = logging.getLogger(__name__)

@dataclass
class TabState:
    """State information for a browser tab."""
    is_healthy: bool = True
    last_used: float = field(default_factory=time.time)
    processing_time: float = 0.0
    failure_count: int = 0
    max_failures: int = 3
    current_url: Optional[str] = None
    is_loading: bool = False
    last_load_time: float = 0.0

class TabManager:
    """Manages browser tabs for parallel processing."""
    
    def __init__(self, driver: WebDriver, max_tabs: int = 1):
        """Initialize the tab manager.
        
        Args:
            driver: Selenium WebDriver instance
            max_tabs: Maximum number of tabs to use (default: 1)
        """
        self.driver = driver
        self.max_tabs = max_tabs
        self.tab_states: Dict[int, TabState] = {}
        self._lock = threading.Lock()
        self._tab_event = threading.Event()
        self.min_load_interval = 2.0  # Minimum seconds between loads in same tab
        
        logger.info(f"Initialized TabManager with max_tabs={max_tabs}")
        
    def setup_tabs(self) -> bool:
        """Set up the required number of tabs.
        
        Returns:
            bool: True if setup was successful
        """
        if not self.driver:
            logger.error("No WebDriver instance available")
            return False
            
        try:
            logger.info(f"Setting up {self.max_tabs} tab...")
            
            # Initialize main tab
            self.tab_states[0] = TabState()
            logger.debug("Initialized main tab")
            
            # Open additional tabs if needed
            for i in range(1, self.max_tabs):
                try:
                    self.driver.execute_script("window.open('about:blank', '_blank');")
                    self.tab_states[i] = TabState()
                    logger.debug(f"Opened and initialized tab {i}")
                except WebDriverException as e:
                    logger.error(f"Failed to open tab {i}: {e}")
                    return False
                    
            logger.info(f"Successfully set up {self.max_tabs} tab")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up tabs: {e}")
            return False

    def get_next_tab(self) -> int:
        """Get the next available tab index.
        
        Returns:
            int: Index of the next available tab
            
        Raises:
            RuntimeError: If no healthy tabs are available
        """
        if not self.driver:
            self.setup_tabs()
            
        with self._lock:
            # Find the least recently used healthy tab
            healthy_tabs = [
                (idx, state) for idx, state in self.tab_states.items()
                if state.is_healthy and not state.is_loading
            ]
            
            if not healthy_tabs:
                # If no healthy tabs, try to recover one
                self._recover_tabs()
                healthy_tabs = [
                    (idx, state) for idx, state in self.tab_states.items()
                    if state.is_healthy and not state.is_loading
                ]
                if not healthy_tabs:
                    # Last resort: try to use any tab that's not loading
                    available_tabs = [
                        (idx, state) for idx, state in self.tab_states.items()
                        if not state.is_loading
                    ]
                    if available_tabs:
                        tab_index = min(available_tabs, key=lambda x: x[1].last_used)[0]
                        self.tab_states[tab_index].is_healthy = True  # Give it another chance
                        self.tab_states[tab_index].last_used = time.time()
                        self.tab_states[tab_index].is_loading = True
                        return tab_index
                    raise RuntimeError("No healthy tabs available")
            
            # Get the least recently used tab
            tab_index = min(healthy_tabs, key=lambda x: x[1].last_used)[0]
            self.tab_states[tab_index].last_used = time.time()
            self.tab_states[tab_index].is_loading = True
            return tab_index

    def switch_to_tab(self, tab_index: int) -> bool:
        """Switch to a specific tab and verify it's ready.
        
        Args:
            tab_index: Index of the tab to switch to
            
        Returns:
            bool: True if switch was successful, False otherwise
        """
        try:
            if not self._tab_event.is_set():
                self._tab_event.wait(timeout=10)  # Wait for any ongoing tab operations
            
            self._tab_event.clear()
            try:
                # Get the window handle for this tab
                handles = self.driver.window_handles
                if tab_index >= len(handles):
                    logger.error(f"Tab index {tab_index} out of range")
                    return False
                    
                # Switch to the tab
                self.driver.switch_to.window(handles[tab_index])
                
                # Just verify the tab is responsive
                self.driver.execute_script("return document.readyState")
                
                return True
                
            finally:
                self._tab_event.set()
                
        except WebDriverException as e:
            logger.error(f"Error switching to tab {tab_index}: {e}")
            # Don't mark as unhealthy immediately, increment failure count
            with self._lock:
                if tab_index in self.tab_states:
                    self.tab_states[tab_index].failure_count += 1
                    if self.tab_states[tab_index].failure_count >= self.tab_states[tab_index].max_failures:
                        self._mark_tab_unhealthy(tab_index)
            return False

    def load_url(self, tab_index: int, url: str, timeout: int = 30) -> bool:
        """Load a URL in a specific tab.
        
        Args:
            tab_index: Index of the tab to use
            url: URL to load
            timeout: Maximum time to wait for page load
            
        Returns:
            bool: True if URL was loaded successfully, False otherwise
        """
        if not self.switch_to_tab(tab_index):
            return False
            
        try:
            if not self._tab_event.is_set():
                self._tab_event.wait(timeout=10)
                
            self._tab_event.clear()
            try:
                # Check if we need to wait before loading
                state = self.tab_states[tab_index]
                time_since_last = time.time() - state.last_load_time
                if time_since_last < self.min_load_interval:
                    time.sleep(self.min_load_interval - time_since_last)
                
                # Load the URL
                self.driver.get(url)
                state.last_load_time = time.time()
                state.current_url = url
                state.is_loading = False
                
                # Wait for page load
                WebDriverWait(self.driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Mark tab as healthy
                self.mark_tab_healthy(tab_index)
                return True
                
            finally:
                self._tab_event.set()
                
        except Exception as e:
            logger.error(f"Error loading URL in tab {tab_index}: {e}")
            self._mark_tab_unhealthy(tab_index)
            self.tab_states[tab_index].is_loading = False
            return False

    def mark_tab_unhealthy(self, tab_index: int) -> None:
        """Mark a tab as unhealthy."""
        with self._lock:
            if tab_index in self.tab_states:
                self.tab_states[tab_index].is_healthy = False
                self.tab_states[tab_index].failure_count += 1
                self.tab_states[tab_index].is_loading = False
                logger.warning(f"Tab {tab_index} marked as unhealthy after {self.tab_states[tab_index].failure_count} failures")

    def mark_tab_healthy(self, tab_index: int) -> None:
        """Mark a tab as healthy."""
        with self._lock:
            if tab_index in self.tab_states:
                self.tab_states[tab_index].is_healthy = True
                self.tab_states[tab_index].failure_count = 0
                self.tab_states[tab_index].is_loading = False
                logger.debug(f"Tab {tab_index} marked as healthy")

    def record_tab_processing_time(self, tab_index: int, processing_time: float) -> None:
        """Record processing time for a tab."""
        with self._lock:
            if tab_index in self.tab_states:
                self.tab_states[tab_index].processing_time += processing_time

    def get_tab_stats(self) -> Dict[int, Dict]:
        """Get statistics for all tabs."""
        return {
            idx: {
                'is_healthy': state.is_healthy,
                'failure_count': state.failure_count,
                'processing_time': state.processing_time,
                'last_used': time.time() - state.last_used,
                'current_url': state.current_url,
                'is_loading': state.is_loading
            }
            for idx, state in self.tab_states.items()
        }

    def cleanup(self) -> None:
        """Clean up tabs, leaving only the first one."""
        try:
            if not self._tab_event.is_set():
                self._tab_event.wait(timeout=10)
                
            self._tab_event.clear()
            try:
                # Store the first window handle
                first_handle = self.driver.window_handles[0]
                
                # Close all other tabs
                for handle in self.driver.window_handles[1:]:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
                
                # Switch back to the first tab
                self.driver.switch_to.window(first_handle)
                
                # Clear tab states
                self.tab_states.clear()
                self.tab_states[0] = TabState()
                
            finally:
                self._tab_event.set()
                
        except Exception as e:
            logger.error(f"Error during tab cleanup: {e}")

    def _recover_tabs(self) -> None:
        """Attempt to recover unhealthy tabs."""
        with self._lock:
            for tab_index, state in self.tab_states.items():
                if not state.is_healthy and state.failure_count < state.max_failures:
                    # Give the tab another chance
                    state.is_healthy = True
                    state.failure_count = 0
                    logger.info(f"Recovered tab {tab_index}")

    def _mark_tab_unhealthy(self, tab_index: int) -> None:
        """Mark a tab as unhealthy and attempt recovery."""
        with self._lock:
            if tab_index in self.tab_states:
                self.tab_states[tab_index].is_healthy = False
                self.tab_states[tab_index].failure_count += 1
                self.tab_states[tab_index].is_loading = False
                if self.tab_states[tab_index].failure_count < 3:
                    self._recover_tabs() 