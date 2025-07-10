#!/usr/bin/env python3
"""
Tests for data extractors
"""

import sys
import os
import pytest
from unittest.mock import Mock

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.extractor.match_data_extractor import MatchDataExtractor
from src.data.extractor.h2h_data_extractor import H2HDataExtractor
from src.data.elements_model import MatchElements, H2HElements
from src.core.exceptions import DataNotFoundError, DataParseError, DataValidationError


@pytest.fixture
def mock_loader():
    """Fixture for mock loader"""
    loader = Mock()
    loader.elements = MatchElements()
    return loader


@pytest.fixture
def match_extractor(mock_loader):
    """Fixture for MatchDataExtractor"""
    return MatchDataExtractor(mock_loader)


@pytest.fixture
def mock_h2h_loader():
    """Fixture for mock H2H loader with required methods"""
    loader = Mock()
    loader.elements = H2HElements()
    
    # Mock the required methods for H2HDataExtractor
    loader.get_date = Mock()
    loader.get_home_team = Mock()
    loader.get_away_team = Mock()
    loader.get_result = Mock()
    loader.get_competition = Mock()
    
    return loader


@pytest.fixture
def match_extractor(mock_loader):
    """Fixture for MatchDataExtractor"""
    return MatchDataExtractor(mock_loader)


@pytest.fixture
def h2h_extractor(mock_h2h_loader):
    """Fixture for H2HDataExtractor"""
    return H2HDataExtractor(mock_h2h_loader)


class TestMatchDataExtractor:
    """Test cases for MatchDataExtractor"""

    def test_match_data_extractor_initialization(self, match_extractor, mock_loader):
        """Test MatchDataExtractor initialization"""
        assert match_extractor.get_loader() == mock_loader
        assert hasattr(match_extractor, 'match_data_verifier')

    def test_extract_match_data_success(self, match_extractor, mock_loader):
        """Test successful match data extraction"""
        # Mock elements with text
        mock_country = Mock()
        mock_country.text = 'Test Country'
        mock_league = Mock()
        mock_league.text = 'Test League'
        mock_home_team = Mock()
        mock_home_team.text = 'Team A'
        mock_away_team = Mock()
        mock_away_team.text = 'Team B'
        mock_date = Mock()
        mock_date.text = '2023-01-01 20:00'
        mock_match_id = 'test123'
        
        mock_loader.elements.country = mock_country
        mock_loader.elements.league = mock_league
        mock_loader.elements.home_team = mock_home_team
        mock_loader.elements.away_team = mock_away_team
        mock_loader.elements.date = mock_date
        mock_loader.elements.match_id = mock_match_id
        
        result = match_extractor.extract_match_data()
        
        assert result.country == 'Test Country'
        assert result.league == 'Test League'
        assert result.home_team == 'Team A'
        assert result.away_team == 'Team B'
        assert result.date == '2023-01-01'
        assert result.time == '20:00'
        assert result.match_id == 'test123'

    def test_extract_match_data_with_none_elements(self, match_extractor, mock_loader):
        """Test match data extraction with None elements"""
        # Set some elements to None
        mock_loader.elements.country = None
        mock_league = Mock()
        mock_league.text = 'Test League'
        mock_loader.elements.league = mock_league
        mock_loader.elements.home_team = None
        mock_away_team = Mock()
        mock_away_team.text = 'Team B'
        mock_loader.elements.away_team = mock_away_team
        mock_date = Mock()
        mock_date.text = '2023-01-01 20:00'
        mock_loader.elements.date = mock_date
        mock_loader.elements.time = None
        mock_loader.elements.match_id = 'test123'
        
        result = match_extractor.extract_match_data()
        
        assert result.country is None
        assert result.league == 'Test League'
        assert result.home_team is None
        assert result.away_team == 'Team B'
        assert result.date == '2023-01-01'
        assert result.time == '20:00'
        assert result.match_id == 'test123'

    def test_extract_match_data_with_empty_text(self, match_extractor, mock_loader):
        """Test match data extraction with empty text"""
        mock_country = Mock()
        mock_country.text = ''
        mock_league = Mock()
        mock_league.text = '   '  # Whitespace
        mock_home_team = Mock()
        mock_home_team.text = 'Team A'
        
        mock_loader.elements.country = mock_country
        mock_loader.elements.league = mock_league
        mock_loader.elements.home_team = mock_home_team
        mock_loader.elements.away_team = None
        mock_loader.elements.date = None
        mock_loader.elements.match_id = None
        
        result = match_extractor.extract_match_data()
        
        assert result.country is None
        assert result.league is None
        assert result.home_team == 'Team A'
        assert result.away_team is None
        assert result.date is None
        assert result.time is None
        assert result.match_id is None

    def test_extract_match_data_property_access(self, match_extractor, mock_loader):
        """Test accessing extracted data via properties"""
        mock_country = Mock()
        mock_country.text = 'Test Country'
        mock_league = Mock()
        mock_league.text = 'Test League'
        
        mock_loader.elements.country = mock_country
        mock_loader.elements.league = mock_league
        mock_loader.elements.home_team = None
        mock_loader.elements.away_team = None
        mock_loader.elements.date = None
        mock_loader.elements.match_id = None
        
        # Extract data
        match_extractor.extract_match_data()
        
        # Access via properties
        assert match_extractor.country == 'Test Country'
        assert match_extractor.league == 'Test League'
        assert match_extractor.home_team is None
        assert match_extractor.away_team is None
        assert match_extractor.date is None
        assert match_extractor.time is None
        assert match_extractor.match_id is None

    def test_extract_match_data_exception_handling(self, match_extractor, mock_loader):
        """Test match data extraction with exception handling"""
        mock_country = Mock()
        mock_country.text = 'Test Country'
        mock_league = Mock()
        mock_league.text.side_effect = Exception("Text access error")
        
        mock_loader.elements.country = mock_country
        mock_loader.elements.league = mock_league
        mock_loader.elements.home_team = None
        mock_loader.elements.away_team = None
        mock_loader.elements.date = None
        mock_loader.elements.match_id = None
        
        # Should handle DataParseError gracefully
        try:
            result = match_extractor.extract_match_data()
        except DataParseError as e:
            assert "Text access error" in str(e)
        else:
            # If no exception, check for partial data
            assert result.country == 'Test Country'
            assert result.league is None


