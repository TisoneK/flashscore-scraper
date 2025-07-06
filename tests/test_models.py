#!/usr/bin/env python3
"""
Tests for data models
"""

import sys
import os
import unittest
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import MatchModel, OddsModel, H2HMatchModel


class TestOddsModel(unittest.TestCase):
    """Test cases for OddsModel"""

    def test_odds_model_creation(self):
        """Test creating an OddsModel instance"""
        odds = OddsModel(match_id='test123')
        
        self.assertEqual(odds.match_id, 'test123')
        self.assertIsNone(odds.home_odds)
        self.assertIsNone(odds.away_odds)
        self.assertIsNone(odds.match_total)
        self.assertIsNone(odds.over_odds)
        self.assertIsNone(odds.under_odds)

    def test_odds_model_with_values(self):
        """Test creating an OddsModel instance with values"""
        odds = OddsModel(
            match_id='test123',
            home_odds=1.85,
            away_odds=2.10,
            match_total=153.5,
            over_odds=1.85,
            under_odds=1.95
        )
        
        self.assertEqual(odds.match_id, 'test123')
        self.assertEqual(odds.home_odds, 1.85)
        self.assertEqual(odds.away_odds, 2.10)
        self.assertEqual(odds.match_total, 153.5)
        self.assertEqual(odds.over_odds, 1.85)
        self.assertEqual(odds.under_odds, 1.95)

    def test_odds_model_to_dict(self):
        """Test converting OddsModel to dictionary"""
        odds = OddsModel(
            match_id='test123',
            home_odds=1.85,
            away_odds=2.10,
            match_total=153.5,
            over_odds=1.85,
            under_odds=1.95
        )
        
        odds_dict = odds.__dict__
        
        self.assertEqual(odds_dict['match_id'], 'test123')
        self.assertEqual(odds_dict['home_odds'], 1.85)
        self.assertEqual(odds_dict['away_odds'], 2.10)
        self.assertEqual(odds_dict['match_total'], 153.5)
        self.assertEqual(odds_dict['over_odds'], 1.85)
        self.assertEqual(odds_dict['under_odds'], 1.95)


class TestH2HMatchModel(unittest.TestCase):
    """Test cases for H2HMatchModel"""

    def test_h2h_match_model_creation(self):
        """Test creating an H2HMatchModel instance"""
        h2h_match = H2HMatchModel(
            match_id='test123',
            date='2023-01-01',
            home_team='Team A',
            away_team='Team B',
            home_score=85,
            away_score=80,
            competition='League1'
        )
        
        self.assertEqual(h2h_match.match_id, 'test123')
        self.assertEqual(h2h_match.date, '2023-01-01')
        self.assertEqual(h2h_match.home_team, 'Team A')
        self.assertEqual(h2h_match.away_team, 'Team B')
        self.assertEqual(h2h_match.home_score, 85)
        self.assertEqual(h2h_match.away_score, 80)
        self.assertEqual(h2h_match.competition, 'League1')

    def test_h2h_match_model_to_dict(self):
        """Test converting H2HMatchModel to dictionary"""
        h2h_match = H2HMatchModel(
            match_id='test123',
            date='2023-01-01',
            home_team='Team A',
            away_team='Team B',
            home_score=85,
            away_score=80,
            competition='League1'
        )
        
        h2h_dict = h2h_match.__dict__
        
        self.assertEqual(h2h_dict['match_id'], 'test123')
        self.assertEqual(h2h_dict['date'], '2023-01-01')
        self.assertEqual(h2h_dict['home_team'], 'Team A')
        self.assertEqual(h2h_dict['away_team'], 'Team B')
        self.assertEqual(h2h_dict['home_score'], 85)
        self.assertEqual(h2h_dict['away_score'], 80)
        self.assertEqual(h2h_dict['competition'], 'League1')


