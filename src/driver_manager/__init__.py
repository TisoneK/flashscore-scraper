"""
Driver Manager Module for FlashScore Scraper

This module provides comprehensive driver management functionality including:
- WebDriver initialization and lifecycle management
- Automated driver download and installation
- Platform-specific driver handling
- Version management for Chrome and Firefox drivers
"""

from .web_driver_manager import WebDriverManager
from .driver_installer import DriverInstaller
from .chrome_driver import ChromeDriver
from .firefox_driver import FirefoxDriver

__all__ = [
    'WebDriverManager',
    'DriverInstaller',
    'ChromeDriver',
    'FirefoxDriver'
]

# For backward compatibility
DriverManager = WebDriverManager 