import logging
from src.data.elements_model import H2HElements
from typing import Optional
from src.config import CONFIG, SELECTORS, H2H_URL, MIN_H2H_MATCHES
from src.core.url_verifier import URLVerifier
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
        self.selenium_utils = selenium_utils
        self.url_verifier = URLVerifier(driver)
        self.h2h_data_verifier = H2HDataVerifier(driver)
        
        # Network resilience components
        self.network_monitor = NetworkMonitor()
        self.retry_manager = NetworkRetryManager()
        
        # Start network monitoring
        self.network_monitor.start_monitoring()

    def __del__(self):
        """Cleanup network monitoring on destruction."""
        if hasattr(self, 'network_monitor'):
            self.network_monitor.stop_monitoring()

    def get_h2h_section(self):
        sections = self._safe_find_elements('css', SELECTORS['h2h']['section'])
        if not sections or len(sections) < 3:
            return None
        return sections[2]

    def get_h2h_rows(self, h2h_section):
        row_elements = self._safe_find_elements('css', SELECTORS['h2h']['row'], parent=h2h_section)
        h2h_rows = []
        for row in row_elements:
            try:
                row_dict = {
                    'date': self._safe_find_element('css', SELECTORS['h2h']['date'], parent=row),
                    'home_team': self._safe_find_element('css', SELECTORS['h2h']['home_participant'], parent=row),
                    'away_team': self._safe_find_element('css', SELECTORS['h2h']['away_participant'], parent=row),
                    'home_score': self._safe_find_element('css', SELECTORS['h2h']['result']['home'], parent=row),
                    'away_score': self._safe_find_element('css', SELECTORS['h2h']['result']['away'], parent=row),
                    'competition': self._safe_find_element('css', SELECTORS['h2h']['event']['container'], parent=row),
                }
                h2h_rows.append(row_dict)
            except Exception:
                continue
        return h2h_rows

    def get_h2h_row_count(self, h2h_rows):
        return len(h2h_rows)

    def load_h2h(self, match_id: str, status_callback=None) -> bool:
        """Load the H2H page for a match and extract all required elements with network resilience."""
        if status_callback:
            status_callback(f"Loading H2H data for match {match_id}...")
        def _load_operation():
            url = H2H_URL.format(match_id=match_id)
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                raise Exception(f"Error loading H2H page for {match_id}: {error}")
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
            self.elements.h2h_section = self.get_h2h_section()
            is_valid, error = self.h2h_data_verifier.verify_h2h_section(self.elements.h2h_section)
            if not is_valid:
                raise Exception(f"Error verifying h2h_section for {match_id}: {error}")
            show_more_selector = SELECTORS['h2h']['show_more']
            show_more_btn = self._safe_find_element('css', show_more_selector, parent=self.elements.h2h_section)
            if show_more_btn and show_more_btn.is_displayed():
                show_more_btn.click()
                if self.selenium_utils:
                    self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
                if status_callback:
                    status_callback(f"Clicked 'show more' for H2H data on match {match_id}.")
            else:
                logger.warning(f"'Show more' button not present in H2H section for {match_id}. Insufficient H2H data likely.")
            self.elements.h2h_rows = self.get_h2h_rows(self.elements.h2h_section)
            self.elements.h2h_row_count = self.get_h2h_row_count(self.elements.h2h_rows)
            is_valid, error = self.h2h_data_verifier.verify_h2h_rows(self.elements.h2h_rows)
            if not is_valid:
                raise Exception(f"Error verifying h2h_rows for {match_id}: {error}")
            is_valid, error = self.h2h_data_verifier.verify_h2h_row_count(self.elements.h2h_row_count)
            if not is_valid:
                raise Exception(f"Error verifying h2h_row_count for {match_id}: {error}")
            return True
        try:
            result = self.retry_manager.retry_network_operation(_load_operation)
            if status_callback:
                status_callback(f"H2H data loaded for match {match_id}.")
            return result
        except Exception as e:
            logger.error(f"Failed to load H2H page for {match_id} after retries: {e}")
            self.elements.h2h_rows = []
            self.elements.h2h_row_count = 0
            if status_callback:
                status_callback(f"Failed to load H2H data for match {match_id}: {e}")
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
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
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

    def get_h2h_count(self):
        """Return the number of H2H matches found, capped at MIN_H2H_MATCHES."""
        return min(self.elements.h2h_row_count, MIN_H2H_MATCHES) 