"""
URL Builder for Flashscore match URLs.

This module provides a UrlBuilder class for generating Flashscore URLs 
with the canonical Flashscore structure. Minimal `?mid=...` URLs are not used.
"""

from urllib.parse import urlparse, parse_qs
from typing import Dict, Optional, TypedDict, Literal, overload, Union
import re
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)


class MatchData(TypedDict, total=False):
    """Type definition for match data used in URL building."""
    mid: str
    home_slug: str
    home_id: str
    away_slug: str
    away_id: str


UrlType = Literal[
    "summary",
    "home_away_odds",
    "over_under_odds",
    "h2h",
]


class UrlBuilder:
    """
    Builder for Flashscore match URLs with the canonical URL structure.
    
    Canonical URL structure pattern:
    https://www.flashscore.co.ke/match/basketball/{home_slug}-{home_id}/{away_slug}-{away_id}/{path}/?mid={mid}
    
    Where {path} can be:
    - summary/
    - odds/home-away/ft-including-ot/
    - odds/over-under/ft-including-ot/
    - h2h/overall/
    """

    BASE_DOMAIN = "https://www.flashscore.co.ke/match"
    VALID_ID = re.compile(r"^[A-Za-z0-9]+$")
    VALID_SLUG = re.compile(r"^[a-z0-9-]+$")

    def __init__(
        self,
        mid: str,
        home_slug: str,
        home_id: str,
        away_slug: str,
        away_id: str,
    ):
        self.mid = mid
        self.home_slug = home_slug
        self.home_id = home_id
        self.away_slug = away_slug
        self.away_id = away_id

    # ---------- Parsing ----------
    @classmethod
    def parse_summary_url(cls, url: str) -> MatchData:
        """Parse a Flashscore summary URL into its components."""
        parsed = urlparse(url)
        if not parsed.netloc or "flashscore" not in parsed.netloc:
            raise ValueError("Not a Flashscore URL")

        params = parse_qs(parsed.query)
        mid = params.get("mid", [""])[0]
        if not mid:
            raise ValueError("Missing match ID in URL")

        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        # Accept canonical forms with at least 4 parts:
        # /match/basketball/{home_slug}-{home_id}/{away_slug}-{away_id}/...
        if len(path_parts) < 4 or path_parts[0] != "match" or path_parts[1] != "basketball":
            raise ValueError("Malformed Flashscore match URL")

        # home and away parts are expected to be the 3rd and 4th segments
        try:
            home_part = path_parts[2]
            away_part = path_parts[3]
        except IndexError:
            raise ValueError("Malformed Flashscore match URL")

        # Split slug and id using the last hyphen; validate presence
        try:
            home_slug, home_id = home_part.rsplit("-", 1)
            away_slug, away_id = away_part.rsplit("-", 1)
        except ValueError:
            raise ValueError("Malformed Flashscore match URL")

        return {
            "mid": mid,
            "home_slug": home_slug,
            "home_id": home_id,
            "away_slug": away_slug,
            "away_id": away_id,
        }

    @classmethod
    def from_element(cls, element: WebElement) -> "UrlBuilder":
        """Create a UrlBuilder instance directly from a match element.
        
        Args:
            element: Selenium WebElement containing the match data
            
        Returns:
            UrlBuilder: Configured with data from the match element
            
        Raises:
            ValueError: If the element doesn't contain a valid match URL
        """
        # Try multiple selectors for the anchor tag - updated for current Flashscore structure
        anchor_selectors = [
            'a.eventRowLink',
            'a[href*="/match/"]',
            'a[href*="flashscore"]',
            'a[href*="basketball"]',
            'a',
            'div[onclick]',  # Sometimes matches are clickable divs
            '[data-testid*="match"]'  # Data testid approach
        ]
        
        anchor = None
        url = None
        
        for selector in anchor_selectors:
            try:
                anchor = element.find_element(By.CSS_SELECTOR, selector)
                url = anchor.get_attribute('href')
                if url and 'flashscore' in url and '/match/' in url:
                    break
                # Also check onclick for div elements
                onclick = anchor.get_attribute('onclick')
                if onclick and 'flashscore' in onclick and '/match/' in onclick:
                    # Extract URL from onclick
                    import re
                    url_match = re.search(r'https://[^\'"]+', onclick)
                    if url_match:
                        url = url_match.group()
                        break
            except Exception as e:
                # Log selector failures only if verbose URL builder debug is enabled
                try:
                    from src.utils.config_loader import CONFIG
                    if CONFIG.get('logging', {}).get('verbose_url_builder_debug', False):
                        logger.debug(f"Selector '{selector}' failed: {e}")
                except Exception:
                    pass
                continue
        
        if not anchor or not url:
            # Optionally log detailed diagnostics if verbose URL builder debug is enabled
            try:
                from src.utils.config_loader import CONFIG
                if CONFIG.get('logging', {}).get('verbose_url_builder_debug', False):
                    all_anchors = element.find_elements(By.TAG_NAME, 'a')
                    logger.debug(f"Found {len(all_anchors)} anchor elements in match element")
                    for i, a in enumerate(all_anchors):
                        href = a.get_attribute('href')
                        onclick = a.get_attribute('onclick')
                        logger.debug(f"  Anchor {i}: href='{href}', onclick='{onclick}', class='{a.get_attribute('class')}'")
                    # Also check for clickable divs
                    all_divs = element.find_elements(By.TAG_NAME, 'div')
                    clickable_divs = [d for d in all_divs if d.get_attribute('onclick')]
                    logger.debug(f"Found {len(clickable_divs)} clickable div elements")
                    for i, d in enumerate(clickable_divs):
                        onclick = d.get_attribute('onclick')
                        logger.debug(f"  Div {i}: onclick='{onclick}', class='{d.get_attribute('class')}'")
            except Exception:
                pass
            raise ValueError("No valid anchor element found in match element")
        
        if not url:
            raise ValueError("No URL found in anchor element")
        
        if 'flashscore' not in url or '/match/' not in url:
            raise ValueError(f"Invalid match URL: {url}")
        
        try:
            return cls.from_summary_url(url)
        except Exception as e:
            raise ValueError(f"Failed to parse URL from match element: {e}")
            
    @classmethod
    def from_summary_url(cls, summary_url: str) -> "UrlBuilder":
        """Create a UrlBuilder instance from a canonical summary URL."""
        data = cls.parse_summary_url(summary_url)
        return cls(
            mid=data["mid"],
            home_slug=data["home_slug"],
            home_id=data["home_id"],
            away_slug=data["away_slug"],
            away_id=data["away_id"],
        )

    @classmethod
    def from_match_urls(cls, urls: Dict[str, str]) -> "UrlBuilder":
        """Create a UrlBuilder from a MatchUrls-like dict using its summary URL.

        Expects a mapping with key 'summary'. This avoids importing the TypedDict
        to keep modules decoupled.
        """
        summary_url = urls.get("summary")
        if not summary_url:
            raise ValueError("'summary' URL missing from urls mapping")
        return cls.from_summary_url(summary_url)

    # ---------- Validation ----------
    @classmethod
    def _validate_id(cls, value: str, field: str) -> None:
        if not cls.VALID_ID.match(value):
            raise ValueError(f"Invalid {field}: {value} (must be alphanumeric)")

    @classmethod
    def _validate_slug(cls, value: str, field: str) -> None:
        if not cls.VALID_SLUG.match(value):
            raise ValueError(
                f"Invalid {field}: {value} (must be lowercase letters, numbers, or hyphens)"
            )

    def _validate(self) -> None:
        self._validate_id(self.mid, "mid")
        self._validate_slug(self.home_slug, "home_slug")
        self._validate_id(self.home_id, "home_id")
        self._validate_slug(self.away_slug, "away_slug")
        self._validate_id(self.away_id, "away_id")

    # ---------- Core builders ----------
    def _base_url(self) -> str:
        return (
            f"{self.BASE_DOMAIN}/basketball/"
            f"{self.home_slug}-{self.home_id}/{self.away_slug}-{self.away_id}"
        )

    def _build_url(self, path: str) -> str:
        self._validate()
        return f"{self._base_url()}/{path}?mid={self.mid}"

    def summary(self) -> str:
        return self._build_url("summary/")

    def home_away_odds(self) -> str:
        return self._build_url("odds/home-away/ft-including-ot/")

    def over_under_odds(self) -> str:
        return self._build_url("odds/over-under/ft-including-ot/")

    def h2h(self) -> str:
        return self._build_url("h2h/overall/")

    def get_urls(self) -> Dict[str, str]:
        return {
            "summary": self.summary(),
            "home_away_odds": self.home_away_odds(),
            "over_under_odds": self.over_under_odds(),
            "h2h": self.h2h(),
        }

    @overload
    def get(self, url_type: Literal["summary"]) -> str: ...
    @overload
    def get(self, url_type: Literal["home_away_odds"]) -> str: ...
    @overload
    def get(self, url_type: Literal["over_under_odds"]) -> str: ...
    @overload
    def get(self, url_type: Literal["h2h"]) -> str: ...
    
    @overload
    @classmethod
    def from_match_element(cls, element: WebElement) -> Dict[str, str]:
        """Create a dictionary of URLs directly from a match element.
        
        This is a convenience method that combines from_element() and get_urls().
        
        Args:
            element: Selenium WebElement containing the match data
            
        Returns:
            Dict[str, str]: Dictionary of URLs with keys: summary, home_away_odds, 
                          over_under_odds, h2h
            
        Example:
            # Given a match element
            urls = UrlBuilder.from_match_element(match_element)
            summary_url = urls['summary']
            odds_url = urls['home_away_odds']
        """
        ...

    def get(self, url_type: UrlType) -> str:
        urls = self.get_urls()
        if url_type not in urls:
            raise ValueError(f"Unknown URL type: {url_type}")
        return urls[url_type]
        
    @classmethod
    def from_match_element(cls, element: WebElement) -> Dict[str, str]:
        """Create a dictionary of URLs directly from a match element.
        
        This is a convenience method that combines from_element() and get_urls().
        
        Args:
            element: Selenium WebElement containing the match data
            
        Returns:
            Dict[str, str]: Dictionary of URLs with keys: summary, home_away_odds, 
                          over_under_odds, h2h
        """
        return cls.from_element(element).get_urls()
