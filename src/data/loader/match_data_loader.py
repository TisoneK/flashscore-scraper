from src.data.elements_model import MatchElements
from typing import List, Optional, Dict, Any, Union, TypedDict
from urllib.parse import urlparse, parse_qs
import logging

from src.utils.config_loader import CONFIG, SELECTORS
from src.core.url_verifier import URLVerifier
from src.core.url_builder import UrlBuilder
from src.core.network_monitor import NetworkMonitor
from src.core.retry_manager import NetworkRetryManager

from selenium.webdriver.remote.webdriver import WebDriver
from src.data.verifier.loader_verifier import LoaderVerifier
from src.data.verifier.match_data_verifier import MatchDataVerifier
from src.utils.utils import split_date_time
import logging
from src.core.exceptions import DataNotFoundError, DataParseError, DataValidationError, DataUnavailableWarning

logger = logging.getLogger(__name__)

class MatchUrls(TypedDict):
    mid: str
    summary: str
    home_away_odds: str
    over_under_odds: str
    h2h: str

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
            success, error = self.url_verifier.load_and_verify_url(CONFIG['url']['base_url'])
            if not success:
                raise Exception(f"Error loading main page: {error}")
            if self.selenium_utils:
                # Get timeout from config with default
                timeout_config = CONFIG.get('timeout', {})
                dynamic_timeout = timeout_config.get('dynamic_content_timeout', 30)  # default 30 seconds
                self.selenium_utils.wait_for_dynamic_content(dynamic_timeout)
            match_ids = self._get_match_ids_internal()
            self.update_match_id(match_ids)
            return True
        try:
            # Execute with retry logic (no cooperative stop passed here yet)
            result = self.retry_manager.retry_network_operation(_load_operation)
            if status_callback:
                status_callback("Main basketball page loaded.")
            return result
        except Exception as e:
            logger.error(f"Failed to load main page after retries: {e}")
            if status_callback:
                status_callback(f"Failed to load main basketball page: {e}")
            return False

    def collect_match_urls(self) -> List[MatchUrls]:
        """Collect immutable, canonical URLs for all scheduled matches on the list page.
        
        Returns a list of dicts with keys: 'mid', 'summary', 'home_away_odds', 'over_under_odds', 'h2h'.
        Uses only anchor href extraction; no fallbacks.
        """
        urls: List[MatchUrls] = []
        if not self.selenium_utils:
            return urls

        def _collect_operation():
            # Get timeout from config with default
            timeout_config = CONFIG.get('timeout', {})
            page_load_timeout = timeout_config.get('page_load_timeout', 30)  # default 30 seconds
            match_elements = self.selenium_utils.find_all("class", SELECTORS["match"]["scheduled"].split(".")[1], duration=page_load_timeout)
            if not match_elements:
                return []

            collected: List[MatchUrls] = []
            from src.core.url_builder import UrlBuilder  # local import to avoid cycles

            for idx, element in enumerate(match_elements):
                try:
                    # Strict single-selector strategy: anchor with match path
                    anchor = self.selenium_utils.find_element_in_parent(element, "css", 'a[href*="/match/"]')
                    if not anchor:
                        continue
                    href = anchor.get_attribute('href')
                    if not href:
                        continue
                    builder = UrlBuilder.from_summary_url(href)
                    urls_dict = builder.get_urls()
                    urls_dict_with_mid = {**urls_dict, 'mid': builder.mid}
                    collected.append(urls_dict_with_mid)
                except Exception as e:
                    # Log at debug level; still skip to honor no-fallbacks policy
                    logger.debug(f"Skipping match element index {idx} due to error: {e}")
                    continue
            return collected

        try:
            urls = self.retry_manager.retry_network_operation(_collect_operation) or []
        except Exception:
            urls = []
        return urls

    def load_match(
        self, 
        url_builder: Union[UrlBuilder, str],
        status_callback=None
    ) -> bool:
        """Load a match page and extract all required elements with network resilience.
        
        Args:
            url_builder: Either a UrlBuilder instance or a string match ID
            status_callback: Optional callback for status updates
            
        Returns:
            bool: True if match was loaded successfully, False otherwise
        """
        if isinstance(url_builder, str):
            # If a string is provided, treat it as a match ID
            match_id = url_builder
            from src.core.url_builder import UrlBuilder  # Import here to avoid circular imports
            url_builder = UrlBuilder(match_id=match_id)
            
        url = url_builder.get('summary')
        match_id = getattr(url_builder, 'mid', str(url_builder))
        
        logger.debug(f"Loading match using UrlBuilder for match {match_id}")
        
        # Verify the URL using the match data verifier
        if status_callback:
            status_callback(f"Verifying match URL for {match_id}...")
            
        is_valid, error = self.match_data_verifier.verify_url(url, 'summary', status_callback)
        if not is_valid:
            logger.error(f"Invalid URL from UrlBuilder: {error}")
            return False
            
        try:
            # Execute with retry logic
            return self.retry_manager.retry_network_operation(
                lambda: self._load_match_page(url, match_id, status_callback)
            )
        except Exception as e:
            logger.error(f"Failed to load match {match_id} after retries: {e}")
            if status_callback:
                status_callback(f"Failed to load match page for {match_id}: {e}")
            return False

            if element is None:
                raise Exception(f"Failed to extract {element_name}")
            return element

        try:
            return self.retry_manager.retry_network_operation(_extraction_operation)
        except Exception as e:
            logger.warning(f"Failed to extract {element_name}: {e}")
            return None
            
    def _extract_match_id_from_url(self, url: str, default_match_id: str) -> str:
        """Extract match ID from URL if possible, otherwise return the default.
        
        Args:
            url: The URL to extract match ID from
            default_match_id: The match ID to return if extraction fails
            
        Returns:
            str: The extracted match ID or the default if extraction fails
        """
        if not url or not url.startswith(('http://', 'https://')):
            return default_match_id
            
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'mid' in params and params['mid']:
                new_match_id = params['mid'][0]
                if new_match_id != default_match_id:
                    logger.debug(f"Extracted match ID from URL: {new_match_id} (was: {default_match_id})")
                return new_match_id
        except Exception as e:
            logger.warning(f"Could not extract match ID from URL, using default: {e}")
            
        return default_match_id
        
    def _load_match_page(self, url: str, match_id: str, status_callback=None) -> bool:
        """Load and verify the match page.
        
        Args:
            url: The URL to load
            match_id: The match ID for logging
            status_callback: Optional callback for status updates
            
        Returns:
            bool: True if the page was loaded successfully, False otherwise
        """
        def _load_operation():
            if status_callback:
                status_callback(f"Loading match page for {match_id}...")
                
            # Load and verify the URL
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                error_msg = f"Error loading match page for {match_id}: {error}"
                logger.error(error_msg)
                if status_callback:
                    status_callback(error_msg)
                return False
                
            logger.info(f"Successfully loaded match page for {match_id}")
            if status_callback:
                status_callback(f"Successfully loaded match page for {match_id}")
                
            # Wait for dynamic content if using Selenium
            if self.selenium_utils:
                timeout_config = CONFIG.get('timeout', {})
                dynamic_timeout = timeout_config.get('dynamic_content_timeout', 30)  # default 30 seconds
                self.selenium_utils.wait_for_dynamic_content(dynamic_timeout)
            
            # Extract and verify all match elements
            elements_to_verify = [
                ('country', self.get_country, self.match_data_verifier.verify_country),
                ('league', self.get_league, self.match_data_verifier.verify_league),
                ('home_team', self.get_home_team, self.match_data_verifier.verify_home_team),
                ('away_team', self.get_away_team, self.match_data_verifier.verify_away_team),
                ('date', self.get_date, self.match_data_verifier.verify_date),
                ('time', self.get_time, self.match_data_verifier.verify_time)
            ]
            
            for element_name, getter, verifier in elements_to_verify:
                element = self._retry_element_extraction(
                    getter,
                    f"{element_name} for {match_id}"
                )
                if element is None:
                    error_msg = f"Failed to extract {element_name} for {match_id}"
                    logger.error(error_msg)
                    if status_callback:
                        status_callback(error_msg)
                    return False
                    
                setattr(self.elements, element_name, element)
                
                is_valid, error = verifier(element)
                if not is_valid:
                    error_msg = f"Error verifying {element_name} for {match_id}: {error}"
                    logger.error(error_msg)
                    if status_callback:
                        status_callback(error_msg)
                    return False
            
            # Set and verify match ID
            self.elements.match_id = match_id
            is_valid, error = self.match_data_verifier.verify_match_id(match_id)
            if not is_valid:
                error_msg = f"Error verifying match_id for {match_id}: {error}"
                logger.error(error_msg)
                if status_callback:
                    status_callback(error_msg)
                return False
                
            return True
            
        try:
            return self.retry_manager.retry_network_operation(_load_operation)
        except Exception as e:
            error_msg = f"Error in _load_match_page for {match_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if status_callback:
                status_callback(error_msg)
            return False

    def _retry_element_extraction(self, getter_func, element_name: str):
        """Retry element extraction with network resilience.
        
        Args:
            getter_func: Function to call to get the element
            element_name: Name of the element for logging
            
        Returns:
            The extracted element or None if failed
        """
        def _extraction_operation():
            try:
                element = getter_func()
                if element is None:
                    raise Exception(f"Failed to extract {element_name}")
                return element
            except Exception as e:
                raise Exception(f"Failed to extract {element_name}: {str(e)}")

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
                calendar_config = CONFIG.get('selectors', {}).get("calendar", {})
                navigation_config = calendar_config.get("navigation", {})
                
                # Try multiple selectors for the tomorrow button
                selectors = [
                    ("css", navigation_config.get("tomorrow_button", "[data-day-picker-arrow='next']")),
                    ("css", navigation_config.get("tomorrow_button_alt", "[aria-label='Next day']")),
                    ("css", navigation_config.get("tomorrow_button_class", ".wcl-arrow_8k9lP")),
                    ("class", "calendar__navigation--tomorrow"),  # Fallback to old selector
                ]
                
                # Get timeout from config with default
                timeout_config = CONFIG.get('timeout', {})
                element_timeout = timeout_config.get('element_timeout', 10)  # default 10 seconds
                
                for selector_type, selector in selectors:
                    logger.info(f"Trying selector: {selector_type} = {selector}")
                    tomorrow_btn = self.selenium_utils.find(selector_type, selector, duration=element_timeout)
                    if tomorrow_btn:
                        logger.info(f"Found tomorrow button with selector: {selector}")
                        tomorrow_btn.click()
                        # Wait for page to load after click
                        if self.selenium_utils:
                            # Get timeout from config with default
                            timeout_config = CONFIG.get('timeout', {})
                            dynamic_timeout = timeout_config.get('dynamic_content_timeout', 30)  # default 30 seconds
                            self.selenium_utils.wait_for_dynamic_content(dynamic_timeout)
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
                # Get timeout from config with default
                timeout_config = CONFIG.get('timeout', {})
                page_load_timeout = timeout_config.get('page_load_timeout', 30)  # default 30 seconds
                match_elements = self.selenium_utils.find_all("class", SELECTORS["match"]["scheduled"].split(".")[1], duration=page_load_timeout)
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
            self.logger.error(f"Failed to extract match IDs: {e}")
            return []