"""Selenium WebDriver setup and management."""
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import os
import urllib3
from src.utils.config_loader import CONFIG
import platform
from pathlib import Path

from .config import CHROME_OPTIONS

# Get logger for this module
logger = logging.getLogger(__name__)

# Managed Chrome profile dirs — named so stale ones from CRASHED runs are
# recognizable and sweepable. A crashed Chrome leaves its temp profile (and
# its SingletonLock) behind; enough of those fill /tmp and no new session
# can ever start again — the "can't recover after a crash" failure mode.
PROFILE_PREFIX = "fs-scraper-profile-"


def cleanup_stale_chrome(kill_processes: bool = False, max_age_s: int = 3600) -> None:
    """Best-effort recovery sweep after (or before) Chrome crashes.

    - Removes stale managed profile dirs in /tmp older than max_age_s
      (a live scrape's profile is younger; a crashed run's is not).
    - Optionally pkills chrome/chromedriver — ONLY safe when the caller
      knows no legitimate browser session should be alive (e.g. batch
      scrape startup). Linux-only: on a dev machine this would kill the
      developer's own Chrome.
    """
    import shutil
    import tempfile
    import time as _time

    tmp = tempfile.gettempdir()
    try:
        for name in os.listdir(tmp):
            if not name.startswith(PROFILE_PREFIX):
                continue
            path = os.path.join(tmp, name)
            try:
                if _time.time() - os.path.getmtime(path) > max_age_s:
                    shutil.rmtree(path, ignore_errors=True)
                    logger.info(f"Swept stale Chrome profile: {name}")
            except OSError:
                pass
    except OSError:
        pass

    if kill_processes and platform.system().lower() == "linux":
        import subprocess
        for pattern in ("chrome", "chromedriver"):
            try:
                subprocess.run(["pkill", "-9", "-f", pattern], timeout=5, capture_output=True)
            except Exception:
                pass
        logger.info("Killed leftover chrome/chromedriver processes (recovery sweep)")


