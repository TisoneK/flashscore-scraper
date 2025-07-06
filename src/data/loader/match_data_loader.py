from ..elements_model import MatchElements
from typing import List, Optional
from ...config import CONFIG, SELECTORS
from ...core.url_verifier import URLVerifier
from selenium.webdriver.remote.webdriver import WebDriver
from ..verifier.loader_verifier import LoaderVerifier
from ..verifier.match_data_verifier import MatchDataVerifier
from src.utils.utils import split_date_time


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

    def load_main_page(self) -> bool:
        """Load the main basketball page and update match IDs."""
        try:
            success, error = self.url_verifier.load_and_verify_url(CONFIG.url.base_url)
            if not success:
                print(f"Error loading main page: {error}")
                return False
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
            match_ids = self._get_match_ids_internal()
            self.update_match_id(match_ids)
            return True
        except Exception as e:
            print(f"Error loading main page: {e}")
            return False

    def load_match(self, match_id: str) -> bool:
        """Load a match page and extract all required elements into self.elements (as WebElements)."""
        try:
            url = CONFIG.url.match_url_template.format(match_id)
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                print(f"Error loading match page for {match_id}: {error}")
                return False
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
            # Use getter methods and verify each field
            self.elements.country = self.get_country()
            is_valid, error = self.match_data_verifier.verify_country(self.elements.country)
            if not is_valid:
                print(f"Error verifying country for {match_id}: {error}")
                return False
            self.elements.league = self.get_league()
            is_valid, error = self.match_data_verifier.verify_league(self.elements.league)
            if not is_valid:
                print(f"Error verifying league for {match_id}: {error}")
                return False
            self.elements.home_team = self.get_home_team()
            is_valid, error = self.match_data_verifier.verify_home_team(self.elements.home_team)
            if not is_valid:
                print(f"Error verifying home_team for {match_id}: {error}")
                return False
            self.elements.away_team = self.get_away_team()
            is_valid, error = self.match_data_verifier.verify_away_team(self.elements.away_team)
            if not is_valid:
                print(f"Error verifying away_team for {match_id}: {error}")
                return False
            self.elements.date = self.get_date()
            is_valid, error = self.match_data_verifier.verify_date(self.elements.date)
            if not is_valid:
                print(f"Error verifying date for {match_id}: {error}")
                return False
            self.elements.time = self.get_time()
            is_valid, error = self.match_data_verifier.verify_time(self.elements.time)
            if not is_valid:
                print(f"Error verifying time for {match_id}: {error}")
                return False
            self.elements.match_id = match_id  # This is still a string, not an element
            is_valid, error = self.match_data_verifier.verify_match_id(self.elements.match_id)
            if not is_valid:
                print(f"Error verifying match_id for {match_id}: {error}")
                return False
            return True
        except Exception as e:
            print(f"Error loading match page for {match_id}: {e}")
            return False

    def _safe_find_element(self, locator: str, value: str, index: Optional[int] = None):
        """Safely find and return a WebElement using selenium_utils, optionally by index."""
        try:
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
        except Exception:
            return None

    def load_tomorrow_games(self) -> bool:
        """Click the 'tomorrow' button to load tomorrow's games."""
        if self.selenium_utils:
            tomorrow_btn = self.selenium_utils.find("class", "calendar__navigation--tomorrow", duration=CONFIG.timeout.element_timeout)
            if tomorrow_btn:
                tomorrow_btn.click()
                return True
        return False

    def update_match_id(self, match_ids: List[str]):
        self._match_ids = match_ids

    def set_match_id(self, match_id: str):
        self._match_id = match_id

    def get_match_id(self):
        return self._match_id

    def get_match_ids(self) -> List[str]:
        return self._match_ids

    def get_today_match_ids(self) -> List[str]:
        """Get all scheduled match IDs for today."""
        if not self.get_match_ids():
            self.load_main_page()
        return self._match_ids

    def get_tomorrow_match_ids(self) -> List[str]:
        """Get all scheduled match IDs for tomorrow."""
        self.load_main_page()
        if self.load_tomorrow_games():
            match_ids = self._get_match_ids_internal()
            self.update_match_id(match_ids)
            return match_ids
        return []

    def _get_match_ids_internal(self) -> List[str]:
        """Extract match IDs from the main page."""
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
    