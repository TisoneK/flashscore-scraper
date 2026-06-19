"""Selenium WebDriver setup and management."""
import logging
from typing import Optional
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import os
import platform
from pathlib import Path
from src.utils.config_loader import CONFIG
from .chrome_driver import ChromeDriverManager
from .firefox_driver import FirefoxDriver

# Get logger for this module
logger = logging.getLogger(__name__)

class WebDriverManager:
    """Manages the WebDriver instance and its lifecycle."""
    
    def __init__(self, chrome_log_path: str = None):
        """Initialize the WebDriver manager."""
        self.driver = None
        self._active = False
        self._is_closing = False
        self.logger = logging.getLogger(__name__)
        # Convert CONFIG to dict if it's not already
        config_dict = dict(CONFIG) if not isinstance(CONFIG, dict) else CONFIG
        self.chrome_driver = ChromeDriverManager(config_dict, chrome_log_path=chrome_log_path)
        self.firefox_driver = FirefoxDriver()
        
    def initialize(self) -> None:
        """Initialize the WebDriver with appropriate options."""
        if self.driver is not None:
            return
        
        browser_name = CONFIG.get('browser', {}).get('browser_name', 'chrome').lower()
        
        # Detect OS
        system = platform.system().lower()  # 'windows', 'linux', 'darwin'
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Initialize the appropriate driver
        if browser_name == 'chrome':
            self.driver = self.chrome_driver.create_driver()
        elif browser_name == 'firefox':
            self.driver = self.firefox_driver.initialize(system, project_root)
        else:
            raise ValueError(f"Unsupported browser: {browser_name}")
            
        self._active = True
        self.logger.info("WebDriver initialized successfully")
            
    def get_driver(self) -> Optional[webdriver.Remote]:
        """
        Get the WebDriver instance, initializing it if necessary.
        
        Returns:
            Optional[webdriver.Remote]: The WebDriver instance, or None if initialization fails
        """
        # Don't create new drivers during shutdown
        if self._is_closing:
            return None
            
        if self.driver is not None and not self._is_valid_session():
            self.logger.warning("Existing WebDriver session is invalid, creating a new one...")
            self.close(force=True)
            self.driver = None
            
        if self.driver is None:
            try:
                self.initialize()
            except Exception as e:
                self.logger.error(f"Failed to initialize WebDriver: {e}")
                return None
                
        return self.driver
        
    def _is_valid_session(self) -> bool:
        """Check if the current WebDriver session is still valid."""
        if self.driver is None:
            return False
            
        try:
            # Try to get the current URL - if this fails, the session is invalid
            _ = self.driver.current_url
            return True
        except Exception as e:
            self.logger.debug(f"WebDriver session is invalid: {e}")
            return False
        
    def close(self, force: bool = False) -> None:
        """
        Close the WebDriver instance if it exists.
        Fast path for shutdown - no window enumeration, no network calls.
        
        Args:
            force: If True, force kill browser processes if normal shutdown fails
        """
        self._is_closing = True
        
        if not hasattr(self, 'driver') or self.driver is None:
            self.logger.debug("No WebDriver instance to close")
            return
            
        try:
            # Fast path: just quit once, no window enumeration
            self.logger.debug("Closing WebDriver...")
            self.driver.quit()
            self.logger.debug("WebDriver closed successfully")
            self._active = False
            
        except Exception as e:
            self.logger.debug(f"WebDriver quit failed: {e}")
            
            # If force=True, kill processes directly
            if force:
                self.logger.debug("Force killing browser processes...")
                self._kill_browser_processes()
            
        finally:
            # Clear references
            self.driver = None
            self._active = False
    
    def _kill_browser_processes(self) -> None:
        """Force kill any remaining browser processes."""
        try:
            import psutil
            import os
            import time
            
            # Get current process ID to avoid killing ourselves
            current_pid = os.getpid()
            current_process = psutil.Process(current_pid)
            
            # List of Chrome-related process names only (avoid killing Edge)
            browser_processes = [
                'chrome', 'chromedriver', 'google-chrome'
            ]
            
            def kill_process_tree(proc, timeout=3):
                """Kill a process and all its children."""
                try:
                    children = proc.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    gone, still_alive = psutil.wait_procs(children, timeout=timeout)
                    for p in still_alive:
                        try:
                            p.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except psutil.TimeoutExpired:
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # First, try to kill any direct child processes
            try:
                for child in current_process.children(recursive=True):
                    try:
                        proc = psutil.Process(child.pid)
                        proc_name = proc.name().lower()
                        if any(browser in proc_name for browser in browser_processes):
                            self.logger.warning(f"Killing child browser process: {proc.name()} (PID: {proc.pid})")
                            kill_process_tree(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception as e:
                self.logger.warning(f"Error killing child processes: {e}")
            
            # Then, kill any other matching processes
            killed_pids = set()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Skip current process and already killed processes
                    if proc.pid == current_pid or proc.pid in killed_pids:
                        continue
                        
                    # Check if process name matches any browser process
                    proc_name = proc.name().lower()
                    if any(browser in proc_name for browser in browser_processes):
                        self.logger.warning(f"Killing browser process: {proc.name()} (PID: {proc.pid})")
                        try:
                            kill_process_tree(proc)
                            killed_pids.add(proc.pid)
                        except Exception as e:
                            self.logger.warning(f"Failed to kill process {proc.pid}: {e}")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if killed_pids:
                self.logger.info(f"Successfully killed {len(killed_pids)} browser processes")
            else:
                self.logger.info("No browser processes were found running")
                
        except Exception as e:
            self.logger.error(f"Error in process cleanup: {e}")
            raise
                
    def is_active(self) -> bool:
        """Check if the WebDriver is currently active."""
        return self._active and self.driver is not None