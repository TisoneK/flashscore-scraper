#!/usr/bin/env python3
"""
Tests for FlashscoreScraper class
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scraper import FlashscoreScraper
from src.models import MatchModel, OddsModel, H2HMatchModel


class TestFlashscoreScraper(unittest.TestCase):
    """Test cases for FlashscoreScraper class"""

    def setUp(self):
        """Set up test fixtures"""
        self.scraper = FlashscoreScraper()

    @patch('src.scraper.WebDriverManager')
    def test_initialize(self, mock_driver_manager):
        """Test scraper initialization"""
        mock_manager_instance = Mock()
        mock_driver_manager.return_value = mock_manager_instance
        mock_driver = Mock()
        mock_manager_instance.get_driver.return_value = mock_driver
        
        self.scraper.initialize()
        
        mock_manager_instance.initialize.assert_called_once()
        mock_manager_instance.get_driver.assert_called_once()
        self.assertEqual(self.scraper.driver, mock_driver)

    @patch('src.scraper.MatchDataLoader')
    @patch('src.scraper.OddsDataLoader')
    def test_load_initial_data(self, mock_odds_loader, mock_match_loader):
        """Test loading initial data"""
        # Mock the driver and selenium_utils
        self.scraper.driver = Mock()
        self.scraper.selenium_utils = Mock()
        
        # Mock the loaders
        mock_match_instance = Mock()
        mock_match_loader.return_value = mock_match_instance
        mock_match_instance.get_today_match_ids.return_value = ['match1', 'match2', 'match3']
        
        mock_odds_instance = Mock()
        mock_odds_loader.return_value = mock_odds_instance
        
        result = self.scraper.load_initial_data()
        
        self.assertEqual(result, ['match1', 'match2', 'match3'])
        mock_match_instance.load_main_page.assert_called_once()
        mock_match_instance.get_today_match_ids.assert_called_once()

    @patch('src.scraper.MatchDataLoader')
    @patch('src.scraper.OddsDataLoader')
    def test_load_initial_data_no_today_matches(self, mock_odds_loader, mock_match_loader):
        """Test loading initial data when no today matches are available"""
        # Mock the driver and selenium_utils
        self.scraper.driver = Mock()
        self.scraper.selenium_utils = Mock()
        
        # Mock the loaders
        mock_match_instance = Mock()
        mock_match_loader.return_value = mock_match_instance
        mock_match_instance.get_today_match_ids.return_value = []
        mock_match_instance.get_tomorrow_match_ids.return_value = ['tomorrow1', 'tomorrow2']
        
        mock_odds_instance = Mock()
        mock_odds_loader.return_value = mock_odds_instance
        
        result = self.scraper.load_initial_data()
        
        self.assertEqual(result, ['tomorrow1', 'tomorrow2'])
        mock_match_instance.get_tomorrow_match_ids.assert_called_once()

    def test_validate_odds_data_complete(self):
        """Test odds validation with complete data"""
        odds = OddsModel(match_id='test')
        odds.home_odds = 1.85
        odds.away_odds = 2.10
        odds.match_total = 153.5
        odds.over_odds = 1.85
        odds.under_odds = 1.95
        
        is_incomplete, missing_fields = self.scraper.validate_odds_data(odds)
        
        self.assertFalse(is_incomplete)
        self.assertEqual(len(missing_fields), 0)

    def test_validate_odds_data_incomplete(self):
        """Test odds validation with incomplete data"""
        odds = OddsModel(match_id='test')
        odds.home_odds = 1.85
        odds.away_odds = None  # Missing
        odds.match_total = 153.5
        odds.over_odds = None  # Missing
        odds.under_odds = 1.95
        
        is_incomplete, missing_fields = self.scraper.validate_odds_data(odds)
        
        self.assertTrue(is_incomplete)
        self.assertIn('away_odds', missing_fields)
        self.assertIn('over_odds', missing_fields)
        self.assertEqual(len(missing_fields), 2)

    def test_compose_skip_reason(self):
        """Test composing skip reason"""
        # Test with odds incomplete
        odds_incomplete = True
        missing_odds_fields = ['home_odds', 'away_odds']
        h2h_count = 8
        
        reason = self.scraper.compose_skip_reason(odds_incomplete, missing_odds_fields, h2h_count)
        
        self.assertIn('missing or invalid odds fields: home_odds, away_odds', reason)
        self.assertNotIn('insufficient H2H matches', reason)

    def test_compose_skip_reason_insufficient_h2h(self):
        """Test composing skip reason with insufficient H2H matches"""
        # Test with insufficient H2H
        odds_incomplete = False
        missing_odds_fields = []
        h2h_count = 3  # Less than required
        
        reason = self.scraper.compose_skip_reason(odds_incomplete, missing_odds_fields, h2h_count)
        
        self.assertIn('insufficient H2H matches (3 found, 6 required)', reason)
        self.assertNotIn('missing or invalid odds fields', reason)

    def test_compose_skip_reason_both_issues(self):
        """Test composing skip reason with both odds and H2H issues"""
        odds_incomplete = True
        missing_odds_fields = ['home_odds']
        h2h_count = 2
        
        reason = self.scraper.compose_skip_reason(odds_incomplete, missing_odds_fields, h2h_count)
        
        self.assertIn('missing or invalid odds fields: home_odds', reason)
        self.assertIn('insufficient H2H matches (2 found, 6 required)', reason)

    def test_compose_skip_reason_no_issues(self):
        """Test composing skip reason with no issues"""
        odds_incomplete = False
        missing_odds_fields = []
        h2h_count = 8
        
        reason = self.scraper.compose_skip_reason(odds_incomplete, missing_odds_fields, h2h_count)
        
        self.assertEqual(reason, "")

    @patch('src.scraper.MatchDataExtractor')
    def test_extract_match_data(self, mock_extractor_class):
        """Test extracting match data"""
        mock_extractor_instance = Mock()
        mock_extractor_class.return_value = mock_extractor_instance
        mock_match_data = Mock()
        mock_extractor_instance.extract_match_data.return_value = mock_match_data
        
        self.scraper.match_loader = Mock()
        
        result = self.scraper.extract_match_data()
        
        self.assertEqual(result, mock_match_data)
        mock_extractor_instance.extract_match_data.assert_called_once()

    @patch('src.scraper.OddsDataExtractor')
    def test_extract_home_away_odds(self, mock_extractor_class):
        """Test extracting home/away odds"""
        mock_extractor_instance = Mock()
        mock_extractor_class.return_value = mock_extractor_instance
        mock_extractor_instance.home_odds = '1.85'
        mock_extractor_instance.away_odds = '2.10'
        
        self.scraper.home_away_loader = Mock()
        
        home_odds, away_odds = self.scraper.extract_home_away_odds()
        
        self.assertEqual(home_odds, 1.85)
        self.assertEqual(away_odds, 2.10)
        mock_extractor_instance.extract_home_away_odds.assert_called_once()

    @patch('src.scraper.OddsDataExtractor')
    def test_extract_home_away_odds_none_values(self, mock_extractor_class):
        """Test extracting home/away odds with None values"""
        mock_extractor_instance = Mock()
        mock_extractor_class.return_value = mock_extractor_instance
        mock_extractor_instance.home_odds = None
        mock_extractor_instance.away_odds = None
        
        self.scraper.home_away_loader = Mock()
        
        home_odds, away_odds = self.scraper.extract_home_away_odds()
        
        self.assertIsNone(home_odds)
        self.assertIsNone(away_odds)

    @patch('src.scraper.OddsDataExtractor')
    def test_extract_over_under_odds(self, mock_extractor_class):
        """Test extracting over/under odds"""
        mock_extractor_instance = Mock()
        mock_extractor_class.return_value = mock_extractor_instance
        
        # Mock the selected alternative
        selected_alternative = {
            'alternative': '153.5',
            'over': '1.85',
            'under': '1.95'
        }
        mock_extractor_instance.get_selected_alternative.return_value = selected_alternative
        
        self.scraper.over_under_loader = Mock()
        
        match_total, over_odds, under_odds = self.scraper.extract_over_under_odds()
        
        self.assertEqual(match_total, 153.5)
        self.assertEqual(over_odds, 1.85)
        self.assertEqual(under_odds, 1.95)
        mock_extractor_instance.extract_over_under_odds.assert_called_once()

    @patch('src.scraper.OddsDataExtractor')
    def test_extract_over_under_odds_no_selection(self, mock_extractor_class):
        """Test extracting over/under odds when no alternative is selected"""
        mock_extractor_instance = Mock()
        mock_extractor_class.return_value = mock_extractor_instance
        mock_extractor_instance.get_selected_alternative.return_value = None
        
        self.scraper.over_under_loader = Mock()
        
        match_total, over_odds, under_odds = self.scraper.extract_over_under_odds()
        
        self.assertIsNone(match_total)
        self.assertIsNone(over_odds)
        self.assertIsNone(under_odds)

    @patch('src.scraper.H2HDataExtractor')
    def test_extract_h2h_matches(self, mock_extractor_class):
        """Test extracting H2H matches"""
        mock_extractor_instance = Mock()
        mock_extractor_class.return_value = mock_extractor_instance
        
        # Mock H2H data
        mock_h2h_data = [Mock(), Mock(), Mock()]  # 3 matches
        mock_extractor_instance.extract_h2h_data.return_value = mock_h2h_data
        
        # Mock individual match data
        mock_extractor_instance.get_date.side_effect = ['2023-01-01', '2023-01-02', '2023-01-03']
        mock_extractor_instance.get_home_team.side_effect = ['Team A', 'Team B', 'Team C']
        mock_extractor_instance.get_away_team.side_effect = ['Team B', 'Team A', 'Team D']
        mock_extractor_instance.get_home_score.side_effect = [85, 90, 95]
        mock_extractor_instance.get_away_score.side_effect = [80, 85, 88]
        mock_extractor_instance.get_competition.side_effect = ['League1', 'League1', 'League2']
        
        self.scraper.h2h_loader = Mock()
        self.scraper.h2h_loader.get_h2h_count.return_value = 3
        
        h2h_matches, h2h_count = self.scraper.extract_h2h_matches('test_match_id')
        
        self.assertEqual(len(h2h_matches), 3)
        self.assertEqual(h2h_count, 3)
        
        # Check first match
        first_match = h2h_matches[0]
        self.assertEqual(first_match.match_id, 'test_match_id')
        self.assertEqual(first_match.date, '2023-01-01')
        self.assertEqual(first_match.home_team, 'Team A')
        self.assertEqual(first_match.away_team, 'Team B')
        self.assertEqual(first_match.home_score, 85)
        self.assertEqual(first_match.away_score, 80)
        self.assertEqual(first_match.competition, 'League1')

    def test_log_match_info(self):
        """Test logging match information"""
        # Create a test match
        odds = OddsModel(match_id='test')
        odds.home_odds = 1.85
        odds.away_odds = 2.10
        odds.match_total = 153.5
        odds.over_odds = 1.85
        odds.under_odds = 1.95
        
        h2h_match = H2HMatchModel(
            match_id='test',
            date='2023-01-01',
            home_team='Team A',
            away_team='Team B',
            home_score=85,
            away_score=80,
            competition='League1'
        )
        
        match = MatchModel(
            match_id='test',
            country='Test Country',
            league='Test League',
            home_team='Team A',
            away_team='Team B',
            date='2023-01-01',
            time='20:00',
            odds=odds,
            h2h_matches=[h2h_match],
            status='complete',
            skip_reason=''
        )
        
        # This should not raise any exceptions
        self.scraper.log_match_info(match)


if __name__ == '__main__':
    unittest.main() 