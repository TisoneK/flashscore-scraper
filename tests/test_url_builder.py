"""
Tests for the UrlBuilder class using canonical Flashscore URLs.
"""
import pytest
from src.core.url_builder import UrlBuilder


def test_parse_summary_url_components():
    url = "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/summary/?mid=raxc7DVh"
    result = UrlBuilder.parse_summary_url(url)
    assert result == {
        'mid': 'raxc7DVh',
        'home_slug': 'instituto-de-cordoba',
        'home_id': 'rJPlbMMq',
        'away_slug': 'olimpico',
        'away_id': 'ERbTiFhJ',
    }


def test_builder_from_summary_url_and_get_urls():
    summary = "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/summary/?mid=raxc7DVh"
    b = UrlBuilder.from_summary_url(summary)
    urls = b.get_urls()
    assert urls == {
        'summary': "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/summary/?mid=raxc7DVh",
        'home_away_odds': "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/odds/home-away/ft-including-ot/?mid=raxc7DVh",
        'over_under_odds': "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/odds/over-under/ft-including-ot/?mid=raxc7DVh",
        'h2h': "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/h2h/overall/?mid=raxc7DVh",
    }


def test_builder_get_methods():
    b = UrlBuilder(
        mid="raxc7DVh",
        home_slug="instituto-de-cordoba",
        home_id="rJPlbMMq",
        away_slug="olimpico",
        away_id="ERbTiFhJ",
    )
    assert b.summary() == "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/summary/?mid=raxc7DVh"
    assert b.home_away_odds() == "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/odds/home-away/ft-including-ot/?mid=raxc7DVh"
    assert b.over_under_odds() == "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/odds/over-under/ft-including-ot/?mid=raxc7DVh"
    assert b.h2h() == "https://www.flashscore.co.ke/match/basketball/instituto-de-cordoba-rJPlbMMq/olimpico-ERbTiFhJ/h2h/overall/?mid=raxc7DVh"


def test_parse_summary_url_invalid_domain():
    with pytest.raises(ValueError, match="Not a Flashscore URL"):
        UrlBuilder.parse_summary_url("https://example.com/match/basketball/x-y/a-b/summary/?mid=XYZ")


def test_parse_summary_url_missing_mid():
    with pytest.raises(ValueError, match="Missing match ID"):
        UrlBuilder.parse_summary_url("https://www.flashscore.co.ke/match/basketball/x-y/a-b/summary/")
