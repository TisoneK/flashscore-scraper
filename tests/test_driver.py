#!/usr/bin/env python3
"""Test script to verify cross-platform WebDriver configuration."""

import sys
import os
import platform
import pytest
from unittest.mock import patch, Mock, MagicMock
sys.path.append('.')

from src.driver_manager import WebDriverManager
from src.utils.config_loader import CONFIG


def test_os_detection():
    """Test that OS detection works correctly."""
    system = platform.system().lower()
    assert system in ['windows', 'linux', 'darwin'], f"Unexpected OS: {system}"


def test_driver_manager_creation():
    """Test that WebDriverManager can be instantiated."""
    driver_manager = WebDriverManager()
    assert driver_manager is not None
    assert not driver_manager.is_active(), "Driver should not be active initially"


def test_driver_manager_close_without_init():
    """Test that closing an uninitialized driver manager doesn't crash."""
    driver_manager = WebDriverManager()
    driver_manager.close()
    assert not driver_manager.is_active()


def test_config_has_browser_section():
    """Test that CONFIG has a browser section with expected keys."""
    assert 'browser' in CONFIG
    assert 'browser_name' in CONFIG['browser']
    assert 'headless' in CONFIG['browser']


def test_config_default_browser():
    """Test that default browser is chrome."""
    assert CONFIG['browser']['browser_name'] == 'chrome'


if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Testing WebDriver configuration...")
    logger.info(f"Current OS: {platform.system()}")
    logger.info(f"Current browser config: {CONFIG['browser']['browser_name']}")
    
    test_os_detection()
    logger.info("OK: OS detection test passed")
    
    test_driver_manager_creation()
    logger.info("OK: Driver manager creation test passed")
    
    test_driver_manager_close_without_init()
    logger.info("OK: Close without init test passed")
    
    test_config_has_browser_section()
    logger.info("OK: Config browser section test passed")
    
    test_config_default_browser()
    logger.info("OK: Default browser test passed")
    
    logger.info("All tests passed!")
