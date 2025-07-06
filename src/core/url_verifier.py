"""Module for verifying URLs and their content."""
import logging
from typing import Optional, Tuple

from ..config import CONFIG, SELECTORS
from ..utils import SeleniumUtils

logger = logging.getLogger(__name__)

class URLVerifier:
    """Class for verifying URLs and their content."""
    
    def __init__(self, driver):
        """Initialize with WebDriver instance.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        self.selenium_utils = SeleniumUtils(driver)
    
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
            if "match-summary" in url:
                return self.verify_match_url(url)
            elif "h2h" in url:
                return self.verify_h2h_url(url)
            elif "odds-comparison/home-away" in url:
                return self.verify_home_away_odds_url(url)
            elif "odds-comparison/over-under" in url:
                return self.verify_over_under_odds_url(url)
            else:
                return True, None
                
        except Exception as e:
            error_msg = f"Error loading URL {url}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def verify_home_away_odds_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Verify if a home/away odds URL is valid.
        
        Args:
            url: URL to verify
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Check URL format
            if not url.endswith("/odds-comparison/home-away/ft-including-ot"):
                return False, "Invalid home/away odds URL format"
            
            # Check if URL contains /basketball/
            if "/basketball/" not in url:
                return False, "Missing /basketball/ in URL"
            
            # Extract match ID
            match_id = url.split("/match/basketball/")[1].split("/#")[0]
            if not match_id or not match_id.isalnum():
                return False, "Invalid match ID in URL"
            
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
            # Check URL format
            if not url.endswith("/odds-comparison/over-under/ft-including-ot"):
                return False, "Invalid over/under odds URL format"
            
            # Check if URL contains /basketball/
            if "/basketball/" not in url:
                return False, "Missing /basketball/ in URL"
            
            # Extract match ID
            match_id = url.split("/match/basketball/")[1].split("/#")[0]
            if not match_id or not match_id.isalnum():
                return False, "Invalid match ID in URL"
            
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
            # Check URL format
            if not url.endswith("/match-summary"):
                return False, "Invalid match URL format"
            
            # Check if URL contains /basketball/
            if "/basketball/" not in url:
                return False, "Missing /basketball/ in URL"
            
            # Extract match ID
            match_id = url.split("/match/basketball/")[1].split("/#")[0]
            if not match_id or not match_id.isalnum():
                return False, "Invalid match ID in URL"
            
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
            # Get current URL after navigation
            current_url = self.driver.current_url
            self.logger.debug(f"Verifying H2H URL - Expected: {url}, Current: {current_url}")
            
            # Check if URL contains required patterns
            if "/basketball/" not in current_url:
                return False, "Not a basketball match URL"
                
            if "/h2h/overall" not in current_url:
                return False, "Not an H2H page"
                
            # Extract match ID from URL
            try:
                match_id = current_url.split("/match/basketball/")[1].split("/#")[0]
                if not match_id or not match_id.isalnum():
                    return False, "Invalid match ID in URL"
            except IndexError:
                return False, "Invalid URL format"
                
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error verifying H2H URL: {e}")
            return False, str(e) 