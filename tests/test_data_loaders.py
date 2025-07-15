import pytest
from unittest.mock import Mock, patch
from selenium.webdriver.remote.webdriver import WebDriver
from src.data.loader.match_data_loader import MatchDataLoader
from src.data.loader.odds_data_loader import OddsDataLoader
from src.data.loader.h2h_data_loader import H2HDataLoader

@pytest.fixture
def mock_driver():
    return Mock(spec=WebDriver)

@pytest.fixture
def mock_selenium_utils():
    utils = Mock()
    utils.get_match_status.return_value = 'live'
    utils.wait_for_dynamic_content.return_value = True
    return utils

@pytest.fixture
def match_loader(mock_driver, mock_selenium_utils):
    return MatchDataLoader(mock_driver, selenium_utils=mock_selenium_utils)

@pytest.fixture
def odds_loader(mock_driver, mock_selenium_utils):
    return OddsDataLoader(mock_driver, selenium_utils=mock_selenium_utils)

@pytest.fixture
def h2h_loader(mock_driver, mock_selenium_utils):
    return H2HDataLoader(mock_driver, selenium_utils=mock_selenium_utils)

def test_match_loader_skips_live(match_loader):
    assert match_loader.load_match('test_id') is False

def test_odds_loader_skips_live(odds_loader):
    assert odds_loader.load_home_away_odds('test_id') is False
    assert odds_loader.load_over_under_odds('test_id') is False

def test_h2h_loader_skips_live(h2h_loader):
    assert h2h_loader.load_h2h('test_id') is False

# Repeat for 'finished' status
@pytest.fixture
def mock_selenium_utils_finished():
    utils = Mock()
    utils.get_match_status.return_value = 'finished'
    utils.wait_for_dynamic_content.return_value = True
    return utils

def test_match_loader_skips_finished(mock_driver, mock_selenium_utils_finished):
    loader = MatchDataLoader(mock_driver, selenium_utils=mock_selenium_utils_finished)
    assert loader.load_match('test_id') is False

def test_odds_loader_skips_finished(mock_driver, mock_selenium_utils_finished):
    loader = OddsDataLoader(mock_driver, selenium_utils=mock_selenium_utils_finished)
    assert loader.load_home_away_odds('test_id') is False
    assert loader.load_over_under_odds('test_id') is False

def test_h2h_loader_skips_finished(mock_driver, mock_selenium_utils_finished):
    loader = H2HDataLoader(mock_driver, selenium_utils=mock_selenium_utils_finished)
    assert loader.load_h2h('test_id') is False 