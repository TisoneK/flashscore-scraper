import pytest
from unittest.mock import Mock, patch
from src.utils.selenium_utils import SeleniumUtils

class DummyDriver:
    pass

@pytest.fixture
def selenium_utils():
    return SeleniumUtils(DummyDriver())

def make_elem(text):
    elem = Mock()
    elem.text = text
    return elem

@patch.object(SeleniumUtils, 'find')
def test_get_match_status_scheduled(mock_find, selenium_utils):
    # Simulate empty status, date in fixedScore__status
    mock_find.side_effect = [make_elem('\xa0'), make_elem('15.07.2025 11:00')]
    assert selenium_utils.get_match_status() == 'scheduled'

@patch.object(SeleniumUtils, 'find')
def test_get_match_status_live(mock_find, selenium_utils):
    # Simulate live status
    mock_find.side_effect = [make_elem('1st Quarter')]
    assert selenium_utils.get_match_status() == 'live'

@patch.object(SeleniumUtils, 'find')
def test_get_match_status_finished(mock_find, selenium_utils):
    # Simulate finished status
    mock_find.side_effect = [make_elem('FT')]
    assert selenium_utils.get_match_status() == 'finished'

@patch.object(SeleniumUtils, 'find')
def test_get_match_status_unknown(mock_find, selenium_utils):
    # Simulate no elements found
    mock_find.side_effect = [None, None]
    assert selenium_utils.get_match_status() == 'unknown' 