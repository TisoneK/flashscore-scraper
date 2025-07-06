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
from src.config import CONFIG
import platform

from .config import CHROME_OPTIONS

# Get logger for this module
logger = logging.getLogger(__name__)

class WebDriverManager:
    """Manages the WebDriver instance and its lifecycle."""
    
    def __init__(self):
        """Initialize the WebDriver manager."""
        self.driver = None
        self._active = False
        self.logger = logging.getLogger(__name__)
        
    def initialize(self) -> None:
        """Initialize the WebDriver with appropriate options."""
        if self.driver is not None:
            return
        
        browser_name = getattr(CONFIG.browser, 'browser_name', 'chrome').lower()
        options = None
        service = None
        driver_path = None
        
        # Detect OS
        system = platform.system().lower()  # 'windows', 'linux', 'darwin'
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Set up options and driver path for Chrome or Firefox
        if browser_name == 'chrome':
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService
            options = ChromeOptions()
            if CONFIG.browser.headless:
                options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'--window-size={CONFIG.browser.window_size[0]},{CONFIG.browser.window_size[1]}')
            # Suppress browser console output
            options.add_argument('--log-level=3')  # Only fatal errors
            options.add_argument('--silent')
            options.add_argument('--disable-logging')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            if CONFIG.browser.disable_images:
                options.add_argument('--blink-settings=imagesEnabled=false')
            if CONFIG.browser.disable_javascript:
                options.add_argument('--disable-javascript')
            if CONFIG.browser.disable_css:
                options.add_argument('--disable-css')
            if CONFIG.browser.ignore_certificate_errors:
                options.add_argument('--ignore-certificate-errors')
            options.add_argument(f'user-agent={CONFIG.browser.user_agent}')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            # Determine driver path
            if CONFIG.browser.driver_path and os.path.exists(CONFIG.browser.driver_path):
                driver_path = CONFIG.browser.driver_path
            else:
                if system == 'windows':
                    local_driver_path = os.path.join(project_root, 'drivers', 'windows', 'chromedriver.exe')
                elif system == 'linux':
                    local_driver_path = os.path.join(project_root, 'drivers', 'linux', 'chromedriver')
                elif system == 'darwin':
                    local_driver_path = os.path.join(project_root, 'drivers', 'mac', 'chromedriver')
                else:
                    local_driver_path = None
                if local_driver_path and os.path.exists(local_driver_path):
                    driver_path = local_driver_path
            # Start Chrome WebDriver
            if driver_path and os.path.exists(driver_path):
                service = ChromeService(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                self.logger.info(f"Using ChromeDriver: {driver_path}")
            else:
                self.driver = webdriver.Chrome(options=options)
                self.logger.warning(f"Local ChromeDriver not found, using system ChromeDriver")
        elif browser_name == 'firefox':
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService
            options = FirefoxOptions()
            if CONFIG.browser.headless:
                options.add_argument('--headless')
            options.add_argument(f'--width={CONFIG.browser.window_size[0]}')
            options.add_argument(f'--height={CONFIG.browser.window_size[1]}')
            # Determine driver path
            if CONFIG.browser.driver_path and os.path.exists(CONFIG.browser.driver_path):
                driver_path = CONFIG.browser.driver_path
            else:
                if system == 'windows':
                    local_driver_path = os.path.join(project_root, 'drivers', 'windows', 'geckodriver.exe')
                elif system == 'linux':
                    local_driver_path = os.path.join(project_root, 'drivers', 'linux', 'geckodriver')
                elif system == 'darwin':
                    local_driver_path = os.path.join(project_root, 'drivers', 'mac', 'geckodriver')
                else:
                    local_driver_path = None
                if local_driver_path and os.path.exists(local_driver_path):
                    driver_path = local_driver_path
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
            
    def get_driver(self) -> webdriver.Chrome:
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
                
    def is_active(self) -> bool:
        """Check if the WebDriver is currently active."""
        return self._active and self.driver is not None

urllib3.PoolManager(maxsize=10, retries=3)
 

