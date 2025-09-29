from src.data.elements_model import ResultsElements
from typing import List, Optional, Dict, Any
from src.utils.config_loader import CONFIG
from src.core.url_verifier import URLVerifier
from src.core.url_builder import UrlBuilder
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

    def get_home_score(self):
        """Extract the home score element."""
        return self._safe_find_element('css', CONFIG['selectors']['results']['home_score'])

    def get_away_score(self):
        """Extract the away score element."""
        return self._safe_find_element('css', CONFIG['selectors']['results']['away_score'])

    def get_match_status(self):
        """Extract the match status element."""
        return self._safe_find_element('css', CONFIG['selectors']['results']['match_status'])

    # Optionally remove get_final_score if not needed, or update if you want to extract the wrapper
    def get_final_score_wrapper(self):
        """Extract the final score wrapper element (if needed)."""
        return self._safe_find_element('css', CONFIG.get('selectors', {}).get('results', {}).get('final_score_wrapper', ''))

    def load_match_summary(self, url_builder: UrlBuilder, status_callback=None) -> bool:
        """
        Load the match summary page for a specific match using a UrlBuilder instance.
        
        Args:
            url_builder: A UrlBuilder instance containing the match URL
            status_callback: Optional callback for status updates
                
        Returns:
            bool: True if the page was loaded successfully, False otherwise
        """
        match_id = url_builder.mid
        
        try:
            # Get the summary URL from the builder
            url = url_builder.get('summary')
            logger.info(f"[ResultsDataLoader] Loading match summary page for match {match_id}")
            
            if status_callback:
                status_callback(f"Loading match summary for {match_id}...")
            
            # Verify the URL first
            is_valid, error = self.url_verifier.verify_url(url, 'summary')
            if not is_valid:
                error_msg = f"Invalid summary URL for match {match_id}: {error}"
                logger.warning(f"[ResultsDataLoader] {error_msg}")
                if status_callback:
                    status_callback(error_msg)
                return False
            
            # Load the URL with retry logic
            success = self.retry_manager.retry_network_operation(
                lambda: self._load_url_with_verification(
                    url=url,
                    expected_paths=['summary/'],
                    error_message=f"Failed to load match summary page for match {match_id}"
                ),
                operation_name=f"load_match_summary({match_id})",
                status_callback=status_callback
            )
            
            if not success:
                error_msg = f"Failed to load match summary page for match {match_id}"
                logger.warning(f"[ResultsDataLoader] {error_msg}")
                if status_callback:
                    status_callback(error_msg)
                return False
                
            logger.info(f"[ResultsDataLoader] Successfully loaded match summary for {match_id}")
            if status_callback:
                status_callback(f"Successfully loaded match summary for {match_id}")
                
            # Verify the page is valid
            if not self.results_data_verifier.verify_page():
                logger.warning(f"Match summary page verification failed for match {match_id}")
                return False
                
            # Wait specifically for the results container to be present
            if self.selenium_utils:
                try:
                    # Get timeout from config with default
                    timeout_config = CONFIG.get('timeout', {})
                    element_timeout = timeout_config.get('element_timeout', 10)  # default 10 seconds
                    self.selenium_utils.find('css', CONFIG.get('selectors', {}).get('results', {}).get('final_score_wrapper', ''), duration=element_timeout)
                except Exception as e:
                    logger.warning(f"Error waiting for results container: {str(e)}")
                    return False
            
            # Extract and verify elements with retry logic for each
            self.elements.final_score = None  # Optionally update or remove if not used
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
            
            # Verify we have all required elements
            if not all([self.elements.home_score, self.elements.away_score, self.elements.match_status]):
                logger.warning(f"Failed to extract all required elements for match {match_id}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error in load_match_summary for match {match_id}: {str(e)}")
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
        if not self.selenium_utils:
            return None
            
        def _find_operation():
            try:
                return self.selenium_utils.find(locator, value, index=index)
            except Exception as e:
                logger.warning(f"Error finding element {locator}={value}: {str(e)}")
                return None
                
        try:
            return self.retry_manager.retry_network_operation(_find_operation)
        except Exception as e:
            logger.error(f"Failed to find element after retries: {str(e)}")
            return None

    def get_elements(self) -> ResultsElements:
        """Return the current elements."""
        return self.elements

    def set_elements(self, elements: ResultsElements):
        """Set the elements."""
        self.elements = elements 

    def load_match_results(self, url_builder: UrlBuilder, status_callback=None) -> Dict[str, Any]:
        """
        Load and extract match results using a UrlBuilder instance.
        
        Args:
            url_builder: A UrlBuilder instance containing the match URL
            status_callback: Optional callback for status updates
                
        Returns:
            dict: Dictionary containing match results with the following structure:
                {
                    'status': 'success' | 'data_unavailable',
                    'results': {
                        'home_score': str,
                        'away_score': str,
                        'match_status': str,
                        'timestamp': str
                    },
                    'skip_reason': str  # Only present if status is 'data_unavailable'
                }
        """
        match_id = url_builder.mid
        logger.info(f"[ResultsDataLoader] Loading match results for {match_id}")
        
        try:
            # Load the match summary first
            if not self.load_match_summary(url_builder, status_callback):
                error_msg = f"Failed to load match summary for {match_id}"
                logger.warning(f"[ResultsDataLoader] {error_msg}")
                return {
                    'status': 'data_unavailable',
                    'skip_reason': error_msg
                }
            
            # Extract the results
            results = {
                'home_score': None,
                'away_score': None,
                'match_status': None,
                'timestamp': None
            }
            
            # Extract scores with error handling
            try:
                home_score_elem = self.get_home_score()
                results['home_score'] = home_score_elem.text if hasattr(home_score_elem, 'text') else str(home_score_elem)
            except Exception as e:
                logger.warning(f"[ResultsDataLoader] Error extracting home score: {str(e)}")
            
            try:
                away_score_elem = self.get_away_score()
                results['away_score'] = away_score_elem.text if hasattr(away_score_elem, 'text') else str(away_score_elem)
            except Exception as e:
                logger.warning(f"[ResultsDataLoader] Error extracting away score: {str(e)}")
            
            try:
                status_elem = self.get_match_status()
                results['match_status'] = status_elem.text if hasattr(status_elem, 'text') else str(status_elem)
            except Exception as e:
                logger.warning(f"[ResultsDataLoader] Error extracting match status: {str(e)}")
            
            # Add timestamp
            from datetime import datetime
            results['timestamp'] = datetime.now().isoformat()
            
            # Validate we have the minimum required data
            required_fields = ['home_score', 'away_score', 'match_status']
            missing = [field for field in required_fields if not results.get(field)]
            
            if missing:
                error_msg = f"Missing required match result fields: {', '.join(missing)}"
                logger.warning(f"[ResultsDataLoader] {error_msg}")
                return {
                    'status': 'data_unavailable',
                    'skip_reason': error_msg,
                    'partial_results': results
                }
            
            logger.info(f"[ResultsDataLoader] Successfully loaded match results for {match_id}")
            return {
                'status': 'success',
                'results': results
            }
            
        except Exception as e:
            error_msg = f"Error loading match results for {match_id}: {str(e)}"
            logger.error(f"[ResultsDataLoader] {error_msg}", exc_info=True)
            return {
                'status': 'data_unavailable',
                'skip_reason': error_msg
            }

    def get_window_title(self):
        """Return the current window title from the driver if match is finished, else None."""
        try:
            status = self.get_match_status()
            if status and str(status).strip().lower() == 'finished':
                if hasattr(self, 'driver') and self.driver is not None:
                    return self.driver.title
        except Exception:
            return None
        return None 