"""Chrome WebDriver management for FlashScore Scraper."""
import logging
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
import os
import platform
from pathlib import Path
from src.config import CONFIG

logger = logging.getLogger(__name__)

class ChromeDriver:
    """Manages Chrome WebDriver setup and configuration."""
    
    def __init__(self):
        """Initialize Chrome driver manager."""
        self.logger = logging.getLogger(__name__)
    
    def _get_platform_paths(self, system: str, project_root: str) -> Tuple[Optional[str], Optional[str]]:
        """Get platform-specific Chrome driver and browser binary paths."""
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
    
    def create_options(self) -> ChromeOptions:
        """Create Chrome options based on configuration."""
        options = ChromeOptions()
        
        # Use chrome_options configuration if available, otherwise fall back to browser config
        chrome_config = getattr(CONFIG, 'chrome_options', None)
        
        if chrome_config:
            # Use the dedicated Chrome options configuration
            for option in chrome_config.to_list():
                options.add_argument(option)
        else:
            # Fall back to browser configuration
            if CONFIG.browser.headless:
                options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'--window-size={CONFIG.browser.window_size[0]},{CONFIG.browser.window_size[1]}')
        
        # Suppress browser console output
        options.add_argument('--log-level=3')  # Only fatal errors
        options.add_argument('--silent')
        options.add_argument('--disable-logging')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Performance options from browser config
        if CONFIG.browser.disable_images:
            options.add_argument('--blink-settings=imagesEnabled=false')
        if CONFIG.browser.disable_javascript:
            options.add_argument('--disable-javascript')
        if CONFIG.browser.disable_css:
            options.add_argument('--disable-css')
        if CONFIG.browser.ignore_certificate_errors:
            options.add_argument('--ignore-certificate-errors')
        
        # User agent and anti-detection
        options.add_argument(f'user-agent={CONFIG.browser.user_agent}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        return options
    
    def setup_binary_location(self, options: ChromeOptions, system: str, project_root: str) -> None:
        """Set up Chrome binary location if available."""
        _, chrome_binary_path = self._get_platform_paths(system, project_root)
        
        # Check for Chrome binary in local installation
        if chrome_binary_path and os.path.exists(chrome_binary_path):
            self.logger.info(f"Found Chrome binary at: {chrome_binary_path}")
            options.binary_location = chrome_binary_path
        else:
            # Fallback to system Chrome
            self.logger.info("Chrome binary not found in local installation, using system Chrome")
    
    def get_driver_path(self, system: str, project_root: str) -> Optional[str]:
        """Get the appropriate ChromeDriver path."""
        driver_path, _ = self._get_platform_paths(system, project_root)
        
        # Check configured driver path first
        if CONFIG.browser.driver_path and os.path.exists(CONFIG.browser.driver_path):
            driver_path = CONFIG.browser.driver_path
            self.logger.info(f"Using configured driver path: {driver_path}")
        elif driver_path and os.path.exists(driver_path):
            self.logger.info(f"Using local ChromeDriver: {driver_path}")
        else:
            self.logger.warning(f"Local ChromeDriver not found at {driver_path}")
            driver_path = None
        
        return driver_path
    
    def create_driver(self, options: ChromeOptions, driver_path: Optional[str] = None) -> webdriver.Chrome:
        """Create and return a Chrome WebDriver instance."""
        if driver_path and os.path.exists(driver_path):
            service = ChromeService(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            self.logger.info(f"Using ChromeDriver: {driver_path}")
        else:
            driver = webdriver.Chrome(options=options)
            self.logger.warning("Local ChromeDriver not found, using system ChromeDriver")
        
        # Anti-detection
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception:
            pass
        
        return driver
    
    def initialize(self, system: str, project_root: str) -> webdriver.Chrome:
        """Initialize Chrome WebDriver with all necessary setup."""
        # Create options
        options = self.create_options()
        
        # Setup binary location
        self.setup_binary_location(options, system, project_root)
        
        # Get driver path
        driver_path = self.get_driver_path(system, project_root)
        
        # Create and return driver
        return self.create_driver(options, driver_path) 