class WebDriverManager:
    """Manages the WebDriver instance and its lifecycle."""

    def __init__(self):
        """Initialize the WebDriver manager."""
        self.driver = None
        self._active = False
        self._profile_dir: Optional[str] = None
        self.logger = logging.getLogger(__name__)
        
    def _get_platform_paths(self, system: str, project_root: str) -> tuple[Optional[str], Optional[str]]:
        """Get platform-specific driver and browser binary paths."""
        driver_path = None
        chrome_binary_path = None
        
        if system == 'windows':
            # Windows paths
            driver_path = os.path.join(project_root, 'drivers', 'windows', 'chromedriver.exe')
            chrome_binary_path = os.path.join(project_root, 'drivers', 'windows', 'chrome-win64', 'chrome.exe')
        elif system == 'linux':
            # Linux paths
            driver_path = os.path.join(project_root, 'drivers', 'linux', 'chromedriver')
            chrome_binary_path = os.path.join(project_root, 'drivers', 'linux', 'chrome')
        elif system == 'darwin':
            # macOS paths
            driver_path = os.path.join(project_root, 'drivers', 'mac', 'chromedriver')
            chrome_binary_path = os.path.join(project_root, 'drivers', 'mac', 'chrome')
        else:
            # Unknown platform
            logger.warning(f"Unknown platform: {system}, using system defaults")
            
        return driver_path, chrome_binary_path
    
    def _get_firefox_paths(self, system: str, project_root: str) -> tuple[Optional[str], Optional[str]]:
        """Get platform-specific Firefox driver and browser binary paths."""
        driver_path = None
        firefox_binary_path = None
        
        if system == 'windows':
            driver_path = os.path.join(project_root, 'drivers', 'windows', 'geckodriver.exe')
        elif system == 'linux':
            driver_path = os.path.join(project_root, 'drivers', 'linux', 'geckodriver')
        elif system == 'darwin':
            driver_path = os.path.join(project_root, 'drivers', 'mac', 'geckodriver')
        else:
            logger.warning(f"Unknown platform: {system}, using system defaults")
            
        return driver_path, firefox_binary_path
        
    def initialize(self) -> None:
        """Initialize the WebDriver with appropriate options."""
        if self.driver is not None:
            # The cached driver may be DEAD (its Chrome crashed underneath
            # it). Reusing a dead driver fails every call until close() —
            # the "can't recover after a crash" loop. Probe it; if dead,
            # discard and fall through to a fresh session.
            try:
                self.driver.execute_script("return 1")
                return
            except WebDriverException:
                self.logger.warning(
                    "Cached WebDriver is dead (Chrome crashed underneath it) — "
                    "discarding and re-initializing"
                )
                self.close()
        
        browser_name = CONFIG.get('browser', {}).get('browser_name', 'chrome').lower()
        options = None
        service = None
        driver_path = None
        
        # Detect OS
        system = platform.system().lower()  # 'windows', 'linux', 'darwin'
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Set up options and driver path for Chrome or Firefox
        browser_config = CONFIG.get('browser', {})
        if browser_name == 'chrome':
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService
            options = ChromeOptions()
            if browser_config.get('headless', False):
                options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            # Managed, uniquely-named profile dir: crashed runs leave their
            # profile (and SingletonLock) behind — naming them lets
            # cleanup_stale_chrome() sweep the wreckage so new sessions can
            # always start.
            import tempfile
            self._profile_dir = tempfile.mkdtemp(prefix=PROFILE_PREFIX)
            options.add_argument(f'--user-data-dir={self._profile_dir}')
            window_size = browser_config.get('window_size', [1920, 1080])
            options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')
            # Comprehensive browser console output suppression
            options.add_argument('--log-level=3')  # Only fatal errors
            options.add_argument('--silent')
            options.add_argument('--disable-logging')
            options.add_argument('--disable-gpu-logging')
            options.add_argument('--disable-background-logging')
            options.add_argument('--disable-component-logging')
            options.add_argument('--disable-extensions-logging')
            options.add_argument('--disable-ipc-logging')
            options.add_argument('--disable-perf-logging')
            options.add_argument('--disable-renderer-logging')
            options.add_argument('--disable-service-logging')
            options.add_argument('--disable-web-security-logging')
            options.add_argument('--log-file=/dev/null')  # Redirect logs to null
            options.add_argument('--enable-logging=false')
            options.add_argument('--v=0')  # Verbose level 0
            options.add_argument('--vmodule=*=0')  # Disable all verbose modules
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            if browser_config.get('disable_images', False):
                options.add_argument('--blink-settings=imagesEnabled=false')
            if browser_config.get('disable_javascript', False):
                options.add_argument('--disable-javascript')
            if browser_config.get('disable_css', False):
                options.add_argument('--disable-css')
            if browser_config.get('ignore_certificate_errors', False):
                options.add_argument('--ignore-certificate-errors')
            user_agent = browser_config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            options.add_argument(f'user-agent={user_agent}')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Enhanced platform-independent Chrome binary detection
            driver_path, chrome_binary_path = self._get_platform_paths(system, project_root)
            
            # Check for Chrome binary in local installation
            if chrome_binary_path and os.path.exists(chrome_binary_path):
                self.logger.info(f"Found Chrome binary at: {chrome_binary_path}")
                options.binary_location = chrome_binary_path
            else:
                # Fallback to system Chrome
                self.logger.info("Chrome binary not found in local installation, using system Chrome")
            
            # Determine driver path
            if browser_config.get('driver_path') and os.path.exists(browser_config['driver_path']):
                driver_path = browser_config['driver_path']
                self.logger.info(f"Using configured driver path: {driver_path}")
            elif driver_path and os.path.exists(driver_path):
                self.logger.info(f"Using local ChromeDriver: {driver_path}")
            else:
                self.logger.warning(f"Local ChromeDriver not found at {driver_path}")
                driver_path = None
            
            # Start Chrome WebDriver
            if driver_path and os.path.exists(driver_path):
                resolved_path = driver_path
                self.driver = self._create_chrome_with_recovery(
                    lambda: webdriver.Chrome(
                        service=ChromeService(executable_path=resolved_path),
                        options=options,
                    )
                )
                self.logger.info(f"Using ChromeDriver: {driver_path}")
            else:
                self.driver = self._create_chrome_with_recovery(
                    lambda: webdriver.Chrome(options=options)
                )
                self.logger.warning(f"Local ChromeDriver not found, using system ChromeDriver")
                
        elif browser_name == 'firefox':
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService
            options = FirefoxOptions()
            if browser_config.get('headless', False):
                options.add_argument('--headless')
            window_size = browser_config.get('window_size', [1920, 1080])
            options.add_argument(f'--width={window_size[0]}')
            options.add_argument(f'--height={window_size[1]}')
            
            # Determine driver path
            driver_path, firefox_binary_path = self._get_firefox_paths(system, project_root)
            
            if browser_config.get('driver_path') and os.path.exists(browser_config['driver_path']):
                driver_path = browser_config['driver_path']
                self.logger.info(f"Using configured driver path: {driver_path}")
            elif driver_path and os.path.exists(driver_path):
                self.logger.info(f"Using local GeckoDriver: {driver_path}")
            else:
                self.logger.warning(f"Local GeckoDriver not found at {driver_path}")
                driver_path = None
                
            # Start Firefox WebDriver
            if driver_path and os.path.exists(driver_path):
                service = FirefoxService(executable_path=driver_path)
                self.driver = webdriver.Firefox(service=service, options=options)
                self.logger.info(f"Using GeckoDriver: {driver_path}")
            else:
                self.driver = webdriver.Firefox(options=options)
                self.logger.warning(f"Local GeckoDriver not found, using system GeckoDriver")
        else:
            raise ValueError(f"Unsupported browser: {browser_name}")
            
        # Anti-detection for Chrome only
        if browser_name == 'chrome' and self.driver is not None:
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
        self._active = True
        self.logger.info("WebDriver initialized successfully")
            
    def _create_chrome_with_recovery(self, factory):
        """Create a Chrome session; on 'session not created' sweep stale
        profiles and retry ONCE. A single crash must never wedge the
        scraper permanently — that was the pre-2026-07 behavior: the
        exception propagated, nothing cleaned up, and every subsequent
        launch hit the same leftover wreckage."""
        try:
            return factory()
        except WebDriverException as exc:
            msg = str(exc).lower()
            if "session not created" not in msg and "chrome" not in msg:
                raise
            self.logger.warning(
                f"Chrome session failed to start ({exc}) — sweeping stale "
                "profiles and retrying once"
            )
            cleanup_stale_chrome(kill_processes=False)
            import time as _time
            _time.sleep(3)
            return factory()

    def get_driver(self) -> Optional[webdriver.Remote]:
        """Get the WebDriver instance, initializing it if necessary."""
        if self.driver is None:
            self.initialize()
        return self.driver
        
    def close(self) -> None:
        """Close the WebDriver instance if it exists."""
        if self.driver is not None:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {str(e)}")
            finally:
                self.driver = None
                self._active = False
                if self._profile_dir:
                    import shutil
                    shutil.rmtree(self._profile_dir, ignore_errors=True)
                    self._profile_dir = None
                
    def is_active(self) -> bool:
        """Check if the WebDriver is currently active."""
        return self._active and self.driver is not None

urllib3.PoolManager(maxsize=10, retries=3)
 

