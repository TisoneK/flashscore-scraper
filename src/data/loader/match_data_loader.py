from src.data.elements_model import MatchElements
from typing import List, Optional
from src.config import CONFIG, SELECTORS
from src.core.url_verifier import URLVerifier
from src.core.network_monitor import NetworkMonitor
from src.core.retry_manager import NetworkRetryManager

from selenium.webdriver.remote.webdriver import WebDriver
from src.data.verifier.loader_verifier import LoaderVerifier
from src.data.verifier.match_data_verifier import MatchDataVerifier
from src.utils.utils import split_date_time
import logging
from src.core.exceptions import DataNotFoundError, DataParseError, DataValidationError, DataUnavailableWarning

logger = logging.getLogger(__name__)

class MatchDataLoader:
    def __init__(self, driver: WebDriver, selenium_utils=None):
        self.driver = driver
        self._match_ids: List[str] = []
        self._match_id = ""
        self.elements = MatchElements()
        self.selenium_utils = selenium_utils
        self.url_verifier = URLVerifier(driver)
        self.loader_verifier = LoaderVerifier(driver)
        self.match_data_verifier = MatchDataVerifier(driver)
        
        # Network resilience components
        self.network_monitor = NetworkMonitor()
        self.retry_manager = NetworkRetryManager()
        
        # Start network monitoring
        self.network_monitor.start_monitoring()

    def __del__(self):
        """Cleanup network monitoring on destruction."""
        if hasattr(self, 'network_monitor'):
            self.network_monitor.stop_monitoring()

    def get_country(self):
        return self._safe_find_element('css', SELECTORS['match']['navigation']['text'], index=SELECTORS['match']['navigation']['country']['index'])

    def get_league(self):
        return self._safe_find_element('css', SELECTORS['match']['navigation']['text'], index=SELECTORS['match']['navigation']['league']['index'])

    def get_home_team(self):
        return self._safe_find_element('css', SELECTORS['match']['teams']['home'])

    def get_away_team(self):
        return self._safe_find_element('css', SELECTORS['match']['teams']['away'])

    def get_date(self):
        return self._safe_find_element('css', SELECTORS['match']['datetime']['container'])

    def get_time(self):
        return self._safe_find_element('css', SELECTORS['match']['datetime']['container'])

    def load_main_page(self, status_callback=None) -> bool:
        """Load the main basketball page and update match IDs with network resilience."""
        if status_callback:
            status_callback("Loading main basketball page...")
        def _load_operation():
            success, error = self.url_verifier.load_and_verify_url(CONFIG.url.base_url)
            if not success:
                raise Exception(f"Error loading main page: {error}")
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
            match_ids = self._get_match_ids_internal()
            self.update_match_id(match_ids)
            return True
        try:
            # Execute with retry logic
            result = self.retry_manager.retry_network_operation(_load_operation)
            if status_callback:
                status_callback("Main basketball page loaded.")
            return result
        except Exception as e:
            logger.error(f"Failed to load main page after retries: {e}")
            if status_callback:
                status_callback(f"Failed to load main basketball page: {e}")
            return False

    def load_match(self, match_id: str, status_callback=None) -> bool:
        """Load a match page and extract all required elements with network resilience."""
        if status_callback:
            status_callback(f"Loading match page for {match_id}...")
        def _load_operation():
            url = CONFIG.url.match_url_template.format(match_id)
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                raise Exception(f"Error loading match page for {match_id}: {error}")
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
                # --- Match status check ---
                match_status = self.selenium_utils.get_match_status()
                if match_status != 'scheduled':
                    logger.warning(f"[MatchDataLoader] Skipping match {match_id}: status is '{match_status}'")
                    if status_callback:
                        status_callback(f"Skipping match {match_id}: status is '{match_status}'")
                    return False
            # Extract and verify elements with retry logic for each
            self.elements.country = self._retry_element_extraction(
                lambda: self.get_country(),
                f"country for {match_id}"
            )
            is_valid, error = self.match_data_verifier.verify_country(self.elements.country)
            if not is_valid:
                raise Exception(f"Error verifying country for {match_id}: {error}")
            self.elements.league = self._retry_element_extraction(
                lambda: self.get_league(),
                f"league for {match_id}"
            )
            is_valid, error = self.match_data_verifier.verify_league(self.elements.league)
            if not is_valid:
                raise Exception(f"Error verifying league for {match_id}: {error}")
            self.elements.home_team = self._retry_element_extraction(
                lambda: self.get_home_team(),
                f"home_team for {match_id}"
            )
            is_valid, error = self.match_data_verifier.verify_home_team(self.elements.home_team)
            if not is_valid:
                raise Exception(f"Error verifying home_team for {match_id}: {error}")
            self.elements.away_team = self._retry_element_extraction(
                lambda: self.get_away_team(),
                f"away_team for {match_id}"
            )
            is_valid, error = self.match_data_verifier.verify_away_team(self.elements.away_team)
            if not is_valid:
                raise Exception(f"Error verifying away_team for {match_id}: {error}")
            self.elements.date = self._retry_element_extraction(
                lambda: self.get_date(),
                f"date for {match_id}"
            )
            is_valid, error = self.match_data_verifier.verify_date(self.elements.date)
            if not is_valid:
                raise Exception(f"Error verifying date for {match_id}: {error}")
            self.elements.time = self._retry_element_extraction(
                lambda: self.get_time(),
                f"time for {match_id}"
            )
            is_valid, error = self.match_data_verifier.verify_time(self.elements.time)
            if not is_valid:
                raise Exception(f"Error verifying time for {match_id}: {error}")
            self.elements.match_id = match_id
            is_valid, error = self.match_data_verifier.verify_match_id(self.elements.match_id)
            if not is_valid:
                raise Exception(f"Error verifying match_id for {match_id}: {error}")
            return True
        try:
            # Execute with retry logic
            result = self.retry_manager.retry_network_operation(_load_operation)
            if status_callback:
                status_callback(f"Match page for {match_id} loaded.")
            return result
        except Exception as e:
            logger.error(f"Failed to load match {match_id} after retries: {e}")
            if status_callback:
                status_callback(f"Failed to load match page for {match_id}: {e}")
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

    def load_tomorrow_games(self) -> bool:
        """Click the 'tomorrow' button to load tomorrow's games with network resilience."""
        def _click_operation():
            if self.selenium_utils:
                # Get selectors from config
                calendar_config = CONFIG.selectors.get("calendar", {})
                navigation_config = calendar_config.get("navigation", {})
                
                # Try multiple selectors for the tomorrow button
                selectors = [
                    ("css", navigation_config.get("tomorrow_button", "[data-day-picker-arrow='next']")),
                    ("css", navigation_config.get("tomorrow_button_alt", "[aria-label='Next day']")),
                    ("css", navigation_config.get("tomorrow_button_class", ".wcl-arrow_8k9lP")),
                    ("class", "calendar__navigation--tomorrow"),  # Fallback to old selector
                ]
                
                for selector_type, selector in selectors:
                    logger.info(f"Trying selector: {selector_type} = {selector}")
                    tomorrow_btn = self.selenium_utils.find(selector_type, selector, duration=CONFIG.timeout.element_timeout)
                    if tomorrow_btn:
                        logger.info(f"Found tomorrow button with selector: {selector}")
                        tomorrow_btn.click()
                        # Wait for page to load after click
                        if self.selenium_utils:
                            self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
                        logger.info("Tomorrow button clicked successfully")
                        return True
                
                logger.error("No tomorrow button found with any selector")
                return False
            return False

        return self.retry_manager.retry_network_operation(_click_operation)

    def update_match_id(self, match_ids: List[str]):
        self._match_ids = match_ids

    def set_match_id(self, match_id: str):
        self._match_id = match_id

    def get_match_id(self):
        return self._match_id

    def get_match_ids(self) -> List[str]:
        return self._match_ids

    def get_today_match_ids(self) -> List[str]:
        """Get all scheduled match IDs for today with network resilience."""
        if not self.get_match_ids():
            if not self.load_main_page():
                logger.warning("Failed to load main page, returning empty match IDs")
                return []
        return self._match_ids

    def get_tomorrow_match_ids(self) -> List[str]:
        """Get all scheduled match IDs for tomorrow with network resilience."""
        logger.info("Attempting to load tomorrow's matches...")
        if not self.load_main_page():
            logger.warning("Failed to load main page for tomorrow games")
            return []
        
        logger.info("Main page loaded, attempting to click tomorrow button...")
        if self.load_tomorrow_games():
            logger.info("Tomorrow button clicked, extracting match IDs...")
            match_ids = self._get_match_ids_internal()
            logger.info(f"Found {len(match_ids)} match IDs for tomorrow")
            self.update_match_id(match_ids)
            return match_ids
        else:
            logger.error("Failed to click tomorrow button or load tomorrow's games")
            return []

    def _get_match_ids_internal(self) -> List[str]:
        """Extract match IDs from the main page with network resilience."""
        def _extraction_operation():
            match_ids = []
            if self.selenium_utils:
                match_elements = self.selenium_utils.find_all("class", SELECTORS["match"]["scheduled"].split(".")[1], duration=CONFIG.timeout.page_load_timeout)
                if not match_elements:
                    return []
                for element in match_elements:
                    try:
                        element_id = element.get_attribute('id')
                        if element_id and element_id.startswith('g_3_'):
                            match_id = element_id.split('_')[-1]
                            match_ids.append(match_id)
                    except Exception:
                        continue
            return match_ids

        try:
            return self.retry_manager.retry_network_operation(_extraction_operation)
        except Exception as e:
            logger.error(f"Failed to extract match IDs: {e}")
            return [] 
    