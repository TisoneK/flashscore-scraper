import unittest
from src.data.loader.results_data_loader import ResultsDataLoader
from src.data.extractor.results_data_extractor import ResultsDataExtractor
from src.driver_manager.web_driver_manager import WebDriverManager
import os
import time

class TestResultsDataLoader(unittest.TestCase):
    def setUp(self):
        print("[DEBUG] setUp: Initializing WebDriver using WebDriverManager...")
        try:
            log_path = os.path.join(os.path.dirname(__file__), "test_results_loader.log")
            self.driver_manager = WebDriverManager(chrome_log_path=log_path)
            self.driver = self.driver_manager.get_driver()
            from src.utils.selenium_utils import SeleniumUtils
            self.selenium_utils = SeleniumUtils(self.driver)
            self.loader = ResultsDataLoader(self.driver, selenium_utils=self.selenium_utils)
            self.extractor = ResultsDataExtractor(self.loader)
            self.match_id = "nkSrwgqh"  # Real match ID
            print(f"[DEBUG] setUp: WebDriver and loader initialized successfully. Log: {log_path}")
        except Exception as e:
            print(f"[ERROR] setUp: Failed to initialize WebDriver or loader: {e}")
            raise

    def test_load_and_extract_match_results(self):
        print(f"\n[DEBUG] test: Loading match summary for match_id: {self.match_id}")
        try:
            # Test with team info for canonical URL
            team_info = {
                'home_slug': 'instituto-de-cordoba',
                'home_id': 'rJPlbMMq',
                'away_slug': 'olimpico',
                'away_id': 'ERbTiFhJ'
            }
            result = self.loader.load_match_summary(
                self.match_id, 
                team_info=team_info,
                status_callback=print
            )
            # print(f"[DEBUG] Load result: {result}")
            # print(f"[DEBUG] Final score element: {self.loader.elements.final_score}")
            # print(f"[DEBUG] Home score element: {self.loader.elements.home_score}")
            # print(f"[DEBUG] Away score element: {self.loader.elements.away_score}")
            # print(f"[DEBUG] Match status element: {self.loader.elements.match_status}")
            # Use extractor to get actual scores
            home_score, away_score = self.extractor.extract_final_scores(status_callback=print)
            match_status = self.extractor.extract_match_status(status_callback=print)
            print(f"[DEBUG] Extracted home score: {home_score}")
            print(f"[DEBUG] Extracted away score: {away_score}")
            print(f"[DEBUG] Extracted match status: {match_status}")
            self.assertTrue(result)
            self.assertIsInstance(home_score, (int, type(None)))
            self.assertIsInstance(away_score, (int, type(None)))
            print("[DEBUG] Sleeping for 5 seconds so user can view browser...")
            time.sleep(5)
        except Exception as e:
            print(f"[ERROR] test: Exception during test: {e}")
            raise

    def test_load_match_summary_with_invalid_id(self):
        """Test loading a match with an invalid ID."""
        # Test with minimal URL (only match ID)
        result = self.loader.load_match_summary("invalid_id")
        # Test with team info
        team_info = {
            'home_slug': 'invalid',
            'home_id': 'invalid',
            'away_slug': 'invalid',
            'away_id': 'invalid'
        }
        result_with_team_info = self.loader.load_match_summary("invalid_id", team_info=team_info)

    def test_extract_scores_from_real_window_title(self):
        """Test extracting scores from the real window title after loading a real match page."""
        team_info = {
            'home_slug': 'instituto-de-cordoba',
            'home_id': 'rJPlbMMq',
            'away_slug': 'olimpico',
            'away_id': 'ERbTiFhJ'
        }
        # Load the match page with team info
        self.loader.load_match_summary(self.match_id, team_info=team_info, status_callback=print)
        # Use get_window_title() if match is finished, else fallback to driver.title
        title = self.loader.get_window_title() or self.driver.title
        print(f"[DEBUG] Real window title: {title}")
        home_score, away_score = self.extractor.extract_scores_from_title(title, status_callback=print)
        print(f"[DEBUG] Extracted from real title - home score: {home_score}, away score: {away_score}")
        self.assertIsInstance(home_score, (int, type(None)))
        self.assertIsInstance(away_score, (int, type(None)))

    def tearDown(self):
        print("[DEBUG] tearDown: Quitting WebDriver using WebDriverManager...")
        try:
            self.driver_manager.close()
            del self.loader
            del self.extractor
            print("[DEBUG] tearDown: WebDriver closed and objects deleted.")
        except Exception as e:
            print(f"[ERROR] tearDown: Exception during cleanup: {e}")

if __name__ == "__main__":
    unittest.main() 
