import logging
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

from src.data.elements_model import H2HElements
from src.utils.config_loader import CONFIG, SELECTORS, MIN_H2H_MATCHES
from src.core.url_verifier import URLVerifier
from src.core.url_builder import UrlBuilder
from src.core.network_monitor import NetworkMonitor
from src.core.retry_manager import NetworkRetryManager
from selenium.webdriver.remote.webdriver import WebDriver
from src.data.verifier.h2h_data_verifier import H2HDataVerifier
from src.core.exceptions import DataNotFoundError, DataParseError, DataValidationError, DataUnavailableWarning

logger = logging.getLogger(__name__)

class H2HDataLoader:
    def __init__(self, driver: WebDriver, selenium_utils=None):
        self.driver = driver
        self.elements = H2HElements()
        self.elements.h2h_row_count = 0  # Always track row count
        # When True, indicates the H2H section explicitly contains a 'no data' marker
        # meaning the match legitimately has no H2H games. This differs from a load
        # failure or missing section.
        self._explicit_empty = False
        self.selenium_utils = selenium_utils
        self.url_verifier = URLVerifier(driver)
        self.h2h_data_verifier = H2HDataVerifier(driver)
        
        # Network resilience components
        self.network_monitor = NetworkMonitor()
        self.retry_manager = NetworkRetryManager()
        
        # Start network monitoring (handled centrally to avoid duplicates)
        # self.network_monitor.start_monitoring()

    def __del__(self):
        """Cleanup network monitoring on destruction."""
        if hasattr(self, 'network_monitor'):
            self.network_monitor.stop_monitoring()

    def get_h2h_section(self):
        # Try to get H2H section(s). Flashscore sometimes renders multiple sections;
        # historically the H2H section was at index 2 but this can change.
        sections = self._safe_find_elements('css', SELECTORS['h2h']['section'])
        if sections:
            # Prefer the historically-indexed section if present, else return the first available
            if len(sections) >= 3:
                return sections[2]
            return sections[0]

        # Fallback: try the higher-level H2H container selector if present
        container_selector = SELECTORS['h2h'].get('container')
        if container_selector:
            container = self._safe_find_element('css', container_selector)
            if container:
                return container

        return None

    def get_h2h_rows(self, h2h_section):
        row_elements = self._safe_find_elements('css', SELECTORS['h2h']['row'], parent=h2h_section)
        h2h_rows = []
        for row in row_elements:
            try:
                result_container = self._safe_find_element('css', SELECTORS['h2h']['result']['container'], parent=row)
                home_score_el = None
                away_score_el = None
                if result_container:
                    home_score_el = self._safe_find_element('css', SELECTORS['h2h']['result']['home'], parent=result_container)
                    away_score_el = self._safe_find_element('css', SELECTORS['h2h']['result']['away'], parent=result_container)

                row_dict = {
                    'date': self._safe_find_element('css', SELECTORS['h2h']['date'], parent=row),
                    'home_team': self._safe_find_element('css', SELECTORS['h2h']['home_participant']['container'], parent=row),
                    'away_team': self._safe_find_element('css', SELECTORS['h2h']['away_participant']['container'], parent=row),
                    'home_score': home_score_el,
                    'away_score': away_score_el,
                    'competition': self._safe_find_element('css', SELECTORS['h2h']['event']['container'], parent=row),
                }
                h2h_rows.append(row_dict)
            except Exception:
                continue
        return h2h_rows

    def get_h2h_row_count(self, h2h_rows):
        return len(h2h_rows)

    def load_h2h(
        self, 
        url_builder: UrlBuilder,
        status_callback=None
    ) -> bool:
        """Load the H2H page for a match and extract all required elements with network resilience.
        
        Args:
            url_builder: A UrlBuilder instance containing the match URL
            status_callback: Optional callback for status updates
                
        Returns:
            bool: True if H2H data was loaded successfully, False otherwise
        """
        def _load_operation():
            # Get the H2H URL from the builder
            url = url_builder.get('h2h')
            match_id = url_builder.mid
            
            if status_callback:
                status_callback(f"Loading H2H data for match {match_id}...")
                
            logger.debug(f"Using H2H URL: {url}")
            
            # Verify the H2H URL
            is_valid, error = self.h2h_data_verifier.verify_url(url, status_callback)
            if not is_valid:
                error_msg = f"Invalid H2H URL: {error}"
                logger.error(error_msg)
                if status_callback:
                    status_callback(error_msg)
                return False
                
            # Verify and load the URL with enhanced verification
            if status_callback:
                status_callback(f"Loading H2H page for {match_id}...")
                
            # Verify and load the URL
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                error_msg = f"Error loading H2H page for {match_id}: {error}"
                logger.error(error_msg)
                if status_callback:
                    status_callback(error_msg)
                raise Exception(error_msg)
                
            logger.info(f"Successfully loaded H2H page for {match_id}")
            if status_callback:
                status_callback(f"Successfully loaded H2H page for {match_id}")
            
            if self.selenium_utils:
                # Get timeout from config with default
                timeout_config = CONFIG.get('timeout', {})
                dynamic_timeout = timeout_config.get('dynamic_content_timeout', 30)  # default 30 seconds
                self.selenium_utils.wait_for_dynamic_content(dynamic_timeout)
                    
                # Check for H2H main tab
                if not self.selenium_utils.check_tab_present('H2H'):
                    error_msg = f"No H2H data available for match {match_id}."
                    logger.warning(f"[H2HDataLoader] {error_msg}")
                    if status_callback:
                        status_callback(error_msg)
                    return False
            
            # Extract H2H section and rows
            self.elements.h2h_section = self.get_h2h_section()
            is_valid, error = self.h2h_data_verifier.verify_h2h_section(self.elements.h2h_section)
            if not is_valid:
                raise Exception(f"Error verifying h2h_section for {match_id}: {error}")

            # Detect explicit no-data state and short-circuit without retries/exceptions
            try:
                no_data_selector = SELECTORS['h2h'].get('no_data')
                # Only check for the 'no data' indicator inside the resolved H2H section to avoid
                # picking up unrelated global no-data elements elsewhere on the page.
                if no_data_selector and self.selenium_utils and self.elements.h2h_section is not None:
                    # Suppress debug: absence is the normal case when rows exist
                    no_data_el = self.selenium_utils.find('css', no_data_selector, parent=self.elements.h2h_section, suppress_debug=True)
                    if no_data_el:
                        logger.info("'No H2H data' indicator present. Treating as valid empty state.")
                        self.elements.h2h_rows = []
                        self.elements.h2h_row_count = 0
                        # Mark explicit empty so callers can treat this as expected
                        self._explicit_empty = True
                        return True
            except Exception:
                # Non-fatal: proceed with normal flow if detection fails
                pass
            
            # Handle 'show more' button if present
            show_more_selector = SELECTORS['h2h']['show_more']
            # Use elements list to avoid exceptions/log spam when missing
            show_more_candidates = self._safe_find_elements('css', show_more_selector, parent=self.elements.h2h_section)
            show_more_btn = None
            for el in show_more_candidates:
                try:
                    if el and hasattr(el, 'is_displayed') and el.is_displayed():
                        show_more_btn = el
                        break
                except Exception:
                    continue
            if show_more_btn:
                try:
                    show_more_btn.click()
                    if self.selenium_utils:
                        timeout_config = CONFIG.get('timeout', {})
                        dynamic_timeout = timeout_config.get('dynamic_content_timeout', 30)
                        self.selenium_utils.wait_for_dynamic_content(dynamic_timeout)
                    if status_callback:
                        status_callback(f"Loaded additional H2H data for match {match_id}.")
                except Exception:
                    logger.info(f"'Show more' button present but not clickable for {match_id}. Proceeding with available H2H rows.")
            else:
                logger.info(f"'Show more' button not present in H2H section for {match_id}. Proceeding with available H2H rows.")
            
            # Extract and verify H2H rows
            self.elements.h2h_rows = self.get_h2h_rows(self.elements.h2h_section)
            self.elements.h2h_row_count = self.get_h2h_row_count(self.elements.h2h_rows)
            # If we found rows, it's not an explicit-empty state
            if self.elements.h2h_row_count:
                self._explicit_empty = False
            
            # Validation: treat insufficient rows as non-fatal (no exceptions, no retries)
            is_valid, error = self.h2h_data_verifier.verify_h2h_rows(self.elements.h2h_rows)
            if not is_valid:
                logger.info(f"[H2HDataLoader] Soft validation issue for h2h_rows: {error}")
                # Continue; upstream will decide skip_reason based on count
            
            is_valid, error = self.h2h_data_verifier.verify_h2h_row_count(self.elements.h2h_row_count)
            if not is_valid:
                logger.info(f"[H2HDataLoader] Soft validation issue for h2h_row_count: {error}")
                # Continue; upstream will decide skip_reason based on count
            
            return True
        
        try:
            # Execute with retry logic
            return self.retry_manager.retry_network_operation(
                _load_operation
            )
        except Exception as e:
            logger.error(f"Failed to load H2H page for {url_builder.mid}: {e}", exc_info=True)
            if status_callback:
                status_callback(f"Failed to load H2H page for {url_builder.mid}: {e}")
            return False

    def _safe_find_element(self, locator: str, value: str, parent: Optional[object] = None):
        """Safely find and return a WebElement using selenium_utils with network resilience."""
        def _find_operation():
            if self.selenium_utils:
                return self.selenium_utils.find(locator, value, parent=parent)
            return None

        try:
            return self.retry_manager.retry_network_operation(_find_operation)
        except Exception:
            return None

    def _safe_find_elements(self, locator: str, value: str, parent: Optional[object] = None):
        """Safely find and return WebElements using selenium_utils with network resilience."""
        def _find_operation():
            if self.selenium_utils:
                return self.selenium_utils.find_all(locator, value, parent=parent)
            return []

        try:
            return self.retry_manager.retry_network_operation(_find_operation)
        except Exception:
            return []

    def get_date(self, row):
        return row.get('date')

    def get_home_team(self, row):
        return row.get('home_team')

    def get_away_team(self, row):
        return row.get('away_team')

    def get_result(self, row):
        return row.get('result')

    def get_competition(self, row):
        return row.get('competition')

    def click_show_more(self):
        """Click the 'show more' button in the H2H section if present with network resilience."""
        def _click_operation():
            if not self.selenium_utils:
                return False
            show_more_selector = SELECTORS['h2h']['show_more']
            parent = self.elements.h2h_section if hasattr(self.elements, 'h2h_section') else None
            show_more_btn = self._safe_find_element('css', show_more_selector, parent=parent)
            if show_more_btn and show_more_btn.is_displayed():
                show_more_btn.click()
                # Get timeout from config with default
                timeout_config = CONFIG.get('timeout', {})
                dynamic_timeout = timeout_config.get('dynamic_content_timeout', 30)  # default 30 seconds
                self.selenium_utils.wait_for_dynamic_content(dynamic_timeout)
                return True
            return False

        try:
            return self.retry_manager.retry_network_operation(_click_operation)
        except Exception as e:
            logger.error(f"Error clicking show more: {e}")
            return False

    @property
    def h2h_row_count(self):
        return self.elements.h2h_row_count

    @h2h_row_count.setter
    def h2h_row_count(self, value):
        self.elements.h2h_row_count = value

    def get_total_h2h_matches(self):
        """Return the total number of available H2H matches (games)."""
        return self.h2h_row_count

    def is_explicit_empty(self) -> bool:
        """Return True if the H2H section explicitly indicated no data for this match."""
        return bool(getattr(self, '_explicit_empty', False))

    def get_h2h_count(self):
        """Return the number of H2H matches found, capped at MIN_H2H_MATCHES."""
        return min(self.elements.h2h_row_count, MIN_H2H_MATCHES) 