class TestH2HDataExtractor:
    """Test cases for H2HDataExtractor"""

    def test_h2h_data_extractor_initialization(self, h2h_extractor, mock_h2h_loader):
        """Test H2HDataExtractor initialization"""
        assert h2h_extractor._loader == mock_h2h_loader
        assert isinstance(h2h_extractor.elements, H2HElements)

    def test_extract_h2h_data_success(self, h2h_extractor, mock_h2h_loader):
        """Test successful H2H data extraction"""
        # Mock row objects with proper structure
        mock_row1 = Mock()
        mock_row2 = Mock()
        
        # Mock the loader methods to return proper elements
        mock_date_el = Mock()
        mock_date_el.text = '2023-01-01'
        mock_h2h_loader.get_date.return_value = mock_date_el
        
        mock_home_el = Mock()
        mock_home_el.text = 'Team A'
        mock_h2h_loader.get_home_team.return_value = mock_home_el
        
        mock_away_el = Mock()
        mock_away_el.text = 'Team B'
        mock_h2h_loader.get_away_team.return_value = mock_away_el
        
        mock_result_el = Mock()
        mock_result_el.text = '85 - 80'
        mock_h2h_loader.get_result.return_value = mock_result_el
        
        mock_comp_el = Mock()
        mock_comp_el.text = 'League1'
        mock_h2h_loader.get_competition.return_value = mock_comp_el
        
        # Set up the h2h_rows
        mock_h2h_loader.elements.h2h_rows = [mock_row1, mock_row2]
        
        result = h2h_extractor.extract_h2h_data()
        
        assert len(result) == 2
        assert result[0]['date'] == '2023-01-01'
        assert result[0]['home_team'] == 'Team A'
        assert result[0]['away_team'] == 'Team B'
        assert result[0]['competition'] == 'League1'

    def test_extract_h2h_data_empty_rows(self, h2h_extractor, mock_h2h_loader):
        """Test H2H data extraction with empty rows"""
        mock_h2h_loader.elements.h2h_rows = []
        
        result = h2h_extractor.extract_h2h_data()
        
        assert len(result) == 0

    def test_extract_h2h_data_with_none_elements(self, h2h_extractor, mock_h2h_loader):
        """Test H2H data extraction with None elements"""
        # Mock row object
        mock_row = Mock()
        mock_h2h_loader.elements.h2h_rows = [mock_row]
        
        # Mock the loader methods to return proper elements
        mock_date_el = Mock()
        mock_date_el.text = '2023-01-01'
        mock_h2h_loader.get_date.return_value = mock_date_el
        
        mock_home_el = Mock()
        mock_home_el.text = 'Team A'
        mock_h2h_loader.get_home_team.return_value = mock_home_el
        
        mock_away_el = Mock()
        mock_away_el.text = 'Team B'
        mock_h2h_loader.get_away_team.return_value = mock_away_el
        
        mock_result_el = Mock()
        mock_result_el.text = '85 - 80'
        mock_h2h_loader.get_result.return_value = mock_result_el
        
        mock_comp_el = Mock()
        mock_comp_el.text = 'League1'
        mock_h2h_loader.get_competition.return_value = mock_comp_el
        
        result = h2h_extractor.extract_h2h_data()
        
        assert len(result) == 1
        assert result[0]['date'] == '2023-01-01'
        assert result[0]['home_team'] == 'Team A'
        assert result[0]['away_team'] == 'Team B'
        assert result[0]['competition'] == 'League1'

    def test_get_date(self, h2h_extractor, mock_h2h_loader):
        """Test getting date from H2H data"""
        # Set up mock data
        mock_row = Mock()
        mock_h2h_loader.elements.h2h_rows = [mock_row]
        
        # Mock the loader methods
        mock_date_el = Mock()
        mock_date_el.text = '2023-01-01'
        mock_h2h_loader.get_date.return_value = mock_date_el
        
        mock_home_el = Mock()
        mock_home_el.text = 'Team A'
        mock_h2h_loader.get_home_team.return_value = mock_home_el
        
        mock_away_el = Mock()
        mock_away_el.text = 'Team B'
        mock_h2h_loader.get_away_team.return_value = mock_away_el
        
        mock_result_el = Mock()
        mock_result_el.text = '85 - 80'
        mock_h2h_loader.get_result.return_value = mock_result_el
        
        mock_comp_el = Mock()
        mock_comp_el.text = 'League1'
        mock_h2h_loader.get_competition.return_value = mock_comp_el
        
        h2h_extractor.extract_h2h_data()
        date = h2h_extractor.get_date(0)
        
        assert date == '2023-01-01'

    def test_get_home_team(self, h2h_extractor, mock_h2h_loader):
        """Test getting home team from H2H data"""
        # Set up mock data
        mock_row = Mock()
        mock_h2h_loader.elements.h2h_rows = [mock_row]
        
        # Mock the loader methods
        mock_date_el = Mock()
        mock_date_el.text = '2023-01-01'
        mock_h2h_loader.get_date.return_value = mock_date_el
        
        mock_home_el = Mock()
        mock_home_el.text = 'Team A'
        mock_h2h_loader.get_home_team.return_value = mock_home_el
        
        mock_away_el = Mock()
        mock_away_el.text = 'Team B'
        mock_h2h_loader.get_away_team.return_value = mock_away_el
        
        mock_result_el = Mock()
        mock_result_el.text = '85 - 80'
        mock_h2h_loader.get_result.return_value = mock_result_el
        
        mock_comp_el = Mock()
        mock_comp_el.text = 'League1'
        mock_h2h_loader.get_competition.return_value = mock_comp_el
        
        h2h_extractor.extract_h2h_data()
        home_team = h2h_extractor.get_home_team(0)
        
        assert home_team == 'Team A'

    def test_get_away_team(self, h2h_extractor, mock_h2h_loader):
        """Test getting away team from H2H data"""
        # Set up mock data
        mock_row = Mock()
        mock_h2h_loader.elements.h2h_rows = [mock_row]
        
        # Mock the loader methods
        mock_date_el = Mock()
        mock_date_el.text = '2023-01-01'
        mock_h2h_loader.get_date.return_value = mock_date_el
        
        mock_home_el = Mock()
        mock_home_el.text = 'Team A'
        mock_h2h_loader.get_home_team.return_value = mock_home_el
        
        mock_away_el = Mock()
        mock_away_el.text = 'Team B'
        mock_h2h_loader.get_away_team.return_value = mock_away_el
        
        mock_result_el = Mock()
        mock_result_el.text = '85 - 80'
        mock_h2h_loader.get_result.return_value = mock_result_el
        
        mock_comp_el = Mock()
        mock_comp_el.text = 'League1'
        mock_h2h_loader.get_competition.return_value = mock_comp_el
        
        h2h_extractor.extract_h2h_data()
        away_team = h2h_extractor.get_away_team(0)
        
        assert away_team == 'Team B'

    def test_get_home_score(self, h2h_extractor, mock_h2h_loader):
        """Test getting home score from H2H data"""
        # Set up mock data
        mock_row = Mock()
        mock_row.get.return_value = Mock(text='85')
        mock_h2h_loader.elements.h2h_rows = [mock_row]
        
        # Mock the loader methods
        mock_date_el = Mock()
        mock_date_el.text = '2023-01-01'
        mock_h2h_loader.get_date.return_value = mock_date_el
        
        mock_home_el = Mock()
        mock_home_el.text = 'Team A'
        mock_h2h_loader.get_home_team.return_value = mock_home_el
        
        mock_away_el = Mock()
        mock_away_el.text = 'Team B'
        mock_h2h_loader.get_away_team.return_value = mock_away_el
        
        mock_result_el = Mock()
        mock_result_el.text = '85 - 80'
        mock_h2h_loader.get_result.return_value = mock_result_el
        
        mock_comp_el = Mock()
        mock_comp_el.text = 'League1'
        mock_h2h_loader.get_competition.return_value = mock_comp_el
        
        h2h_extractor.extract_h2h_data()
        home_score = h2h_extractor.get_home_score(0)
        
        assert home_score == '85'

    def test_get_away_score(self, h2h_extractor, mock_h2h_loader):
        """Test getting away score from H2H data"""
        # Set up mock data
        mock_row = Mock()
        mock_row.get.return_value = Mock(text='80')
        mock_h2h_loader.elements.h2h_rows = [mock_row]
        
        # Mock the loader methods
        mock_date_el = Mock()
        mock_date_el.text = '2023-01-01'
        mock_h2h_loader.get_date.return_value = mock_date_el
        
        mock_home_el = Mock()
        mock_home_el.text = 'Team A'
        mock_h2h_loader.get_home_team.return_value = mock_home_el
        
        mock_away_el = Mock()
        mock_away_el.text = 'Team B'
        mock_h2h_loader.get_away_team.return_value = mock_away_el
        
        mock_result_el = Mock()
        mock_result_el.text = '85 - 80'
        mock_h2h_loader.get_result.return_value = mock_result_el
        
        mock_comp_el = Mock()
        mock_comp_el.text = 'League1'
        mock_h2h_loader.get_competition.return_value = mock_comp_el
        
        h2h_extractor.extract_h2h_data()
        away_score = h2h_extractor.get_away_score(0)
        
        assert away_score == '80'

    def test_get_competition(self, h2h_extractor, mock_h2h_loader):
        """Test getting competition from H2H data"""
        # Set up mock data
        mock_row = Mock()
        mock_h2h_loader.elements.h2h_rows = [mock_row]
        
        # Mock the loader methods
        mock_date_el = Mock()
        mock_date_el.text = '2023-01-01'
        mock_h2h_loader.get_date.return_value = mock_date_el
        
        mock_home_el = Mock()
        mock_home_el.text = 'Team A'
        mock_h2h_loader.get_home_team.return_value = mock_home_el
        
        mock_away_el = Mock()
        mock_away_el.text = 'Team B'
        mock_h2h_loader.get_away_team.return_value = mock_away_el
        
        mock_result_el = Mock()
        mock_result_el.text = '85 - 80'
        mock_h2h_loader.get_result.return_value = mock_result_el
        
        mock_comp_el = Mock()
        mock_comp_el.text = 'League1'
        mock_h2h_loader.get_competition.return_value = mock_comp_el
        
        h2h_extractor.extract_h2h_data()
        competition = h2h_extractor.get_competition(0)
        
        assert competition == 'League1'

    def test_get_data_invalid_index(self, h2h_extractor, mock_h2h_loader):
        """Test getting data with invalid index"""
        # Set up mock data
        mock_row = Mock()
        mock_h2h_loader.elements.h2h_rows = [mock_row]
        
        # Mock the loader methods
        mock_date_el = Mock()
        mock_date_el.text = '2023-01-01'
        mock_h2h_loader.get_date.return_value = mock_date_el
        
        mock_home_el = Mock()
        mock_home_el.text = 'Team A'
        mock_h2h_loader.get_home_team.return_value = mock_home_el
        
        mock_away_el = Mock()
        mock_away_el.text = 'Team B'
        mock_h2h_loader.get_away_team.return_value = mock_away_el
        
        mock_result_el = Mock()
        mock_result_el.text = '85 - 80'
        mock_h2h_loader.get_result.return_value = mock_result_el
        
        mock_comp_el = Mock()
        mock_comp_el.text = 'League1'
        mock_h2h_loader.get_competition.return_value = mock_comp_el
        
        h2h_extractor.extract_h2h_data()
        date = h2h_extractor.get_date(999)  # Invalid index
        
        assert date is None

    def test_extract_h2h_data_exception_handling(self, h2h_extractor, mock_h2h_loader):
        """Test H2H data extraction with exception handling"""
        mock_row = Mock()
        mock_row.get.side_effect = Exception("Text access error")
        mock_h2h_loader.elements.h2h_rows = [mock_row]
        
        # Should handle DataParseError gracefully
        try:
            result = h2h_extractor.extract_h2h_data()
        except DataParseError as e:
            assert "Text access error" in str(e)
        else:
            # If no exception, check for empty result
            assert len(result) == 0


class TestDataExtractorsIntegration:
    """Integration tests for data extractors"""

    def test_extractors_with_same_loader(self, mock_loader):
        """Test that extractors can share the same loader"""
        match_extractor = MatchDataExtractor(mock_loader)
        h2h_extractor = H2HDataExtractor(mock_loader)
        
        assert match_extractor.get_loader() == mock_loader
        assert h2h_extractor._loader == mock_loader
        assert hasattr(match_extractor, 'match_data_verifier')
        assert hasattr(h2h_extractor, 'h2h_data_verifier')

    def test_extractors_data_consistency(self, mock_loader):
        """Test data consistency between extractors"""
        # Set up mock data
        mock_country = Mock()
        mock_country.text = 'Test Country'
        mock_loader.elements.country = mock_country
        
        # Create extractors
        match_extractor = MatchDataExtractor(mock_loader)
        h2h_extractor = H2HDataExtractor(mock_loader)
        
        # Extract match data
        match_result = match_extractor.extract_match_data()
        
        # Verify match data was extracted
        assert match_result.country == 'Test Country'
        assert len(h2h_extractor.extract_h2h_data()) == 0 