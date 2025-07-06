#!/usr/bin/env python3
"""
Tests for elements_model.py
"""

import sys
import os
import unittest
from unittest.mock import Mock

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.elements_model import MatchElements, OddsElements, H2HElements


class TestMatchElements(unittest.TestCase):
    """Test cases for MatchElements dataclass"""

    def test_match_elements_default_creation(self):
        """Test creating MatchElements with default values"""
        elements = MatchElements()
        
        self.assertIsNone(elements.country)
        self.assertIsNone(elements.league)
        self.assertIsNone(elements.home_team)
        self.assertIsNone(elements.away_team)
        self.assertIsNone(elements.date)
        self.assertIsNone(elements.time)
        self.assertIsNone(elements.match_id)

    def test_match_elements_with_values(self):
        """Test creating MatchElements with specific values"""
        mock_country = Mock()
        mock_league = Mock()
        mock_home_team = Mock()
        mock_away_team = Mock()
        mock_date = Mock()
        mock_time = Mock()
        mock_match_id = Mock()
        
        elements = MatchElements(
            country=mock_country,
            league=mock_league,
            home_team=mock_home_team,
            away_team=mock_away_team,
            date=mock_date,
            time=mock_time,
            match_id=mock_match_id
        )
        
        self.assertEqual(elements.country, mock_country)
        self.assertEqual(elements.league, mock_league)
        self.assertEqual(elements.home_team, mock_home_team)
        self.assertEqual(elements.away_team, mock_away_team)
        self.assertEqual(elements.date, mock_date)
        self.assertEqual(elements.time, mock_time)
        self.assertEqual(elements.match_id, mock_match_id)

    def test_match_elements_partial_values(self):
        """Test creating MatchElements with partial values"""
        mock_home_team = Mock()
        mock_away_team = Mock()
        
        elements = MatchElements(
            home_team=mock_home_team,
            away_team=mock_away_team
        )
        
        self.assertIsNone(elements.country)
        self.assertIsNone(elements.league)
        self.assertEqual(elements.home_team, mock_home_team)
        self.assertEqual(elements.away_team, mock_away_team)
        self.assertIsNone(elements.date)
        self.assertIsNone(elements.time)
        self.assertIsNone(elements.match_id)


class TestOddsElements(unittest.TestCase):
    """Test cases for OddsElements dataclass"""

    def test_odds_elements_default_creation(self):
        """Test creating OddsElements with default values"""
        elements = OddsElements()
        
        self.assertIsNone(elements.home_odds)
        self.assertIsNone(elements.away_odds)
        self.assertIsNone(elements.match_total)
        self.assertIsNone(elements.over_odds)
        self.assertIsNone(elements.under_odds)
        self.assertEqual(elements.all_totals, [])

    def test_odds_elements_with_values(self):
        """Test creating OddsElements with specific values"""
        mock_home_odds = Mock()
        mock_away_odds = Mock()
        mock_match_total = Mock()
        mock_over_odds = Mock()
        mock_under_odds = Mock()
        mock_all_totals = [Mock(), Mock()]
        
        elements = OddsElements(
            home_odds=mock_home_odds,
            away_odds=mock_away_odds,
            match_total=mock_match_total,
            over_odds=mock_over_odds,
            under_odds=mock_under_odds,
            all_totals=mock_all_totals
        )
        
        self.assertEqual(elements.home_odds, mock_home_odds)
        self.assertEqual(elements.away_odds, mock_away_odds)
        self.assertEqual(elements.match_total, mock_match_total)
        self.assertEqual(elements.over_odds, mock_over_odds)
        self.assertEqual(elements.under_odds, mock_under_odds)
        self.assertEqual(elements.all_totals, mock_all_totals)

    def test_odds_elements_empty_all_totals(self):
        """Test creating OddsElements with empty all_totals"""
        elements = OddsElements(all_totals=[])
        
        self.assertEqual(elements.all_totals, [])
        self.assertIsInstance(elements.all_totals, list)

    def test_odds_elements_modify_all_totals(self):
        """Test modifying all_totals after creation"""
        elements = OddsElements()
        mock_total = Mock()
        
        elements.all_totals.append(mock_total)
        
        self.assertEqual(len(elements.all_totals), 1)
        self.assertEqual(elements.all_totals[0], mock_total)


