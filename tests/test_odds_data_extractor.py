#!/usr/bin/env python3
"""
Tests for OddsDataExtractor class
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.extractor.odds_data_extractor import OddsDataExtractor


class MockOddsLoader:
    """Mock loader for testing purposes"""
    def __init__(self, elements=None):
        self.elements = elements or MockOddsElements()
        self.driver = None


class MockOddsElements:
    """Mock elements for testing purposes"""
    def __init__(self, totals=None):
        if totals is None:
            # Default test data
            totals = [
                {'alternative': MockElement('153.0'), 'over': MockElement('1.90'), 'under': MockElement('1.90')},
                {'alternative': MockElement('153.5'), 'over': MockElement('1.85'), 'under': MockElement('1.95')},
                {'alternative': MockElement('154.0'), 'over': MockElement('1.80'), 'under': MockElement('2.00')},
                {'alternative': MockElement('154.5'), 'over': MockElement('1.75'), 'under': MockElement('2.05')},
                {'alternative': MockElement('155.0'), 'over': MockElement('1.70'), 'under': MockElement('2.10')},
            ]
        self.all_totals = totals


class MockElement:
    """Mock element with text attribute"""
    def __init__(self, text):
        self.text = text


class TestOddsDataExtractor(unittest.TestCase):
    """Test cases for OddsDataExtractor class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_loader = MockOddsLoader()
        self.extractor = OddsDataExtractor(self.mock_loader)

    def test_has_half_point_valid_values(self):
        """Test has_half_point method with valid values"""
        # Test values with .5
        self.assertTrue(self.extractor.has_half_point('153.5'))
        self.assertTrue(self.extractor.has_half_point('154.5'))
        self.assertTrue(self.extractor.has_half_point('155.5'))
        
        # Test values without .5
        self.assertFalse(self.extractor.has_half_point('153.0'))
        self.assertFalse(self.extractor.has_half_point('154.0'))
        self.assertFalse(self.extractor.has_half_point('155.0'))
        
        # Test edge cases
        self.assertFalse(self.extractor.has_half_point(None))
        self.assertFalse(self.extractor.has_half_point('invalid'))
        self.assertFalse(self.extractor.has_half_point(''))

    def test_get_selected_alternative_with_half_points(self):
        """Test get_selected_alternative when .5 alternatives are available"""
        # Should select 153.5 because it has .5 and over odds closest to 1.85
        selected = self.extractor.get_selected_alternative()
        
        self.assertIsNotNone(selected)
        self.assertEqual(selected['alternative'].text, '153.5')
        self.assertEqual(selected['over'].text, '1.85')
        self.assertTrue(self.extractor.has_half_point(selected['alternative'].text))

    def test_get_selected_alternative_no_half_points(self):
        """Test get_selected_alternative when no .5 alternatives are available"""
        # Create data without .5 alternatives
        totals = [
            {'alternative': MockElement('153.0'), 'over': MockElement('1.85'), 'under': MockElement('1.95')},
            {'alternative': MockElement('154.0'), 'over': MockElement('1.80'), 'under': MockElement('2.00')},
            {'alternative': MockElement('155.0'), 'over': MockElement('1.75'), 'under': MockElement('2.05')},
        ]
        self.mock_loader.elements = MockOddsElements(totals)
        
        selected = self.extractor.get_selected_alternative()
        
        self.assertIsNotNone(selected)
        # Should select 153.0 because it has over odds closest to 1.85
        self.assertEqual(selected['alternative'].text, '153.0')
        self.assertEqual(selected['over'].text, '1.85')

    def test_get_selected_alternative_low_odds(self):
        """Test get_selected_alternative with only low odds (below 1.85)"""
        totals = [
            {'alternative': MockElement('153.0'), 'over': MockElement('1.60'), 'under': MockElement('2.20')},
            {'alternative': MockElement('153.5'), 'over': MockElement('1.65'), 'under': MockElement('2.15')},
            {'alternative': MockElement('154.0'), 'over': MockElement('1.70'), 'under': MockElement('2.10')},
        ]
        self.mock_loader.elements = MockOddsElements(totals)
        
        selected = self.extractor.get_selected_alternative()
        
        self.assertIsNotNone(selected)
        # Should select 153.5 because it has .5 and closest to 1.85
        self.assertEqual(selected['alternative'].text, '153.5')
        self.assertEqual(selected['over'].text, '1.65')

    def test_get_selected_alternative_with_index(self):
        """Test get_selected_alternative with specific index"""
        selected = self.extractor.get_selected_alternative(index=2)
        
        self.assertIsNotNone(selected)
        self.assertEqual(selected['alternative'].text, '154.0')
        self.assertEqual(selected['over'].text, '1.80')

    def test_get_selected_alternative_invalid_index(self):
        """Test get_selected_alternative with invalid index"""
        selected = self.extractor.get_selected_alternative(index=999)
        self.assertIsNone(selected)

    def test_get_best_alternative_with_half_and_target(self):
        """Test get_best_alternative when .5 alternatives with over >= 1.85 are available"""
        selected = self.extractor.get_best_alternative()
        
        self.assertIsNotNone(selected)
        # Should select 153.5 because it has .5 and over >= 1.85
        self.assertEqual(selected['alternative'].text, '153.5')
        self.assertEqual(selected['over'].text, '1.85')
        self.assertTrue(self.extractor.has_half_point(selected['alternative'].text))

    def test_get_best_alternative_only_target(self):
        """Test get_best_alternative when only alternatives with over >= 1.85 are available (no .5)"""
        totals = [
            {'alternative': MockElement('153.0'), 'over': MockElement('1.85'), 'under': MockElement('1.95')},
            {'alternative': MockElement('154.0'), 'over': MockElement('1.90'), 'under': MockElement('2.00')},
            {'alternative': MockElement('155.0'), 'over': MockElement('1.75'), 'under': MockElement('2.05')},
        ]
        self.mock_loader.elements = MockOddsElements(totals)
        
        selected = self.extractor.get_best_alternative()
        
        self.assertIsNotNone(selected)
        # Should select 153.0 because it has over >= 1.85 (first one)
        self.assertEqual(selected['alternative'].text, '153.0')
        self.assertEqual(selected['over'].text, '1.85')

    def test_get_best_alternative_low_odds_fallback(self):
        """Test get_best_alternative with only low odds, should fall back to closest overall"""
        totals = [
            {'alternative': MockElement('153.0'), 'over': MockElement('1.60'), 'under': MockElement('2.20')},
            {'alternative': MockElement('153.5'), 'over': MockElement('1.65'), 'under': MockElement('2.15')},
            {'alternative': MockElement('154.0'), 'over': MockElement('1.70'), 'under': MockElement('2.10')},
        ]
        self.mock_loader.elements = MockOddsElements(totals)
        
        selected = self.extractor.get_best_alternative()
        
        self.assertIsNotNone(selected)
        # Should select 154.0 because it has over odds closest to 1.85
        self.assertEqual(selected['alternative'].text, '154.0')
        self.assertEqual(selected['over'].text, '1.70')

    def test_get_all_totals(self):
        """Test get_all_totals method"""
        totals = self.extractor.get_all_totals()
        
        self.assertEqual(len(totals), 5)
        self.assertEqual(totals[0]['alternative'].text, '153.0')
        self.assertEqual(totals[0]['over'].text, '1.90')
        self.assertEqual(totals[0]['under'].text, '1.90')

    def test_get_total_alternatives(self):
        """Test get_total_alternatives method"""
        count = self.extractor.get_total_alternatives()
        self.assertEqual(count, 5)

    def test_best_alternative_target_property(self):
        """Test best_alternative_target property"""
        # Test default value
        self.assertEqual(self.extractor.best_alternative_target, 1.85)
        
        # Test setting new value
        self.extractor.best_alternative_target = 1.90
        self.assertEqual(self.extractor.best_alternative_target, 1.90)

    def test_extract_home_away_odds(self):
        """Test extract_home_away_odds method"""
        # Mock the elements with home/away odds
        mock_elements = Mock()
        mock_elements.home_odds = MockElement('1.85')
        mock_elements.away_odds = MockElement('2.10')
        
        result = self.extractor.extract_home_away_odds(mock_elements)
        
        self.assertEqual(result['home_odds'], '1.85')
        self.assertEqual(result['away_odds'], '2.10')
        self.assertEqual(self.extractor.home_odds, '1.85')
        self.assertEqual(self.extractor.away_odds, '2.10')

    def test_extract_over_under_odds(self):
        """Test extract_over_under_odds method"""
        # Mock the elements with over/under odds
        mock_elements = Mock()
        mock_elements.match_total = MockElement('153.5')
        mock_elements.over_odds = MockElement('1.85')
        mock_elements.under_odds = MockElement('1.95')
        
        result = self.extractor.extract_over_under_odds(mock_elements)
        
        self.assertEqual(result['match_total'], '153.5')
        self.assertEqual(result['over_odds'], '1.85')
        self.assertEqual(result['under_odds'], '1.95')
        self.assertEqual(self.extractor.match_total, '153.5')
        self.assertEqual(self.extractor.over_odds, '1.85')
        self.assertEqual(self.extractor.under_odds, '1.95')


if __name__ == '__main__':
    unittest.main() 