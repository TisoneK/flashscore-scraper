"""Selenium WebDriver setup and management."""
import logging
from typing import Optional
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
import os
import platform
from pathlib import Path
from src.config import CONFIG
from .chrome_driver import ChromeDriverManager
from .firefox_driver import FirefoxDriver
from dataclasses import asdict

# Get logger for this module
logger = logging.getLogger(__name__)

class WebDriverManager:
    """Manages the WebDriver instance and its lifecycle."""
    
    def __init__(self):
        """Initialize the WebDriver manager."""
        self.driver = None
        self._active = False
        self.logger = logging.getLogger(__name__)
        self.chrome_driver = ChromeDriverManager(asdict(CONFIG))
        self.firefox_driver = FirefoxDriver()
        
    def initialize(self) -> None:
        """Initialize the WebDriver with appropriate options."""
        if self.driver is not None:
            return
        
        browser_name = getattr(CONFIG.browser, 'browser_name', 'chrome').lower()
        
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