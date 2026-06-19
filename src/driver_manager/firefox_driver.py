"""Firefox WebDriver management for FlashScore Scraper."""
import logging
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import os
import platform
from pathlib import Path
from src.utils.config_loader import CONFIG

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
        browser_config = CONFIG.get('browser', {})
        if browser_config.get('headless', False):
            options.add_argument('--headless')
        window_size = browser_config.get('window_size', [1920, 1080])
        options.add_argument(f'--width={window_size[0]}')
        options.add_argument(f'--height={window_size[1]}')
        
        # Performance options
        if browser_config.get('disable_images', False):
            options.set_preference('permissions.default.image', 2)
        if browser_config.get('disable_javascript', False):
            options.set_preference('javascript.enabled', False)
        if browser_config.get('disable_css', False):
            options.set_preference('permissions.default.stylesheet', 2)
        if browser_config.get('ignore_certificate_errors', False):
            options.set_preference('network.http.ssl-token-cache-size', 0)
        
        # User agent
        user_agent = browser_config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.set_preference('general.useragent.override', user_agent)
        
        # Additional Firefox-specific preferences
        options.set_preference('dom.webdriver.enabled', False)
        options.set_preference('useAutomationExtension', False)
        options.set_preference('general.useragent.override', user_agent)
        
        return options
    
    def get_driver_path(self, system: str, project_root: str) -> Optional[str]:
        """Get the appropriate GeckoDriver path."""
        driver_path, _ = self._get_platform_paths(system, project_root)
        
        # Check configured driver path first
        browser_config = CONFIG.get('browser', {})
        if browser_config.get('driver_path') and os.path.exists(browser_config['driver_path']):
            driver_path = browser_config['driver_path']
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