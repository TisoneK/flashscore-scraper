from ..elements_model import OddsElements
from typing import Optional
from ...config import CONFIG, SELECTORS, ODDS_URL_HOME_AWAY, ODDS_URL_OVER_UNDER
from ...core.url_verifier import URLVerifier
from ...core.network_monitor import NetworkMonitor
from ...core.retry_manager import NetworkRetryManager
from selenium.webdriver.remote.webdriver import WebDriver
from ..verifier.odds_data_verifier import OddsDataVerifier
import logging

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
        self.network_monitor.start_monitoring()

    def __del__(self):
        """Cleanup network monitoring on destruction."""
        if hasattr(self, 'network_monitor'):
            self.network_monitor.stop_monitoring()

    def get_home_odds(self):
        return self._safe_find_element('css', SELECTORS['odds']['table']['home_away']['odds']['home']['cell'])

    def get_away_odds(self):
        return self._safe_find_element('css', SELECTORS['odds']['table']['home_away']['odds']['away']['cell'])

    def get_match_total(self, all_totals):
        return all_totals[0]['alternative'] if all_totals else None

    def get_over_odds(self, all_totals):
        return all_totals[0]['over'] if all_totals else None

    def get_under_odds(self, all_totals):
        return all_totals[0]['under'] if all_totals else None

    def get_all_totals(self):
        """Get all totals with network resilience."""
        def _extraction_operation():
            if not self.selenium_utils:
                return []
            total_elements = self.selenium_utils.find_all('css', SELECTORS['odds']['table']['over_under']['odds']['total']['cell'])
            over_elements = self.selenium_utils.find_all('css', SELECTORS['odds']['table']['over_under']['odds']['over']['cell'])
            under_elements = self.selenium_utils.find_all('css', SELECTORS['odds']['table']['over_under']['odds']['under']['cell'])
            all_totals = []
            for t, o, u in zip(total_elements, over_elements, under_elements):
                all_totals.append({'alternative': t, 'over': o, 'under': u})
            return all_totals

        try:
            return self.retry_manager.retry_network_operation(_extraction_operation)
        except Exception as e:
            logger.warning(f"Failed to extract all totals: {e}")
            return []

    def load_home_away_odds(self, match_id: str) -> bool:
        """Load home/away odds with network resilience."""
        def _load_operation():
            url = ODDS_URL_HOME_AWAY.format(match_id=match_id)
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                raise Exception(f"Error loading home/away odds page for {match_id}: {error}")
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
            self.elements.home_odds = self.get_home_odds()
            self.elements.away_odds = self.get_away_odds()
            # home_odds and away_odds are optional, do not fail if missing
            return True

        try:
            return self.retry_manager.retry_network_operation(_load_operation)
        except Exception as e:
            logger.error(f"Failed to load home/away odds page for {match_id} after retries: {e}")
            return False

    def load_over_under_odds(self, match_id: str) -> bool:
        """Load over/under odds with network resilience."""
        def _load_operation():
            url = ODDS_URL_OVER_UNDER.format(match_id=match_id)
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                raise Exception(f"Error loading over/under odds page for {match_id}: {error}")
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
            
            self.elements.all_totals = self.get_all_totals()
            is_valid, error = self.odds_data_verifier.verify_all_totals(self.elements.all_totals)
            if not is_valid:
                raise Exception(f"Error verifying all_totals for {match_id}: {error}")
            
            self.elements.match_total = self.get_match_total(self.elements.all_totals)
            is_valid, error = self.odds_data_verifier.verify_match_total(self.elements.match_total)
            if not is_valid:
                raise Exception(f"Error verifying match_total for {match_id}: {error}")
            
            self.elements.over_odds = self.get_over_odds(self.elements.all_totals)
            is_valid, error = self.odds_data_verifier.verify_over_odds(self.elements.over_odds)
            if not is_valid:
                raise Exception(f"Error verifying over_odds for {match_id}: {error}")
            
            self.elements.under_odds = self.get_under_odds(self.elements.all_totals)
            is_valid, error = self.odds_data_verifier.verify_under_odds(self.elements.under_odds)
            if not is_valid:
                raise Exception(f"Error verifying under_odds for {match_id}: {error}")
            
            return True

        try:
            return self.retry_manager.retry_network_operation(_load_operation)
        except Exception as e:
            logger.error(f"Failed to load over/under odds page for {match_id} after retries: {e}")
            return False

    def load_odds(self, match_id: str) -> bool:
        """Load both home/away and over/under odds for a match with network resilience."""
        home_away_success = self.load_home_away_odds(match_id)
        over_under_success = self.load_over_under_odds(match_id)
        return home_away_success and over_under_success

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