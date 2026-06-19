"""Tests for exit flow functionality to ensure clean shutdown without driver creation."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cli.cli_manager import CLIManager
from scraper import FlashscoreScraper


class TestExitFlow(unittest.TestCase):
    """Test cases for exit flow functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cli_manager = CLIManager()
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self.cli_manager, 'close'):
            self.cli_manager.close()
    
    def test_exit_without_scraper_does_not_create_driver(self):
        """Test that exiting without an active scraper doesn't create a driver."""
        # Ensure no scraper is active
        self.cli_manager.scraper = None
        self.cli_manager._is_running = False
        
        # Mock the WebDriverManager to track if get_driver is called
        with patch('scraper.WebDriverManager') as mock_webdriver_manager:
            mock_manager_instance = Mock()
            mock_webdriver_manager.return_value = mock_manager_instance
            
            # Simulate exit
            self.cli_manager._is_running = False
            self.cli_manager._is_closing = True
            
            # Call _stop_scraper
            self.cli_manager._stop_scraper()
            
            # Verify no driver was created
            mock_manager_instance.get_driver.assert_not_called()
    
    def test_exit_with_inactive_scraper_does_not_create_driver(self):
        """Test that exiting with an inactive scraper doesn't create a driver."""
        # Create a mock scraper without active driver
        mock_scraper = Mock()
        mock_scraper.has_active_driver.return_value = False
        self.cli_manager.scraper = mock_scraper
        
        # Mock the WebDriverManager
        with patch('scraper.WebDriverManager') as mock_webdriver_manager:
            mock_manager_instance = Mock()
            mock_webdriver_manager.return_value = mock_manager_instance
            
            # Simulate exit
            self.cli_manager._is_running = False
            self.cli_manager._is_closing = True
            
            # Call _stop_scraper
            self.cli_manager._stop_scraper()
            
            # Verify no driver was created
            mock_manager_instance.get_driver.assert_not_called()
    
    def test_has_active_driver_method(self):
        """Test the has_active_driver method works correctly."""
        scraper = FlashscoreScraper()
        
        # Initially no driver
        self.assertFalse(scraper.has_active_driver())
        
        # Set a mock driver
        scraper._driver = Mock()
        self.assertTrue(scraper.has_active_driver())
        
        # Clear driver
        scraper._driver = None
        self.assertFalse(scraper.has_active_driver())
    
    def test_driver_property_respects_closing_flag(self):
        """Test that driver property returns None when closing flag is set."""
        scraper = FlashscoreScraper()
        scraper._is_closing = True
        
        # Mock the driver manager
        with patch.object(scraper, '_driver_manager') as mock_manager:
            mock_manager.get_driver.return_value = Mock()
            
            # Driver property should return None when closing
            driver = scraper.driver
            self.assertIsNone(driver)
            
            # Verify get_driver was not called
            mock_manager.get_driver.assert_not_called()
    
    def test_close_method_fast_path(self):
        """Test that close method uses fast path without network calls."""
        scraper = FlashscoreScraper()
        
        # Mock the driver
        mock_driver = Mock()
        scraper._driver = mock_driver
        
        # Mock the driver manager
        mock_manager = Mock()
        scraper._driver_manager = mock_manager
        
        # Call close
        scraper.close()
        
        # Verify driver.quit() was called once
        mock_driver.quit.assert_called_once()
        
        # Verify driver manager close was called with force=True
        mock_manager.close.assert_called_once_with(force=True)
        
        # Verify driver was cleared
        self.assertIsNone(scraper._driver)
    
    def test_webdriver_manager_respects_closing_flag(self):
        """Test that WebDriverManager doesn't create drivers when closing."""
        from driver_manager.web_driver_manager import WebDriverManager
        
        manager = WebDriverManager()
        manager._is_closing = True
        
        # get_driver should return None when closing
        driver = manager.get_driver()
        self.assertIsNone(driver)
    
    def test_json_storage_empty_list_handling(self):
        """Test that JSONStorage handles empty lists without IndexError."""
        from storage.json_storage import JSONStorage
        
        storage = JSONStorage()
        
        # This should not raise an IndexError
        result = storage.save_matches([])
        self.assertTrue(result)
    
    def test_config_dict_access(self):
        """Test that CONFIG is accessed as a dictionary."""
        from utils.config_loader import CONFIG
        
        # These should work without AttributeError
        browser_name = CONFIG.get('browser', {}).get('browser_name', 'chrome')
        self.assertIsInstance(browser_name, str)
        
        # Test nested access
        timeout_config = CONFIG.get('timeout', {})
        self.assertIsInstance(timeout_config, dict)


if __name__ == '__main__':
    unittest.main()
