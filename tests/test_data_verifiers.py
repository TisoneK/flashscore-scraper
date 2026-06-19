#!/usr/bin/env python3
"""
Tests for data verifiers
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.data.verifier.base_verifier import BaseVerifier
from src.data.verifier.match_data_verifier import MatchDataVerifier
from src.data.verifier.odds_data_verifier import OddsDataVerifier
from src.data.verifier.h2h_data_verifier import H2HDataVerifier
from src.data.verifier.model_verifier import ModelVerifier
from src.data.verifier.loader_verifier import LoaderVerifier
from src.data.verifier.extractor_verifier import ExtractorVerifier


@pytest.fixture
def mock_driver():
    """Fixture for mock driver"""
    return Mock()


@pytest.fixture
def base_verifier(mock_driver):
    """Fixture for BaseVerifier"""
    return BaseVerifier(mock_driver)


@pytest.fixture
def match_data_verifier(mock_driver):
    """Fixture for MatchDataVerifier"""
    return MatchDataVerifier(mock_driver)


@pytest.fixture
def odds_data_verifier(mock_driver):
    """Fixture for OddsDataVerifier"""
    return OddsDataVerifier(mock_driver)


@pytest.fixture
def h2h_data_verifier(mock_driver):
    """Fixture for H2HDataVerifier"""
    return H2HDataVerifier(mock_driver)


@pytest.fixture
def model_verifier(mock_driver):
    """Fixture for ModelVerifier"""
    return ModelVerifier(mock_driver)


@pytest.fixture
def loader_verifier(mock_driver):
    """Fixture for LoaderVerifier"""
    return LoaderVerifier(mock_driver)


@pytest.fixture
def extractor_verifier(mock_driver):
    """Fixture for ExtractorVerifier"""
    return ExtractorVerifier(mock_driver)


# BaseVerifier tests
def test_base_verifier_initialization(base_verifier, mock_driver):
    """Test BaseVerifier initialization"""
    assert base_verifier.driver == mock_driver


def test_base_verifier_verify_method(base_verifier):
    """Test BaseVerifier verify method"""
    # BaseVerifier.verify should be implemented by subclasses
    with pytest.raises(NotImplementedError):
        base_verifier.verify()


# MatchDataVerifier tests
def test_match_data_verifier_initialization(match_data_verifier, mock_driver):
    """Test MatchDataVerifier initialization"""
    assert match_data_verifier.driver == mock_driver


def test_verify_match_page_success(match_data_verifier, mock_driver):
    """Test successful match page verification"""
    # Mock the find_element method to return a valid element
    mock_element = Mock()
    mock_driver.find_element.return_value = mock_element
    
    result = match_data_verifier.verify_match_page()
    
    assert result is True
    mock_driver.find_element.assert_called()


def test_verify_match_page_failure(match_data_verifier, mock_driver):
    """Test match page verification failure"""
    # Mock the find_element method to raise an exception
    mock_driver.find_element.side_effect = Exception("Element not found")
    
    result = match_data_verifier.verify_match_page()
    
    assert result is False


def test_verify_match_data_success(match_data_verifier):
    """Test successful match data verification"""
    mock_elements = Mock()
    mock_elements.country = Mock(text='Test Country')
    mock_elements.league = Mock(text='Test League')
    mock_elements.home_team = Mock(text='Team A')
    mock_elements.away_team = Mock(text='Team B')
    mock_elements.date = Mock(text='2023-01-01')
    mock_elements.time = Mock(text='20:00')
    
    result = match_data_verifier.verify_match_data(mock_elements)
    
    assert result is True


def test_verify_match_data_missing_fields(match_data_verifier):
    """Test match data verification with missing fields"""
    mock_elements = Mock()
    mock_elements.country = None
    mock_elements.league = Mock(text='Test League')
    mock_elements.home_team = None
    mock_elements.away_team = Mock(text='Team B')
    mock_elements.date = None
    mock_elements.time = Mock(text='20:00')
    
    result = match_data_verifier.verify_match_data(mock_elements)
    
    assert result is False


def test_verify_match_data_empty_fields(match_data_verifier):
    """Test match data verification with empty fields"""
    mock_elements = Mock()
    mock_elements.country = Mock(text='')
    mock_elements.league = Mock(text='Test League')
    mock_elements.home_team = Mock(text='   ')  # Whitespace
    mock_elements.away_team = Mock(text='Team B')
    mock_elements.date = Mock(text='2023-01-01')
    mock_elements.time = Mock(text='20:00')
    
    result = match_data_verifier.verify_match_data(mock_elements)
    
    assert result is False


# OddsDataVerifier tests
def test_odds_data_verifier_initialization(odds_data_verifier, mock_driver):
    """Test OddsDataVerifier initialization"""
    assert odds_data_verifier.driver == mock_driver


@pytest.mark.parametrize("total", ['153.5', '154.0', '155.5', '160.0'])
def test_verify_match_total_valid(odds_data_verifier, total):
    """Test valid match total verification"""
    is_valid, error = odds_data_verifier.verify_match_total(total)
    assert is_valid is True, f"Match total {total} should be valid"
    assert error is None


@pytest.mark.parametrize("total", [None, '', 'invalid', 'abc', '123.456'])
def test_verify_match_total_invalid(odds_data_verifier, total):
    """Test invalid match total verification"""
    is_valid, error = odds_data_verifier.verify_match_total(total)
    assert is_valid is False, f"Match total {total} should be invalid"
    assert error is not None


@pytest.mark.parametrize("odds", ['1.85', '2.10', '1.50', '3.00'])
def test_verify_over_odds_valid(odds_data_verifier, odds):
    """Test valid over odds verification"""
    is_valid, error = odds_data_verifier.verify_over_odds(odds)
    assert is_valid is True, f"Over odds {odds} should be valid"
    assert error is None


@pytest.mark.parametrize("odds", [None, '', 'invalid', 'abc', '0.5', '10.0'])
def test_verify_over_odds_invalid(odds_data_verifier, odds):
    """Test invalid over odds verification"""
    is_valid, error = odds_data_verifier.verify_over_odds(odds)
    assert is_valid is False, f"Over odds {odds} should be invalid"
    assert error is not None


@pytest.mark.parametrize("odds", ['1.85', '2.10', '1.50', '3.00'])
def test_verify_under_odds_valid(odds_data_verifier, odds):
    """Test valid under odds verification"""
    is_valid, error = odds_data_verifier.verify_under_odds(odds)
    assert is_valid is True, f"Under odds {odds} should be valid"
    assert error is None


@pytest.mark.parametrize("odds", [None, '', 'invalid', 'abc', '0.5', '10.0'])
def test_verify_under_odds_invalid(odds_data_verifier, odds):
    """Test invalid under odds verification"""
    is_valid, error = odds_data_verifier.verify_under_odds(odds)
    assert is_valid is False, f"Under odds {odds} should be invalid"
    assert error is not None


@pytest.mark.parametrize("odds", ['1.85', '2.10', '1.50', '3.00'])
def test_verify_home_odds_valid(odds_data_verifier, odds):
    """Test valid home odds verification"""
    is_valid, error = odds_data_verifier.verify_home_odds(odds)
    assert is_valid is True, f"Home odds {odds} should be valid"
    assert error is None


@pytest.mark.parametrize("odds", [None, '', 'invalid', 'abc', '0.5', '10.0'])
def test_verify_home_odds_invalid(odds_data_verifier, odds):
    """Test invalid home odds verification"""
    is_valid, error = odds_data_verifier.verify_home_odds(odds)
    assert is_valid is False, f"Home odds {odds} should be invalid"
    assert error is not None


@pytest.mark.parametrize("odds", ['1.85', '2.10', '1.50', '3.00'])
def test_verify_away_odds_valid(odds_data_verifier, odds):
    """Test valid away odds verification"""
    is_valid, error = odds_data_verifier.verify_away_odds(odds)
    assert is_valid is True, f"Away odds {odds} should be valid"
    assert error is None


@pytest.mark.parametrize("odds", [None, '', 'invalid', 'abc', '0.5', '10.0'])
def test_verify_away_odds_invalid(odds_data_verifier, odds):
    """Test invalid away odds verification"""
    is_valid, error = odds_data_verifier.verify_away_odds(odds)
    assert is_valid is False, f"Away odds {odds} should be invalid"
    assert error is not None


# H2HDataVerifier tests
def test_h2h_data_verifier_initialization(h2h_data_verifier, mock_driver):
    """Test H2HDataVerifier initialization"""
    assert h2h_data_verifier.driver == mock_driver


def test_verify_h2h_section_success(h2h_data_verifier, mock_driver):
    """Test successful H2H section verification"""
    mock_element = Mock()
    mock_driver.find_element.return_value = mock_element
    
    result = h2h_data_verifier.verify_h2h_section()
    
    assert result is True
    mock_driver.find_element.assert_called()


def test_verify_h2h_section_failure(h2h_data_verifier, mock_driver):
    """Test H2H section verification failure"""
    mock_driver.find_element.side_effect = Exception("Element not found")
    
    result = h2h_data_verifier.verify_h2h_section()
    
    assert result is False


def test_verify_h2h_data_success(h2h_data_verifier):
    """Test successful H2H data verification"""
    mock_elements = Mock()
    mock_elements.h2h_rows = [Mock(), Mock(), Mock()]
    mock_elements.h2h_row_count = 3
    
    result = h2h_data_verifier.verify_h2h_data(mock_elements)
    
    assert result is True


def test_verify_h2h_data_empty(h2h_data_verifier):
    """Test H2H data verification with empty data"""
    mock_elements = Mock()
    mock_elements.h2h_rows = []
    mock_elements.h2h_row_count = 0
    
    result = h2h_data_verifier.verify_h2h_data(mock_elements)
    
    assert result is False


def test_verify_h2h_data_mismatch(h2h_data_verifier):
    """Test H2H data verification with count mismatch"""
    mock_elements = Mock()
    mock_elements.h2h_rows = [Mock(), Mock()]
    mock_elements.h2h_row_count = 5  # Different from actual count
    
    result = h2h_data_verifier.verify_h2h_data(mock_elements)
    
    assert result is False


# ModelVerifier tests
def test_model_verifier_initialization(model_verifier, mock_driver):
    """Test ModelVerifier initialization"""
    assert model_verifier.driver == mock_driver


def test_verify_match_model_success(model_verifier):
    """Test successful match model verification"""
    from src.models import MatchModel, OddsModel
    
    odds = OddsModel(match_id='test123')
    odds.home_odds = 1.85
    odds.away_odds = 2.10
    odds.match_total = 153.5
    odds.over_odds = 1.85
    odds.under_odds = 1.95
    
    match = MatchModel(
        match_id='test123',
        country='Test Country',
        league='Test League',
        home_team='Team A',
        away_team='Team B',
        date='2023-01-01',
        time='20:00',
        odds=odds,
        h2h_matches=[],
        status='complete',
        skip_reason=''
    )
    
    result = model_verifier.verify_match_model(match)
    
    assert result is True


def test_verify_match_model_invalid(model_verifier):
    """Test invalid match model verification"""
    from src.models import MatchModel, OddsModel
    
    odds = OddsModel(match_id='test123')
    # Missing required odds fields
    
    match = MatchModel(
        match_id='test123',
        country='',
        league='',
        home_team='',
        away_team='',
        date='',
        time='',
        odds=odds,
        h2h_matches=[],
        status='incomplete',
        skip_reason='missing data'
    )
    
    result = model_verifier.verify_match_model(match)
    
    assert result is False


# LoaderVerifier tests
def test_loader_verifier_initialization(loader_verifier, mock_driver):
    """Test LoaderVerifier initialization"""
    assert loader_verifier.driver == mock_driver


def test_verify_loader_success(loader_verifier, mock_driver):
    """Test successful loader verification"""
    mock_loader = Mock()
    mock_loader.driver = mock_driver
    mock_loader.elements = Mock()
    
    result = loader_verifier.verify_loader(mock_loader)
    
    assert result is True


def test_verify_loader_missing_driver(loader_verifier):
    """Test loader verification with missing driver"""
    mock_loader = Mock()
    mock_loader.driver = None
    mock_loader.elements = Mock()
    
    result = loader_verifier.verify_loader(mock_loader)
    
    assert result is False


def test_verify_loader_missing_elements(loader_verifier, mock_driver):
    """Test loader verification with missing elements"""
    mock_loader = Mock()
    mock_loader.driver = mock_driver
    mock_loader.elements = None
    
    result = loader_verifier.verify_loader(mock_loader)
    
    assert result is False


# ExtractorVerifier tests
def test_extractor_verifier_initialization(extractor_verifier, mock_driver):
    """Test ExtractorVerifier initialization"""
    assert extractor_verifier.driver == mock_driver


def test_verify_extractor_success(extractor_verifier):
    """Test successful extractor verification"""
    mock_extractor = Mock()
    mock_extractor.loader = Mock()
    mock_extractor.elements = Mock()
    
    result = extractor_verifier.verify_extractor(mock_extractor)
    
    assert result is True


def test_verify_extractor_missing_loader(extractor_verifier):
    """Test extractor verification with missing loader"""
    mock_extractor = Mock()
    mock_extractor.loader = None
    mock_extractor.elements = Mock()
    
    result = extractor_verifier.verify_extractor(mock_extractor)
    
    assert result is False


def test_verify_extractor_missing_elements(extractor_verifier):
    """Test extractor verification with missing elements"""
    mock_extractor = Mock()
    mock_extractor.loader = Mock()
    mock_extractor.elements = None
    
    result = extractor_verifier.verify_extractor(mock_extractor)
    
    assert result is False


# Integration tests
def test_all_verifiers_initialization(mock_driver):
    """Test all verifiers can be initialized together"""
    match_verifier = MatchDataVerifier(mock_driver)
    odds_verifier = OddsDataVerifier(mock_driver)
    h2h_verifier = H2HDataVerifier(mock_driver)
    model_verifier = ModelVerifier(mock_driver)
    loader_verifier = LoaderVerifier(mock_driver)
    extractor_verifier = ExtractorVerifier(mock_driver)
    
    assert match_verifier.driver == mock_driver
    assert odds_verifier.driver == mock_driver
    assert h2h_verifier.driver == mock_driver
    assert model_verifier.driver == mock_driver
    assert loader_verifier.driver == mock_driver
    assert extractor_verifier.driver == mock_driver


def test_verifiers_share_driver(mock_driver):
    """Test that all verifiers share the same driver"""
    verifiers = [
        MatchDataVerifier(mock_driver),
        OddsDataVerifier(mock_driver),
        H2HDataVerifier(mock_driver),
        ModelVerifier(mock_driver),
        LoaderVerifier(mock_driver),
        ExtractorVerifier(mock_driver)
    ]
    
    for verifier in verifiers:
        assert verifier.driver == mock_driver 