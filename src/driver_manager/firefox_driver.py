"""Firefox WebDriver management for FlashScore Scraper."""
import logging
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import os
import platform
from pathlib import Path
from src.config import CONFIG

logger = logging.getLogger(__name__)

class FirefoxDriver:
    """Manages Firefox WebDriver setup and configuration."""
    
    def __init__(self):
        """Initialize Firefox driver manager."""
        self.logger = logging.getLogger(__name__)
    
    def _get_platform_paths(self, system: str, project_root: str) -> Tuple[Optional[str], Optional[str]]:
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
    
    def create_options(self) -> FirefoxOptions:
        """Create Firefox options based on configuration."""
        options = FirefoxOptions()
        
        # Basic options
        if CONFIG.browser.headless:
            options.add_argument('--headless')
        options.add_argument(f'--width={CONFIG.browser.window_size[0]}')
        options.add_argument(f'--height={CONFIG.browser.window_size[1]}')
        
        # Performance options
        if CONFIG.browser.disable_images:
            options.set_preference('permissions.default.image', 2)
        if CONFIG.browser.disable_javascript:
            options.set_preference('javascript.enabled', False)
        if CONFIG.browser.disable_css:
            options.set_preference('permissions.default.stylesheet', 2)
        if CONFIG.browser.ignore_certificate_errors:
            options.set_preference('network.http.ssl-token-cache-size', 0)
        
        # User agent
        options.set_preference('general.useragent.override', CONFIG.browser.user_agent)
        
        # Additional Firefox-specific preferences
        options.set_preference('dom.webdriver.enabled', False)
        options.set_preference('useAutomationExtension', False)
        options.set_preference('general.useragent.override', CONFIG.browser.user_agent)
        
        return options
    
    def get_driver_path(self, system: str, project_root: str) -> Optional[str]:
        """Get the appropriate GeckoDriver path."""
        driver_path, _ = self._get_platform_paths(system, project_root)
        
        # Check configured driver path first
        if CONFIG.browser.driver_path and os.path.exists(CONFIG.browser.driver_path):
            driver_path = CONFIG.browser.driver_path
            self.logger.info(f"Using configured driver path: {driver_path}")
        elif driver_path and os.path.exists(driver_path):
            self.logger.info(f"Using local GeckoDriver: {driver_path}")
        else:
            self.logger.warning(f"Local GeckoDriver not found at {driver_path}")
            driver_path = None
        
        return driver_path
    
    def create_driver(self, options: FirefoxOptions, driver_path: Optional[str] = None) -> webdriver.Firefox:
        """Create and return a Firefox WebDriver instance."""
        if driver_path and os.path.exists(driver_path):
            service = FirefoxService(executable_path=driver_path)
            driver = webdriver.Firefox(service=service, options=options)
            self.logger.info(f"Using GeckoDriver: {driver_path}")
        else:
            driver = webdriver.Firefox(options=options)
            self.logger.warning("Local GeckoDriver not found, using system GeckoDriver")
        
        return driver
    
    def initialize(self, system: str, project_root: str) -> webdriver.Firefox:
        """Initialize Firefox WebDriver with all necessary setup."""
        # Create options
        options = self.create_options()
        
        # Get driver path
        driver_path = self.get_driver_path(system, project_root)
        
        # Create and return driver
        return self.create_driver(options, driver_path) 