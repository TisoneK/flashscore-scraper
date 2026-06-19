"""Module for verifying URLs and their content."""
import logging
import re
from typing import Optional, Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.selenium_utils import SeleniumUtils

from src.core.url_builder import UrlBuilder

logger = logging.getLogger(__name__)

class URLVerifier:
    """Class for verifying URLs and their content."""
    
    def __init__(self, driver):
        """Initialize with WebDriver instance.
        
        Args:
            driver: Selenium WebDriver instance
        """
        from src.utils.selenium_utils import SeleniumUtils
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        self.selenium_utils = SeleniumUtils(driver)
    
    def verify_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Verify if a URL is valid without loading it.
        
        Args:
            url: URL to verify
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Verify the URL based on its type
            if "/summary/" in url:
                return self.verify_match_url(url)
            elif "/h2h/" in url:
                return self.verify_h2h_url(url)
            elif "/odds/home-away/" in url:
                return self.verify_home_away_odds_url(url)
            elif "/odds/over-under/" in url:
                return self.verify_over_under_odds_url(url)
            else:
                # Generic URL validation
                from urllib.parse import urlparse
                parsed = urlparse(url)
                if not all([parsed.scheme, parsed.netloc]):
                    return False, f"Invalid URL format: {url}"
                return True, None
                
        except Exception as e:
            error_msg = f"Error verifying URL {url}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def load_and_verify_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Load a URL and verify its content.
        
        Args:
            url: URL to load and verify
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Load the URL and wait for page load
            self.selenium_utils.navigate_to(url)
            
            # Hide common banners
            self.selenium_utils.hide_common_banners()
            
            # Verify the URL based on its type
            if "/summary/" in url:
                return self.verify_match_url(url)
            elif "/h2h/" in url:
                return self.verify_h2h_url(url)
            elif "/odds/home-away/" in url:
                return self.verify_home_away_odds_url(url)
            elif "/odds/over-under/" in url:
                return self.verify_over_under_odds_url(url)
            else:
                return True, None
                
        except Exception as e:
            error_msg = f"Error loading URL {url}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _extract_url_components(self, url: str) -> Dict[str, str]:
        """Extract components from a Flashscore URL.
        
        Args:
            url: URL to parse
            
        Returns:
            Dict containing URL components or empty dict if invalid
        """
        # Pattern for the canonical URL structure
        pattern = (
            r"https?://www\.flashscore\.co\.ke/match/basketball/"
            r"(?P<home_slug>[a-z0-9-]+)-(?P<home_id>[a-zA-Z0-9]+)/"
            r"(?P<away_slug>[a-z0-9-]+)-(?P<away_id>[a-zA-Z0-9]+)/"
            r"(?P<path>summary|odds/home-away/ft-including-ot|odds/over-under/ft-including-ot|h2h/overall)/"
            r"\?mid=(?P<mid>[a-zA-Z0-9]+)"
        )
        
        match = re.search(pattern, url)
        if match:
            return match.groupdict()
        return {}
    
    def verify_home_away_odds_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Verify if a home/away odds URL is valid.
        
        Args:
            url: URL to verify
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            components = self._extract_url_components(url)
            if not components:
                return False, "Invalid URL format"
                
            if components['path'] != 'odds/home-away/ft-including-ot':
                return False, "Not a home/away odds URL"
                
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error verifying home/away odds URL: {e}")
            return False, str(e)

    def verify_over_under_odds_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Verify if an over/under odds URL is valid.
        
        Args:
            url: URL to verify
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            components = self._extract_url_components(url)
            if not components:
                return False, "Invalid URL format"
                
            if components['path'] != 'odds/over-under/ft-including-ot':
                return False, "Not an over/under odds URL"
                
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error verifying over/under odds URL: {e}")
            return False, str(e)
    
    def verify_match_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Verify if a match URL is valid.
        
        Args:
            url: URL to verify
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            components = self._extract_url_components(url)
            if not components:
                return False, "Invalid URL format"
                
            if components['path'] != 'summary':
                return False, "Not a match summary URL"
                
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error verifying match URL: {e}")
            return False, str(e)
    
    def verify_h2h_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Verify if an H2H URL is valid.
        
        Args:
            url: URL to verify
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            components = self._extract_url_components(url)
            if not components:
                return False, "Invalid URL format"
                
            if components['path'] != 'h2h/overall':
                return False, "Not an H2H URL"
                
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error verifying H2H URL: {e}")
            return False, str(e) 