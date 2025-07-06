from ..elements_model import OddsElements
from typing import Optional
from ...config import CONFIG, SELECTORS, ODDS_URL_HOME_AWAY, ODDS_URL_OVER_UNDER
from ...core.url_verifier import URLVerifier
from selenium.webdriver.remote.webdriver import WebDriver
from ..verifier.odds_data_verifier import OddsDataVerifier

class OddsDataLoader:
    def __init__(self, driver: WebDriver, selenium_utils=None):
        self.driver = driver
        self.elements = OddsElements()
        self.selenium_utils = selenium_utils
        self.url_verifier = URLVerifier(driver)
        self.odds_data_verifier = OddsDataVerifier(driver)

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
        total_elements = self.selenium_utils.find_all('css', SELECTORS['odds']['table']['over_under']['odds']['total']['cell'])
        over_elements = self.selenium_utils.find_all('css', SELECTORS['odds']['table']['over_under']['odds']['over']['cell'])
        under_elements = self.selenium_utils.find_all('css', SELECTORS['odds']['table']['over_under']['odds']['under']['cell'])
        all_totals = []
        for t, o, u in zip(total_elements, over_elements, under_elements):
            all_totals.append({'alternative': t, 'over': o, 'under': u})
        return all_totals

    def load_home_away_odds(self, match_id: str) -> bool:
        try:
            url = ODDS_URL_HOME_AWAY.format(match_id=match_id)
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                print(f"Error loading home/away odds page for {match_id}: {error}")
                return False
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
            self.elements.home_odds = self.get_home_odds()
            self.elements.away_odds = self.get_away_odds()
            # home_odds and away_odds are optional, do not fail if missing
            return True
        except Exception as e:
            print(f"Error loading home/away odds page for {match_id}: {e}")
            return False

    def load_over_under_odds(self, match_id: str) -> bool:
        try:
            url = ODDS_URL_OVER_UNDER.format(match_id=match_id)
            success, error = self.url_verifier.load_and_verify_url(url)
            if not success:
                print(f"Error loading over/under odds page for {match_id}: {error}")
                return False
            if self.selenium_utils:
                self.selenium_utils.wait_for_dynamic_content(CONFIG.timeout.dynamic_content_timeout)
            self.elements.all_totals = self.get_all_totals()
            is_valid, error = self.odds_data_verifier.verify_all_totals(self.elements.all_totals)
            if not is_valid:
                print(f"Error verifying all_totals for {match_id}: {error}")
                return False
            self.elements.match_total = self.get_match_total(self.elements.all_totals)
            is_valid, error = self.odds_data_verifier.verify_match_total(self.elements.match_total)
            if not is_valid:
                print(f"Error verifying match_total for {match_id}: {error}")
                return False
            self.elements.over_odds = self.get_over_odds(self.elements.all_totals)
            is_valid, error = self.odds_data_verifier.verify_over_odds(self.elements.over_odds)
            if not is_valid:
                print(f"Error verifying over_odds for {match_id}: {error}")
                return False
            self.elements.under_odds = self.get_under_odds(self.elements.all_totals)
            is_valid, error = self.odds_data_verifier.verify_under_odds(self.elements.under_odds)
            if not is_valid:
                print(f"Error verifying under_odds for {match_id}: {error}")
                return False
            return True
        except Exception as e:
            print(f"Error loading over/under odds page for {match_id}: {e}")
            return False

    def load_odds(self, match_id: str) -> bool:
        """Load both home/away and over/under odds for a match."""
        home_away_success = self.load_home_away_odds(match_id)
        over_under_success = self.load_over_under_odds(match_id)
        return home_away_success and over_under_success

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