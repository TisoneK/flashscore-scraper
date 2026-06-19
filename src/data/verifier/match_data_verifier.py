from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

from .base_verifier import BaseVerifier
from src.core.url_verifier import URLVerifier
from src.core.url_builder import UrlBuilder

class MatchDataVerifier(BaseVerifier):
    def __init__(self, driver):
        self.url_verifier = URLVerifier(driver)
        self.driver = driver

    def verify(self, data, status_callback=None):
        required_fields = ['country', 'league', 'home_team', 'away_team', 'date', 'time', 'match_id']
        # If data is a string, treat as field name for field-specific validation
        if isinstance(data, str):
            method = getattr(self, f'verify_{data}', None)
            if method:
                return method(None, status_callback)
            else:
                return False, f"No verifier for field: {data}"
        # Otherwise, validate all required fields
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
        if status_callback:
            status_callback("Match data verification completed.")
        return True, ""

    def verify_country(self, value, status_callback=None):
        if value is None:
            return False, "Missing country element"
        return True, ""

    def verify_league(self, value, status_callback=None):
        if value is None:
            return False, "Missing league element"
        return True, ""

    def verify_home_team(self, value, status_callback=None):
        if value is None:
            return False, "Missing home_team element"
        return True, ""

    def verify_away_team(self, value, status_callback=None):
        if value is None:
            return False, "Missing away_team element"
        return True, ""

    def verify_date(self, value, status_callback=None):
        if value is None:
            return False, "Missing date element"
        return True, ""

    def verify_time(self, value, status_callback=None):
        if value is None:
            return False, "Missing time element"
        return True, ""

    def verify_match_id(self, value, status_callback=None):
        if value is None:
            return False, "Missing match_id"
        if not isinstance(value, str) or not value:
            return False, "Invalid match_id"
        
        # If the value is a URL, validate its format
        if value.startswith(('http://', 'https://')):
            try:
                # Try to parse as a match element URL
                builder = UrlBuilder.from_summary_url(value)
                # If we get here, the URL is valid
                return True, ""
            except ValueError as e:
                return False, f"Invalid match URL: {value} ({str(e)})"
        
        # If it's not a URL, it should be a valid match ID
        # Basic validation for match ID format (adjust as needed)
        if not value.strip():
            return False, "Empty match ID"
            
        return True, ""
        
    def verify_url(self, url: str, url_type: Optional[str] = None, status_callback=None) -> tuple[bool, str]:
        """Verify if the given URL is valid and accessible.
        
        Args:
            url: The URL to verify
            url_type: Optional URL type ('summary', 'h2h', 'odds', etc.)
            status_callback: Optional callback for status updates
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "Missing or invalid URL"
            
        try:
            # First verify the URL format using UrlBuilder
            try:
                if url_type == 'summary' or '/match/' in url or '/summary/' in url:
                    # For summary URLs, parse with from_summary_url
                    builder = UrlBuilder.from_summary_url(url)
                    urls = builder.get_urls()
                    # If we need to verify a specific URL type
                    if url_type and url_type in urls:
                        url = urls[url_type]
                elif url_type == 'h2h' or '/h2h/' in url:
                    # For H2H URLs, convert to summary URL first
                    summary_url = url.replace('/h2h/', '/summary/')
                    builder = UrlBuilder.from_summary_url(summary_url)
                    url = builder.h2h()
                elif url_type in ['home_away_odds', 'over_under_odds'] or '/odds/' in url:
                    # For odds URLs, convert to summary URL first
                    summary_url = url.replace('/odds/', '/summary/')
                    builder = UrlBuilder.from_summary_url(summary_url)
                    urls = builder.get_urls()
                    if url_type not in urls:
                        return False, f"Unknown odds URL type: {url_type}"
                    url = urls[url_type]
                else:
                    # Generic URL validation
                    result = urlparse(url)
                    if not all([result.scheme, result.netloc]):
                        return False, f"Invalid URL format: {url}"
            except ValueError as e:
                return False, f"Invalid URL format for type {url_type}: {str(e)}"
            
            # Then check if it's accessible
            if status_callback:
                status_callback(f"Verifying URL: {url}")
                
            success, error = self.url_verifier.verify_url(url)
            if not success:
                return False, f"URL verification failed: {error}"
                
            return True, ""
            
        except Exception as e:
            return False, f"Error verifying URL: {str(e)}"