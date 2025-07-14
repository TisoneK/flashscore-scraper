#!/usr/bin/env python3
"""Test script to verify cross-platform WebDriver configuration."""

import sys
import os
import platform
import pytest
from unittest.mock import patch, Mock
sys.path.append('.')

from src.driver_manager import WebDriverManager
from src.config import CONFIG


def test_driver_initialization():
    """Test the WebDriver initialization using pytest."""
    driver_manager = WebDriverManager()
    driver_manager.initialize()
    
    # Get driver info
    driver = driver_manager.get_driver()
    assert driver is not None, "Driver should not be None"
    assert hasattr(driver, 'quit'), "Driver should have quit method"
    
    driver_manager.close()
    assert not driver_manager.is_active(), "Driver should be inactive after closing"


def test_os_detection():
    """Test that OS detection works correctly."""
    system = platform.system().lower()
    assert system in ['windows', 'linux', 'darwin'], f"Unexpected OS: {system}"


def test_chrome_driver_selection():
    """Test Chrome driver selection logic."""
    # Test with Chrome (default)
    CONFIG.browser.browser_name = "chrome"
    driver_manager = WebDriverManager()
    driver_manager.initialize()
    
    driver = driver_manager.get_driver()
    assert driver is not None, "Chrome driver should be initialized"
    
    # Check if it's a Chrome driver
    assert "chrome" in str(type(driver)).lower(), "Should be Chrome WebDriver"
    
    driver_manager.close()


def test_firefox_driver_selection():
    """Test Firefox driver selection logic."""
    # Test with Firefox
    CONFIG.browser.browser_name = "firefox"
    driver_manager = WebDriverManager()
    driver_manager.initialize()
    
    driver = driver_manager.get_driver()
    assert driver is not None, "Firefox driver should be initialized"
    
    # Check if it's a Firefox driver
    assert "firefox" in str(type(driver)).lower(), "Should be Firefox WebDriver"
    
    driver_manager.close()


def test_driver_manager_lifecycle():
    """Test the complete lifecycle of the driver manager."""
    driver_manager = WebDriverManager()
    
    # Initially should not be active
    assert not driver_manager.is_active(), "Driver should not be active initially"
    
    # Initialize
    driver_manager.initialize()
    assert driver_manager.is_active(), "Driver should be active after initialization"
    
    # Get driver
    driver = driver_manager.get_driver()
    assert driver is not None, "Driver should be available"
    
    # Close
    driver_manager.close()
    assert not driver_manager.is_active(), "Driver should not be active after closing"


if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Testing cross-platform WebDriver configuration...")
    logger.info(f"Current OS: {platform.system()}")
    logger.info(f"Current browser config: {CONFIG.browser.browser_name}")
    
    # Run basic initialization test
    test_driver_initialization()
    logger.info("✓ Basic driver initialization test passed")
    
    # Run OS detection test
    test_os_detection()
    logger.info("✓ OS detection test passed")
    
    # Run browser-specific tests
    test_chrome_driver_selection()
    logger.info("✓ Chrome driver selection test passed")
    
    test_firefox_driver_selection()
    logger.info("✓ Firefox driver selection test passed")
    
    logger.info("✓ All tests passed!") 