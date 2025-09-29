from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

from .base_verifier import BaseVerifier
from src.core.url_verifier import URLVerifier
from src.core.url_builder import UrlBuilder
from src.utils.config_loader import MIN_H2H_MATCHES

class H2HDataVerifier(BaseVerifier):
    def __init__(self, driver):
        self.url_verifier = URLVerifier(driver)
        self.driver = driver

    def verify(self, data, status_callback=None):
        required_fields = ['h2h_section', 'h2h_rows', 'h2h_row_count']
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
        if status_callback:
            status_callback("H2H data verification completed.")
        return True, ""

    def verify_h2h_section(self, value, status_callback=None):
        if value is None:
            return False, "Missing h2h_section element"
        return True, ""

    def verify_h2h_rows(self, value, status_callback=None):
        if not value or len(value) < MIN_H2H_MATCHES:
            return False, f"Insufficient H2H matches: {len(value) if value else 0} found, {MIN_H2H_MATCHES} required"
        return True, ""

    def verify_h2h_row_count(self, value, status_callback=None):
        if value is None or value < MIN_H2H_MATCHES:
            return False, f"Insufficient h2h_row_count (minimum {MIN_H2H_MATCHES} required)"
        return True, ""

    def verify_url(self, url: str, status_callback=None) -> tuple[bool, str]:
        """Verify if the given H2H URL is valid and accessible.
        
        Args:
            url: The H2H URL to verify
            status_callback: Optional callback for status updates
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "Missing or invalid URL"
            
        try:
            # First verify the URL format using UrlBuilder
            try:
                if '/h2h/' in url:
                    # For H2H URLs, convert to summary URL first
                    summary_url = url.replace('/h2h/', '/summary/')
                    builder = UrlBuilder.from_summary_url(summary_url)
                    h2h_url = builder.h2h()
                    if status_callback:
                        status_callback(f"Resolved H2H URL: {h2h_url}")
                else:
                    # Generic URL validation
                    result = urlparse(url)
                    if not all([result.scheme, result.netloc]):
                        return False, f"Invalid URL format: {url}"
                    h2h_url = url
            except ValueError as e:
                return False, f"Invalid H2H URL format: {str(e)}"
            
            # Then check if it's accessible
            if status_callback:
                status_callback(f"Verifying H2H URL: {h2h_url}")
                
            success, error = self.url_verifier.verify_url(h2h_url)
            if not success:
                return False, f"H2H URL verification failed: {error}"
                
            return True, ""
            
        except Exception as e:
            return False, f"Error verifying H2H URL: {str(e)}"