class TestH2HElements(unittest.TestCase):
    """Test cases for H2HElements dataclass"""

    def test_h2h_elements_default_creation(self):
        """Test creating H2HElements with default values"""
        elements = H2HElements()
        
        self.assertIsNone(elements.h2h_section)
        self.assertEqual(elements.h2h_rows, [])
        self.assertEqual(elements.h2h_row_count, 0)

    def test_h2h_elements_with_values(self):
        """Test creating H2HElements with specific values"""
        mock_section = Mock()
        mock_rows = [Mock(), Mock(), Mock()]
        
        elements = H2HElements(
            h2h_section=mock_section,
            h2h_rows=mock_rows,
            h2h_row_count=3
        )
        
        self.assertEqual(elements.h2h_section, mock_section)
        self.assertEqual(elements.h2h_rows, mock_rows)
        self.assertEqual(elements.h2h_row_count, 3)

    def test_h2h_elements_empty_rows(self):
        """Test creating H2HElements with empty rows"""
        elements = H2HElements(h2h_rows=[])
        
        self.assertEqual(elements.h2h_rows, [])
        self.assertEqual(elements.h2h_row_count, 0)

    def test_h2h_elements_modify_rows(self):
        """Test modifying h2h_rows after creation"""
        elements = H2HElements()
        mock_row = Mock()
        
        elements.h2h_rows.append(mock_row)
        elements.h2h_row_count = 1
        
        self.assertEqual(len(elements.h2h_rows), 1)
        self.assertEqual(elements.h2h_rows[0], mock_row)
        self.assertEqual(elements.h2h_row_count, 1)

    def test_h2h_elements_row_count_mismatch(self):
        """Test H2HElements with row count not matching actual rows"""
        mock_rows = [Mock(), Mock()]
        
        elements = H2HElements(
            h2h_rows=mock_rows,
            h2h_row_count=5  # Different from actual row count
        )
        
        self.assertEqual(len(elements.h2h_rows), 2)
        self.assertEqual(elements.h2h_row_count, 5)


class TestElementsModelIntegration(unittest.TestCase):
    """Integration tests for elements model classes"""

    def test_all_elements_creation(self):
        """Test creating all element types together"""
        # Create mock objects
        mock_match_element = Mock()
        mock_odds_element = Mock()
        mock_h2h_element = Mock()
        
        # Create all element types
        match_elements = MatchElements(
            country=mock_match_element,
            league=mock_match_element,
            home_team=mock_match_element,
            away_team=mock_match_element,
            date=mock_match_element,
            time=mock_match_element,
            match_id=mock_match_element
        )
        
        odds_elements = OddsElements(
            home_odds=mock_odds_element,
            away_odds=mock_odds_element,
            match_total=mock_odds_element,
            over_odds=mock_odds_element,
            under_odds=mock_odds_element,
            all_totals=[mock_odds_element, mock_odds_element]
        )
        
        h2h_elements = H2HElements(
            h2h_section=mock_h2h_element,
            h2h_rows=[mock_h2h_element, mock_h2h_element],
            h2h_row_count=2
        )
        
        # Verify all elements are created correctly
        self.assertIsNotNone(match_elements)
        self.assertIsNotNone(odds_elements)
        self.assertIsNotNone(h2h_elements)
        
        self.assertEqual(len(odds_elements.all_totals), 2)
        self.assertEqual(len(h2h_elements.h2h_rows), 2)
        self.assertEqual(h2h_elements.h2h_row_count, 2)

    def test_elements_immutability(self):
        """Test that elements can be modified after creation"""
        match_elements = MatchElements()
        odds_elements = OddsElements()
        h2h_elements = H2HElements()
        
        # Modify elements
        mock_element = Mock()
        match_elements.country = mock_element
        odds_elements.home_odds = mock_element
        h2h_elements.h2h_section = mock_element
        
        # Verify modifications
        self.assertEqual(match_elements.country, mock_element)
        self.assertEqual(odds_elements.home_odds, mock_element)
        self.assertEqual(h2h_elements.h2h_section, mock_element)


if __name__ == '__main__':
    unittest.main() 