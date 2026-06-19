from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

from .base_verifier import BaseVerifier
from src.core.url_verifier import URLVerifier
from src.core.url_builder import UrlBuilder

class OddsDataVerifier(BaseVerifier):
    def __init__(self, driver):
        self.url_verifier = URLVerifier(driver)
        self.driver = driver

    def verify(self, data, status_callback=None):
        required_fields = ['match_total', 'over_odds', 'under_odds', 'all_totals']
        optional_fields = ['home_odds', 'away_odds']
        if isinstance(data, str):
            method = getattr(self, f'verify_{data}', None)
            if method:
                return method(None, status_callback)
            else:
                return False, f"No verifier for field: {data}"
        for field in required_fields:
            if status_callback:
                status_callback(f"Verifying {field}...")
            method = getattr(self, f'verify_{field}', None)
            if method:
                is_valid, error = method(getattr(data, field, None), status_callback)
                if not is_valid:
                    return False, f"{field}: {error}"
            else:
                value = getattr(data, field, None)
                if value is None:
                    return False, f"Missing field: {field}"
        # Optional fields: do not fail if missing
        if status_callback:
            status_callback("Odds data verification completed.")
        return True, ""

    def verify_home_odds(self, value, status_callback=None):
        # Optional: just warn, do not fail
        return True, ""

    def verify_away_odds(self, value, status_callback=None):
        # Optional: just warn, do not fail
        return True, ""

    def verify_match_total(self, value, status_callback=None):
        if value is None:
            return False, "Missing match_total - over/under odds unavailable"
        return True, ""

    def verify_over_odds(self, value, status_callback=None):
        if value is None:
            return False, "Missing over_odds - over/under odds unavailable"
        return True, ""

    def verify_under_odds(self, value, status_callback=None):
        if value is None:
            return False, "Missing under_odds - over/under odds unavailable"
        return True, ""

    def verify_all_totals(self, value, status_callback=None):
        if value is None:
            return False, "Missing all_totals list"
        return True, ""

    def verify_url(self, url: str, odds_type: str = 'home_away_odds', status_callback=None) -> tuple[bool, str]:
        """Verify if the given odds URL is valid and accessible.
        
        Args:
            url: The odds URL to verify
            odds_type: Type of odds ('home_away_odds' or 'over_under_odds')
            status_callback: Optional callback for status updates
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "Missing or invalid URL"
            
        try:
            # First verify the URL format using UrlBuilder
            try:
                if '/odds/' in url or odds_type in ['home_away_odds', 'over_under_odds']:
                    # For odds URLs, convert to summary URL first
                    summary_url = url.replace('/odds/', '/summary/')
                    builder = UrlBuilder.from_summary_url(summary_url)
                    urls = builder.get_urls()
                    
                    # Get the appropriate odds URL based on type
                    if not odds_type or odds_type not in urls:
                        # Try to determine the odds type from URL if not specified
                        if '/home-away/' in url:
                            odds_type = 'home_away_odds'
                        elif '/over-under/' in url:
                            odds_type = 'over_under_odds'
                        else:
                            odds_type = 'home_away_odds'  # Default fallback
                    
                    if odds_type not in urls:
                        return False, f"Cannot determine odds URL type for: {url}"
                        
                    odds_url = urls[odds_type]
                    if status_callback:
                        status_callback(f"Resolved {odds_type} URL: {odds_url}")
                else:
                    # Generic URL validation
                    result = urlparse(url)
                    if not all([result.scheme, result.netloc]):
                        return False, f"Invalid URL format: {url}"
                    odds_url = url
            except ValueError as e:
                return False, f"Invalid odds URL format: {str(e)}"
            
            # Then check if it's accessible
            if status_callback:
                status_callback(f"Verifying {odds_type} URL: {odds_url}")
                
            success, error = self.url_verifier.verify_url(odds_url)
            if not success:
                return False, f"{odds_type} URL verification failed: {error}"
                
            return True, ""
            
        except Exception as e:
            return False, f"Error verifying {odds_type} URL: {str(e)}"