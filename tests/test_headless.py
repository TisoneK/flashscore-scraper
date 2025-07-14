#!/usr/bin/env python3
"""Test headless mode configuration."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import CONFIG
from src.driver_manager.web_driver_manager import WebDriverManager
import time

def test_headless_mode():
    """Test if headless mode is properly configured."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("🔍 Testing headless mode configuration...")
    
    # Check current config
    logger.info(f"📋 Current headless setting: {CONFIG.browser.headless}")
    
    # Initialize driver
    driver_manager = WebDriverManager()
    
    try:
        logger.info("🚀 Initializing WebDriver...")
        driver_manager.initialize()
        
        driver = driver_manager.get_driver()
        if driver:
            logger.info("✅ WebDriver initialized successfully")
            
            # Check if headless mode is active
            capabilities = driver.capabilities
            logger.info(f"📊 Browser capabilities: {capabilities}")
            
            # Navigate to a simple page to test
            logger.info("🌐 Navigating to test page...")
            driver.get("https://www.google.com")
            time.sleep(2)
            
            title = driver.title
            logger.info(f"📄 Page title: {title}")
            
            logger.info("✅ Headless mode test completed successfully")
            
    except Exception as e:
        logger.error(f"❌ Error during headless test: {e}")
    finally:
        if driver_manager.driver:
            driver_manager.close()
            logger.info("🔒 WebDriver closed")

if __name__ == "__main__":
    test_headless_mode() 