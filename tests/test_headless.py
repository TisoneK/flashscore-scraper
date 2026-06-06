#!/usr/bin/env python3
"""Test headless mode configuration."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.config_loader import CONFIG
from src.driver_manager.web_driver_manager import WebDriverManager


def test_headless_config_exists():
    """Test that headless configuration is present in CONFIG."""
    assert 'browser' in CONFIG, "CONFIG should have 'browser' section"
    assert 'headless' in CONFIG['browser'], "CONFIG['browser'] should have 'headless' key"


def test_headless_default_is_true():
    """Test that headless mode defaults to True."""
    assert CONFIG['browser']['headless'] is True, "Headless should default to True"


def test_webdriver_manager_instantiation():
    """Test that WebDriverManager can be instantiated without a real browser."""
    driver_manager = WebDriverManager()
    assert driver_manager is not None
    assert not driver_manager.is_active(), "Driver should not be active without initialization"


if __name__ == "__main__":
    test_headless_config_exists()
    print("OK: Headless config exists")
    
    test_headless_default_is_true()
    print("OK: Headless default is True")
    
    test_webdriver_manager_instantiation()
    print("OK: WebDriverManager instantiation")
    
    print("All headless tests passed!")
