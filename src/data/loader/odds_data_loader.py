from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from src.data.elements_model import OddsElements
from src.utils.config_loader import CONFIG, SELECTORS
from src.core.url_verifier import URLVerifier
from src.core.url_builder import UrlBuilder
from src.core.network_monitor import NetworkMonitor
from src.core.retry_manager import NetworkRetryManager
from selenium.webdriver.remote.webdriver import WebDriver
from src.data.verifier.odds_data_verifier import OddsDataVerifier
import logging
from src.core.exceptions import DataNotFoundError, DataParseError, DataValidationError, DataUnavailableWarning
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class OddsDataLoader:
    def __init__(self, driver: WebDriver, selenium_utils=None):
        self.driver = driver
        self.elements = OddsElements()
        self.selenium_utils = selenium_utils
        self.url_verifier = URLVerifier(driver)
        self.odds_data_verifier = OddsDataVerifier(driver)
        
        # Network resilience components
        self.network_monitor = NetworkMonitor()
        self.retry_manager = NetworkRetryManager()
        
        # Start network monitoring
        # self.network_monitor.start_monitoring()

    def __del__(self):
        """Cleanup network monitoring on destruction."""
        if hasattr(self, 'network_monitor'):
            try:
                self.network_monitor.stop_monitoring()
            except Exception:
                pass

    def get_home_odds(self):
        return self._safe_find_element('css', SELECTORS['odds']['table']['home_away']['odds']['home']['cell'])

    def get_away_odds(self):
        return self._safe_find_element('css', SELECTORS['odds']['table']['home_away']['odds']['away']['cell'])

    def get_match_total(self, all_totals):
        """Get the selected/active total line, with fallback to first available."""
        if not all_totals:
            return None
        
        # First, try to find a selected/highlighted total
        # In Flashscore, the selected total is indicated by the parent container having 'wclOddsCell--empty' class
        for total_data in all_totals:
            alternative = total_data.get('alternative')
            if alternative and hasattr(alternative, 'get_attribute'):
                # Check if the parent container has the 'wclOddsCell--empty' class (indicates selected)
                try:
                    parent = alternative.find_element('xpath', '..')
                    parent_classes = parent.get_attribute('class') or ''
                    if 'wclOddsCell--empty' in parent_classes:
                        logger.debug(f"Found selected total line: {alternative.text}")
                        return alternative
                except:
                    # If we can't check parent, continue to next
                    pass
                
                # Also check for other common "selected" indicators
                classes = alternative.get_attribute('class') or ''
                if any(indicator in classes.lower() for indicator in ['selected', 'active', 'highlighted', 'current']):
                    logger.debug(f"Found selected total line (by class): {alternative.text}")
                    return alternative
        
        # Fallback to first available total (no log here; we'll log only when final selection is known)
        if all_totals:
            return all_totals[0]['alternative']
        
        return None

    def get_over_odds(self, all_totals, selected_total=None):
        """Get over odds for the selected total line."""
        if not all_totals:
            return None
        
        # Find the selected total and get its over odds
        selected_total = selected_total or self.get_match_total(all_totals)
        if selected_total:
            # Find the corresponding over odds for the selected total
            for total_data in all_totals:
                if total_data.get('alternative') == selected_total:
                    return total_data.get('over')
        
        # Fallback to first available
        return all_totals[0]['over'] if all_totals else None

    def get_under_odds(self, all_totals, selected_total=None):
        """Get under odds for the selected total line."""
        if not all_totals:
            return None
        
        # Find the selected total and get its under odds
        selected_total = selected_total or self.get_match_total(all_totals)
        if selected_total:
            # Find the corresponding under odds for the selected total
            for total_data in all_totals:
                if total_data.get('alternative') == selected_total:
                    return total_data.get('under')
        
        # Fallback to first available
        return all_totals[0]['under'] if all_totals else None

    def get_all_totals(self):
        """Get all totals with network resilience."""
        def _extraction_operation():
            if not self.selenium_utils:
                return []
            
            # Get all total values (the numbers like 149.5, 150.5, etc.)
            total_elements = self.selenium_utils.find_all('css', SELECTORS['odds']['table']['over_under']['odds']['total']['cell'])
            
            # Get all over odds (first link in each row)
            over_elements = self.selenium_utils.find_all('css', SELECTORS['odds']['table']['over_under']['odds']['over']['cell'])
            
            # Get all under odds (second link in each row)
            under_elements = self.selenium_utils.find_all('css', SELECTORS['odds']['table']['over_under']['odds']['under']['cell'])
            
            all_totals = []
            
            # Match totals with their corresponding over/under odds
            # Each row should have one total and two odds (over/under)
            min_length = min(len(total_elements), len(over_elements), len(under_elements))
            
            for i in range(min_length):
                total_elem = total_elements[i] if i < len(total_elements) else None
                over_elem = over_elements[i] if i < len(over_elements) else None
                under_elem = under_elements[i] if i < len(under_elements) else None
                
                all_totals.append({
                    'alternative': total_elem,
                    'over': over_elem,
                    'under': under_elem
                })
            
            logger.debug(f"Extracted {len(all_totals)} total lines with over/under odds")
            return all_totals

        try:
            return self.retry_manager.retry_network_operation(_extraction_operation)
        except Exception as e:
            logger.warning(f"Failed to extract all totals: {e}")
            return []

    def select_total_line(self, total_element):
        """Click on a total line to select it."""
        if not total_element or not hasattr(total_element, 'click'):
            return False
        
        try:
            # Click on the total element to select it
            total_element.click()
            logger.debug(f"Clicked on total line: {total_element.text}")
            return True
        except Exception as e:
            logger.warning(f"Failed to click on total line: {e}")
            return False

    def load_home_away_odds(
        self, 
        url_builder: UrlBuilder,
        status_callback=None
    ) -> bool:
        """Load home/away odds with network resilience and fail-safe for missing odds tab.
        
        Args:
            url_builder: A UrlBuilder instance containing the match URL
            status_callback: Optional callback for status updates
                
        Returns:
            bool: True if home/away odds were loaded successfully, False otherwise
        """
        match_id = url_builder.mid
        logger.info(f"[OddsDataLoader] Starting to load home/away odds for match {match_id}")
        if status_callback:
            status_callback(f"Loading home/away odds for match {match_id}...")
            
        def _load_operation():
            # Get the home/away odds URL from the builder
            url = url_builder.get('home_away_odds')
            logger.debug(f"Using home/away odds URL: {url}")
            
            # Verify the URL using the odds data verifier
            is_valid, error = self.odds_data_verifier.verify_url(url, 'home_away_odds', status_callback)
            if not is_valid:
                error_msg = f"Invalid home/away odds URL: {error}"
                logger.error(error_msg)
                if status_callback:
                    status_callback(error_msg)
                return False
            
            # Load and verify the URL
            if status_callback:
                status_callback(f"Loading home/away odds page for match {match_id}...")
            
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                error_msg = f"Error loading home/away odds page for {match_id}: {error}"
                logger.error(f"[OddsDataLoader] {error_msg}")
                if status_callback:
                    status_callback(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"[OddsDataLoader] Successfully loaded home/away odds for {match_id}")
            if status_callback:
                status_callback(f"Successfully loaded home/away odds for {match_id}")
            
            if self.selenium_utils:
                # Wait for dynamic content to load
                timeout_config = CONFIG.get('timeout', {})
                dynamic_timeout = timeout_config.get('dynamic_content_timeout', 30)
                self.selenium_utils.wait_for_dynamic_content(dynamic_timeout)
                
                # For scheduled matches, we don't need to check status - we know they are scheduled
                
                # Check for required tabs
                if not self.selenium_utils.check_tab_present('Odds'):
                    error_msg = f"No odds available for match {match_id}."
                    logger.warning(f"[OddsDataLoader] {error_msg}")
                    if status_callback:
                        status_callback(error_msg)
                    return False
                    
                if not self.selenium_utils.check_tab_present('Home/Away'):
                    error_msg = f"No Home/Away odds available for match {match_id}."
                    logger.warning(f"[OddsDataLoader] {error_msg}")
                    if status_callback:
                        status_callback(error_msg)
                    return False
            
            # Extract odds data
            logger.info(f"[OddsDataLoader] Extracting home/away odds for match {match_id}")
            self.elements.home_odds = self.get_home_odds()
            self.elements.away_odds = self.get_away_odds()
            
            logger.info(f"[OddsDataLoader] Successfully extracted odds for match {match_id}")
            return True
            
        try:
            logger.info(f"[OddsDataLoader] Starting odds loading process for match {match_id}")
            result = self.retry_manager.retry_network_operation(
                _load_operation
            )
            
            if result and status_callback:
                status_callback(f"Successfully loaded home/away odds for match {match_id}.")
                
            return result
            
        except Exception as e:
            error_msg = f"Failed to load home/away odds for match {match_id}: {str(e)}"
            logger.error(f"[OddsDataLoader] {error_msg}", exc_info=True)
            if status_callback:
                status_callback(error_msg)
            return False

    def load_over_under_odds(
        self, 
        url_builder: UrlBuilder,
        status_callback=None
    ) -> bool:
        """Load over/under odds with network resilience and fail-safe for missing odds tab.
        
        Args:
            url_builder: A UrlBuilder instance containing the match URL
            status_callback: Optional callback for status updates
                
        Returns:
            bool: True if over/under odds were loaded successfully, False otherwise
        """
        match_id = url_builder.mid
        logger.info(f"[OddsDataLoader] Starting to load over/under odds for match {match_id}")
        if status_callback:
            status_callback(f"Loading over/under odds for match {match_id}...")
            
        def _load_operation():
            # Get the over/under odds URL from the builder
            url = url_builder.get('over_under_odds')
            logger.debug(f"Using over/under odds URL: {url}")
            
            # Verify the URL using the odds data verifier
            is_valid, error = self.odds_data_verifier.verify_url(url, 'over_under_odds', status_callback)
            if not is_valid:
                error_msg = f"Invalid over/under odds URL: {error}"
                logger.error(error_msg)
                if status_callback:
                    status_callback(error_msg)
                return False
            
            # Load and verify the URL
            if status_callback:
                status_callback(f"Loading over/under odds page for match {match_id}...")
            
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                error_msg = f"Error loading over/under odds page for {match_id}: {error}"
                logger.error(f"[OddsDataLoader] {error_msg}")
                if status_callback:
                    status_callback(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"[OddsDataLoader] Successfully loaded over/under odds for {match_id}")
            if status_callback:
                status_callback(f"Successfully loaded over/under odds for {match_id}")
            
            if self.selenium_utils:
                # Wait for dynamic content to load
                timeout_config = CONFIG.get('timeout', {})
                dynamic_timeout = timeout_config.get('dynamic_content_timeout', 30)
                self.selenium_utils.wait_for_dynamic_content(dynamic_timeout)
                
                # For scheduled matches, we don't need to check status - we know they are scheduled
                
                # Check for required tabs
                if not self.selenium_utils.check_tab_present('Odds'):
                    error_msg = f"No odds available for match {match_id}."
                    logger.warning(f"[OddsDataLoader] {error_msg}")
                    if status_callback:
                        status_callback(error_msg)
                    return False
                    
                if not self.selenium_utils.check_tab_present('Over/Under'):
                    error_msg = f"No over/under odds available for match {match_id}."
                    logger.warning(f"[OddsDataLoader] {error_msg}")
                    if status_callback:
                        status_callback(error_msg)
                    return False
            
            # Extract and process over/under odds
            logger.info(f"[OddsDataLoader] Extracting over/under odds for match {match_id}")
            all_totals = self.get_all_totals()
            
            if not all_totals:
                logger.warning(f"[OddsDataLoader] No over/under alternatives available for match {match_id}")
                if status_callback:
                    status_callback(f"No over/under market offered for match {match_id}")
                return False
            
            # Try to find the selected total line
            self.elements.match_total = self.get_match_total(all_totals)
            
            # If no total is selected, try clicking on the first available total
            if not self.elements.match_total and all_totals:
                logger.debug(f"[OddsDataLoader] No total line selected, attempting to select first available")
                first_total = all_totals[0].get('alternative')
                if first_total and self.select_total_line(first_total):
                    # Wait a moment for the selection to take effect
                    if self.selenium_utils:
                        self.selenium_utils.wait_for_dynamic_content(2)
                    # Try to get the selected total again
                    self.elements.match_total = self.get_match_total(all_totals)
            
            self.elements.over_odds = self.get_over_odds(all_totals, selected_total=self.elements.match_total)
            self.elements.under_odds = self.get_under_odds(all_totals, selected_total=self.elements.match_total)

            
            # Check if we have valid over/under data
            if not self.elements.match_total or not self.elements.over_odds or not self.elements.under_odds:
                logger.warning(f"[OddsDataLoader] No selected over/under alternative available for match {match_id}")
                if status_callback:
                    status_callback(f"No selected over/under alternative available for match {match_id}")
                return False
            
            # Verify the extracted data
            is_valid, error = self.odds_data_verifier.verify_match_total(self.elements.match_total)
            if not is_valid:
                logger.warning(f"[OddsDataLoader] {error}")
                
            is_valid, error = self.odds_data_verifier.verify_over_odds(self.elements.over_odds)
            if not is_valid:
                logger.warning(f"[OddsDataLoader] {error}")
                
            is_valid, error = self.odds_data_verifier.verify_under_odds(self.elements.under_odds)
            if not is_valid:
                logger.warning(f"[OddsDataLoader] {error}")
            
            logger.info(f"[OddsDataLoader] Successfully processed over/under odds for match {match_id}")
            return True
            
        try:
            logger.info(f"[OddsDataLoader] Starting over/under odds loading process for match {match_id}")
            result = self.retry_manager.retry_network_operation(
                _load_operation
            )
            
            if result and status_callback:
                status_callback(f"Successfully loaded over/under odds for match {match_id}.")
                
            return result
            
        except Exception as e:
            error_msg = f"Failed to load over/under odds for match {match_id}: {str(e)}"
            logger.error(f"[OddsDataLoader] {error_msg}", exc_info=True)
            if status_callback:
                status_callback(f"Failed to load over/under odds for match {match_id}: {str(e)}")
            return False

    def load_odds(self, url_builder: UrlBuilder, status_callback=None) -> bool:
        """Load both home/away and over/under odds for a match with network resilience.
        
        Args:
            url_builder: A UrlBuilder instance containing the match URL
            status_callback: Optional callback for status updates
                
        Returns:
            bool: True if both home/away and over/under odds were loaded successfully, False otherwise
        """
        if status_callback:
            status_callback(f"Loading all odds for match {url_builder.mid}...")
            
        home_away_success = self.load_home_away_odds(url_builder, status_callback)
        over_under_success = self.load_over_under_odds(url_builder, status_callback)
        
        result = home_away_success and over_under_success
        
        if status_callback:
            if result:
                status_callback(f"Successfully loaded all odds for match {url_builder.mid}")
            else:
                status_callback(f"Failed to load some odds for match {url_builder.mid}")
                
        return result

    def load_odds_data(self, url_builder: UrlBuilder) -> Dict[str, Any]:
        """Load and extract all odds data for a match using UrlBuilder.
        
        Args:
            url_builder: A UrlBuilder instance containing the match URL
            
        Returns:
            dict: Dictionary containing status and extracted odds data
            
        The return value is a dictionary with the following structure:
        {
            'status': 'success' | 'data_unavailable',
            'odds': dict,  # Only present if status is 'success'
            'skip_reason': str  # Only present if status is 'data_unavailable'
        }
        """
        match_id = url_builder.mid
        try:
            logger.info(f"[OddsDataLoader] Loading odds data for match {match_id}")
            
            # First try to load all odds
            if not self.load_odds(url_builder):
                warning_msg = f"Failed to load some odds for match {match_id}"
                logger.warning(warning_msg)
                return {
                    'status': 'data_unavailable',
                    'skip_reason': warning_msg
                }
            
            # Extract the odds data
            odds = self._extract_odds(match_id)
            
            if not odds:
                error_msg = f"No odds data found for match {match_id}"
                logger.warning(error_msg)
                return {
                    'status': 'data_unavailable',
                    'skip_reason': error_msg
                }
                
            # Validate the extracted data
            required_fields = ['home_odds', 'away_odds', 'match_total', 'over_odds', 'under_odds']
            missing = [field for field in required_fields if not odds.get(field)]
            
            if missing:
                error_msg = f"Missing odds fields for match {match_id}: {', '.join(missing)}"
                logger.warning(error_msg)
                return {
                    'status': 'data_unavailable',
                    'skip_reason': error_msg
                }
                
            logger.info(f"[OddsDataLoader] Successfully loaded odds data for match {match_id}")
            return {
                'status': 'success',
                'odds': odds
            }
            
        except Exception as e:
            error_msg = f"Unexpected error loading odds for match {match_id}: {str(e)}"
            logger.error(f"[OddsDataLoader] {error_msg}", exc_info=True)
            return {
                'status': 'data_unavailable',
                'skip_reason': error_msg
            }

    def _extract_odds(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Extract odds data from the current page.
        
        Args:
            match_id: The match ID to extract odds for
            
        Returns:
            dict: Dictionary containing extracted odds data, or None if extraction fails
            
        Note:
            This is a helper method that assumes the page has already been loaded.
            Call load_odds() or load_home_away_odds()/load_over_under_odds() first.
        """
        try:
            logger.info(f"[OddsDataLoader] Extracting odds data for match {match_id}")
            
            # Initialize default values
            odds_data = {
                'match_id': match_id,
                'timestamp': datetime.now().isoformat()
            }
            
            # Extract home and away odds
            try:
                home_odds = self.get_home_odds()
                odds_data['home_odds'] = home_odds.text if hasattr(home_odds, 'text') else str(home_odds)
            except Exception as e:
                logger.warning(f"[OddsDataLoader] Error extracting home odds: {str(e)}")
                odds_data['home_odds'] = None
                
            try:
                away_odds = self.get_away_odds()
                odds_data['away_odds'] = away_odds.text if hasattr(away_odds, 'text') else str(away_odds)
            except Exception as e:
                logger.warning(f"[OddsDataLoader] Error extracting away odds: {str(e)}")
                odds_data['away_odds'] = None
            
            # Extract over/under odds
            all_totals = []
            try:
                all_totals = self.get_all_totals() or []
                match_total = self.get_match_total(all_totals)
                over_odds = self.get_over_odds(all_totals)
                under_odds = self.get_under_odds(all_totals)
                
                odds_data.update({
                    'match_total': match_total.text if hasattr(match_total, 'text') else str(match_total) if match_total else None,
                    'over_odds': over_odds.text if hasattr(over_odds, 'text') else str(over_odds) if over_odds else None,
                    'under_odds': under_odds.text if hasattr(under_odds, 'text') else str(under_odds) if under_odds else None
                })
            except Exception as e:
                logger.warning(f"[OddsDataLoader] Error extracting over/under odds: {str(e)}")
                odds_data.update({
                    'match_total': None,
                    'over_odds': None,
                    'under_odds': None
                })
            
            # Log successful extraction
            logger.info(f"[OddsDataLoader] Successfully extracted odds for match {match_id}")
            return odds_data
            
        except Exception as e:
            logger.error(f"[OddsDataLoader] Error extracting odds for match {match_id}: {str(e)}", exc_info=True)
            return None

    def _safe_find_element(self, locator: str, value: str, index: Optional[int] = None):
        """Safely find and return a WebElement using selenium_utils with network resilience."""
        def _find_operation():
            if self.selenium_utils:
                if index is not None:
                    elements = self.selenium_utils.find_all(locator, value)
                    if elements and len(elements) > index:
                        return elements[index]
                    return None
                else:
                    element = self.selenium_utils.find(locator, value)
                    return element
            return None

        try:
            return self.retry_manager.retry_network_operation(_find_operation)
        except Exception:
            return None 