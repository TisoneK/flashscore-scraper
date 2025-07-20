from src.data.elements_model import ResultsElements
from typing import List, Optional
from src.config import CONFIG, SELECTORS
from src.core.url_verifier import URLVerifier
from src.core.network_monitor import NetworkMonitor
from src.core.retry_manager import NetworkRetryManager

from selenium.webdriver.remote.webdriver import WebDriver
from src.data.verifier.loader_verifier import LoaderVerifier
from src.data.verifier.results_data_verifier import ResultsDataVerifier
import logging
from src.core.exceptions import DataNotFoundError, DataParseError, DataValidationError, DataUnavailableWarning

logger = logging.getLogger(__name__)

class ResultsDataLoader:
    def __init__(self, driver: WebDriver, selenium_utils=None):
        self.driver = driver
        self.elements = ResultsElements()
        self.selenium_utils = selenium_utils
        self.url_verifier = URLVerifier(driver)
        self.loader_verifier = LoaderVerifier(driver)
        self.results_data_verifier = ResultsDataVerifier(driver)
        
        # Network resilience components
        self.network_monitor = NetworkMonitor()
        self.retry_manager = NetworkRetryManager()
        
        # Start network monitoring
        self.network_monitor.start_monitoring()

    def __del__(self):
        """Cleanup network monitoring on destruction."""
        if hasattr(self, 'network_monitor'):
            self.network_monitor.stop_monitoring()

    def get_final_score(self):
        """Extract the final score element from the match summary page."""
        return self._safe_find_element('css', SELECTORS['results']['final_score'])

    def get_home_score(self):
        """Extract the home score element."""
        return self._safe_find_element('css', SELECTORS['results']['home_score'])

    def get_away_score(self):
        """Extract the away score element."""
        return self._safe_find_element('css', SELECTORS['results']['away_score'])

    def get_match_status(self):
        """Extract the match status element."""
        return self._safe_find_element('css', SELECTORS['results']['match_status'])

    def load_match_summary(self, match_id: str, status_callback=None) -> bool:
        """Load a match summary page and extract all required elements with network resilience."""
        if status_callback:
            status_callback(f"Loading match summary for {match_id}...")
        
        def _load_operation():
            url = CONFIG.url.match_url_template.format(match_id)
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                raise Exception(f"Error loading match summary for {match_id}: {error}")
            
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
            
            # Extract and verify elements with retry logic for each
            self.elements.final_score = self._retry_element_extraction(
                lambda: self.get_final_score(),
                f"final score for {match_id}"
            )
            
            self.elements.home_score = self._retry_element_extraction(
                lambda: self.get_home_score(),
                f"home score for {match_id}"
            )
            
            self.elements.away_score = self._retry_element_extraction(
                lambda: self.get_away_score(),
                f"away score for {match_id}"
            )
            
            self.elements.match_status = self._retry_element_extraction(
                lambda: self.get_match_status(),
                f"match status for {match_id}"
            )
            
            return True
        
        try:
            # Execute with retry logic
            result = self.retry_manager.retry_network_operation(_load_operation)
            if status_callback:
                status_callback(f"Match summary for {match_id} loaded.")
            return result
        except Exception as e:
            logger.error(f"Failed to load match summary {match_id} after retries: {e}")
            if status_callback:
                status_callback(f"Failed to load match summary for {match_id}: {e}")
            return False

    def _retry_element_extraction(self, extraction_func, element_name: str):
        """Retry element extraction with network resilience."""
        def _extraction_operation():
            element = extraction_func()
            if element is None:
                raise Exception(f"Failed to extract {element_name}")
            return element

        try:
            return self.retry_manager.retry_network_operation(_extraction_operation)
        except Exception as e:
            logger.warning(f"Failed to extract {element_name}: {e}")
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

    def get_elements(self) -> ResultsElements:
        """Return the current elements."""
        return self.elements

    def set_elements(self, elements: ResultsElements):
        """Set the elements."""
        self.elements = elements 