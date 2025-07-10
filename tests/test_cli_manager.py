import unittest
from unittest.mock import patch, MagicMock
from src.cli.cli_manager import CLIManager

class TestCLIManager(unittest.TestCase):
    @patch('os.system')
    def test_clear_terminal(self, mock_system):
        cli = CLIManager()
        cli.clear_terminal()
        mock_system.assert_called_once()
        self.assertIn(mock_system.call_args[0][0], ['cls', 'clear'])

    def test_display_header(self):
        cli = CLIManager()
        cli.colored_display = MagicMock()
        cli.display_header()
        cli.colored_display.show_welcome.assert_called_once()

    def test_handle_scraping_selection(self):
        """Test the new day selection functionality."""
        cli = CLIManager()
        cli.prompts = MagicMock()
        cli.display = MagicMock()
        cli.scraper = MagicMock()
        cli.progress = MagicMock()
        cli.progress.scraping_progress.return_value.__enter__.return_value = MagicMock()
        cli.progress.scraping_progress.return_value.__exit__.return_value = None
        
        # Mock the prompts
        cli.prompts.ask_scraping_day.return_value = "Tomorrow"
        
        # Mock user settings
        cli.user_settings = {'default_day': 'Today'}
        
        # Mock the scraper
        with patch('src.cli.cli_manager.FlashscoreScraper') as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper_class.return_value = mock_scraper
            
            # Test with different day selection
            cli.handle_scraping_selection()
            
            # Verify the scraper was called with the correct day
            mock_scraper.scrape.assert_called_once()
            call_args = mock_scraper.scrape.call_args
            self.assertEqual(call_args[1]['day'], "Tomorrow")
            
            # Verify settings were updated
            self.assertEqual(cli.user_settings['default_day'], "Tomorrow")

    def test_handle_scraping_selection_same_day(self):
        """Test day selection when user chooses the same day as default."""
        cli = CLIManager()
        cli.prompts = MagicMock()
        cli.display = MagicMock()
        cli.scraper = MagicMock()
        cli.progress = MagicMock()
        cli.progress.scraping_progress.return_value.__enter__.return_value = MagicMock()
        cli.progress.scraping_progress.return_value.__exit__.return_value = None
        
        # Mock the prompts to return the same day as default
        cli.prompts.ask_scraping_day.return_value = "Today"
        
        # Mock user settings
        cli.user_settings = {'default_day': 'Today'}
        
        # Mock the scraper
        with patch('src.cli.cli_manager.FlashscoreScraper') as mock_scraper_class:
            mock_scraper = MagicMock()
            mock_scraper_class.return_value = mock_scraper
            
            # Test with same day selection
            cli.handle_scraping_selection()
            
            # Verify the scraper was called with the correct day
            mock_scraper.scrape.assert_called_once()
            call_args = mock_scraper.scrape.call_args
            self.assertEqual(call_args[1]['day'], "Today")
            
            # Verify settings were not changed (same day)
            self.assertEqual(cli.user_settings['default_day'], "Today")

    def test_load_user_settings(self):
        """Test loading user settings with default day."""
        cli = CLIManager()
        # Test that default_day is loaded correctly
        self.assertIn('default_day', cli.user_settings)
        # The default day can be either Today or Tomorrow depending on user settings
        self.assertIn(cli.user_settings['default_day'], ["Today", "Tomorrow"])

if __name__ == '__main__':
    unittest.main() 