class TestMatchModel(unittest.TestCase):
    """Test cases for MatchModel"""

    def setUp(self):
        """Set up test fixtures"""
        self.odds = OddsModel(
            match_id='test123',
            home_odds=1.85,
            away_odds=2.10,
            match_total=153.5,
            over_odds=1.85,
            under_odds=1.95
        )
        
        self.h2h_match = H2HMatchModel(
            match_id='test123',
            date='2023-01-01',
            home_team='Team A',
            away_team='Team B',
            home_score=85,
            away_score=80,
            competition='League1'
        )

    def test_match_model_creation(self):
        """Test creating a MatchModel instance"""
        match = MatchModel(
            match_id='test123',
            country='Test Country',
            league='Test League',
            home_team='Team A',
            away_team='Team B',
            date='2023-01-01',
            time='20:00',
            odds=self.odds,
            h2h_matches=[self.h2h_match],
            status='complete',
            skip_reason=''
        )
        
        self.assertEqual(match.match_id, 'test123')
        self.assertEqual(match.country, 'Test Country')
        self.assertEqual(match.league, 'Test League')
        self.assertEqual(match.home_team, 'Team A')
        self.assertEqual(match.away_team, 'Team B')
        self.assertEqual(match.date, '2023-01-01')
        self.assertEqual(match.time, '20:00')
        self.assertEqual(match.odds, self.odds)
        self.assertEqual(len(match.h2h_matches), 1)
        self.assertEqual(match.status, 'complete')
        self.assertEqual(match.skip_reason, '')

    def test_match_model_with_skip_reason(self):
        """Test creating a MatchModel instance with skip reason"""
        match = MatchModel(
            match_id='test123',
            country='Test Country',
            league='Test League',
            home_team='Team A',
            away_team='Team B',
            date='2023-01-01',
            time='20:00',
            odds=self.odds,
            h2h_matches=[],
            status='incomplete',
            skip_reason='missing odds data'
        )
        
        self.assertEqual(match.status, 'incomplete')
        self.assertEqual(match.skip_reason, 'missing odds data')
        self.assertEqual(len(match.h2h_matches), 0)

    def test_match_model_to_dict(self):
        """Test converting MatchModel to dictionary"""
        match = MatchModel(
            match_id='test123',
            country='Test Country',
            league='Test League',
            home_team='Team A',
            away_team='Team B',
            date='2023-01-01',
            time='20:00',
            odds=self.odds,
            h2h_matches=[self.h2h_match],
            status='complete',
            skip_reason=''
        )
        
        match_dict = match.__dict__
        
        self.assertEqual(match_dict['match_id'], 'test123')
        self.assertEqual(match_dict['country'], 'Test Country')
        self.assertEqual(match_dict['league'], 'Test League')
        self.assertEqual(match_dict['home_team'], 'Team A')
        self.assertEqual(match_dict['away_team'], 'Team B')
        self.assertEqual(match_dict['date'], '2023-01-01')
        self.assertEqual(match_dict['time'], '20:00')
        self.assertEqual(match_dict['odds'], self.odds)
        self.assertEqual(len(match_dict['h2h_matches']), 1)
        self.assertEqual(match_dict['status'], 'complete')
        self.assertEqual(match_dict['skip_reason'], '')

    def test_match_model_created_at(self):
        """Test that created_at is automatically set"""
        match = MatchModel(
            match_id='test123',
            country='Test Country',
            league='Test League',
            home_team='Team A',
            away_team='Team B',
            date='2023-01-01',
            time='20:00',
            odds=self.odds,
            h2h_matches=[],
            status='complete',
            skip_reason=''
        )
        
        # Check that created_at is set and is a valid datetime string
        self.assertIsNotNone(match.created_at)
        try:
            datetime.fromisoformat(match.created_at.replace('Z', '+00:00'))
        except ValueError:
            self.fail("created_at is not a valid datetime string")


if __name__ == '__main__':
    unittest.main() 