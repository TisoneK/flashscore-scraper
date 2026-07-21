import sys
import os
import time
import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Callable

# Import configuration
from src.utils.config_loader import CONFIG, SELECTORS, MIN_H2H_MATCHES

from src.driver_manager import WebDriverManager
from src.utils.selenium_utils import SeleniumUtils
from src.core.url_verifier import URLVerifier
from src.data.loader.match_data_loader import MatchDataLoader
from src.data.extractor.match_data_extractor import MatchDataExtractor
from src.data.loader.odds_data_loader import OddsDataLoader
from src.data.extractor.odds_data_extractor import OddsDataExtractor
from src.data.loader.h2h_data_loader import H2HDataLoader
from src.data.extractor.h2h_data_extractor import H2HDataExtractor
from src.models import MatchModel, OddsModel, H2HMatchModel
from src.storage.json_storage import JSONStorage
from src.core.network_monitor import NetworkMonitor
from src.core.retry_manager import NetworkRetryManager
from src.utils import setup_logging, ensure_logging_configured, get_logging_status
from datetime import datetime
from src.data.loader.results_data_loader import ResultsDataLoader
from src.data.extractor.results_data_extractor import ResultsDataExtractor
from src.core.performance_monitor import PerformanceMonitor
from typing import Protocol
from src.reporting import Reporter, CallbackReporter

# Global variables for logging paths
log_dir = CONFIG.get('logging', {}).get('log_directory', 'logs')
os.makedirs(log_dir, exist_ok=True)

# These will be set when scrape() is called
scraper_log_path = None
chrome_log_path = None

MAX_MATCHES = 3  # Limit for demo/testing

logger = logging.getLogger(__name__)

def get_ddmmyy_date(day: str) -> str:
    from datetime import datetime, timedelta
    if day == "Tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    else:
        return datetime.now().strftime("%Y%m%d")

class DriverManagerLike(Protocol):
    def initialize(self) -> None: ...
    def get_driver(self): ...
    def close(self, force: bool = False) -> None: ...



def _get_results_config():
    """Read results-scraper config from the env-config store (admin-managed).
    
    Returns a dict with:
      - max_workers: int (1-3, default 3)
      - incremental_push: bool (default True)
      - match_duration_minutes: int (default 170 = 2h50m)
      - priority_mode: str ('status' | 'time' | 'off', default 'status')
    """
    defaults = {
        # Serialize by default: one Chrome at a time. Each browser is dozens
        # of OS threads, and running 3 alongside the autonomous schedulers on
        # a small container exhausted the thread limit ("can't start new
        # thread"). Raise RESULTS_MAX_WORKERS only on a larger instance.
        "max_workers": 1,
        "incremental_push": True,
        "match_duration_minutes": 170,
        "priority_mode": "status",
    }
    try:
        from api.env_config_store import get_env_config
        mw = get_env_config("RESULTS_MAX_WORKERS")
        if mw:
            defaults["max_workers"] = max(1, min(3, int(mw)))
        ip = get_env_config("RESULTS_INCREMENTAL_PUSH")
        if ip:
            defaults["incremental_push"] = ip.lower() in ("true", "1", "yes", "on")
        md = get_env_config("RESULTS_MATCH_DURATION_MINUTES")
        if md:
            defaults["match_duration_minutes"] = max(30, min(600, int(md)))
        pm = get_env_config("RESULTS_PRIORITY_MODE")
        if pm:
            defaults["priority_mode"] = pm.lower()
    except Exception:
        logger.debug("Non-critical error (swallowed)")
    return defaults

class FlashscoreScraper:
    def __init__(
        self,
        status_callback=None,
        progress_callback=None,
        *,
        driver_factory: Optional[Callable[[], DriverManagerLike]] = None,
        storage: Optional[JSONStorage] = None,
        config_snapshot: Optional[Dict[str, Any]] = None,
        reporter: Optional[Reporter] = None,
    ):
        # Dependencies with safe defaults to preserve CLI behavior
        self._driver_manager = (driver_factory() if driver_factory else WebDriverManager(chrome_log_path=chrome_log_path))
        self._driver = None  # Private, use driver property
        self.selenium_utils = None
        self.url_verifier = None
        self.json_storage = storage if storage is not None else JSONStorage()
        self.match_loader = None
        self.odds_loader = None
        self.home_away_loader = None
        self.over_under_loader = None
        self.h2h_loader = None
        # Frozen config for this instance (optional)
        self.config = config_snapshot if config_snapshot is not None else CONFIG
        # Network resilience components
        self.network_monitor = NetworkMonitor()
        self.retry_manager = NetworkRetryManager()
        # Reporter abstraction; fallback to simple callbacks for backward compatibility
        self.reporter = reporter if reporter is not None else CallbackReporter(status_callback=status_callback, progress_callback=progress_callback, match_finalized_callback=None)
        # Back-compat field used by existing calls
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        
    def has_active_driver(self) -> bool:
        """Check if there's an active driver without creating a new one."""
        return getattr(self, "_driver", None) is not None

    @property
    def driver(self):
        """Get the current WebDriver instance."""
        # Check if we're in a global closing state (injected via CLI)
        if hasattr(self, '_is_closing') and self._is_closing:
            return None
            
        if self._driver is not None and not self._is_valid_driver_session():
            self._cleanup_driver()
            self._driver = None
            
        if self._driver is None and self._driver_manager is not None:
            self._driver = self._driver_manager.get_driver()
        return self._driver
        
    def _is_valid_driver_session(self):
        """Check if the current WebDriver session is still valid."""
        if self._driver is None:
            return False
            
        try:
            # Try to get the current URL - if this fails, the session is invalid
            _ = self._driver.current_url
            return True
        except Exception as e:
            logger.warning(f"WebDriver session is invalid: {str(e)}")
            return False
            
    def _cleanup_driver(self):
        """Safely clean up the WebDriver instance."""
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception as e:
                logger.warning(f"Error while cleaning up WebDriver: {str(e)}")
            finally:
                self._driver = None

    def initialize(self, status_callback=None):
        import time
        import threading
        start_time = time.time()
        timeout = 120  # 2 minutes hard timeout for initialization

        logger.info("🔄 Initializing scraper components...")

        if status_callback is None:
            status_callback = self.status_callback

        try:
            self.reporter.status("Launching browser and initializing driver...")

            # ── Create Chrome WebDriver with a HARD TIMEOUT ──────────────
            # The previous code called self.driver (which calls webdriver.Chrome())
            # directly — if Chrome hung during startup, the call would block
            # FOREVER with no way to recover. The declared `timeout = 90` was
            # never enforced.
            #
            # Now we run the driver creation in a separate thread and enforce
            # a real timeout. If Chrome doesn't start within 2 minutes, we
            # raise a TimeoutError so the scrape fails fast instead of
            # hanging indefinitely.
            driver_result = {"driver": None, "error": None}
            driver_created = threading.Event()

            def _create_driver():
                try:
                    # Initialize the driver manager first
                    self._driver_manager.initialize()
                    # Then trigger driver creation through the property
                    driver_result["driver"] = self.driver
                except Exception as e:
                    driver_result["error"] = e
                finally:
                    driver_created.set()

            driver_thread = threading.Thread(target=_create_driver, daemon=True)
            driver_thread.start()

            if not driver_created.wait(timeout=timeout):
                # Timed out — Chrome didn't start within 2 minutes
                elapsed = time.time() - start_time
                logger.error(f"❌ Chrome initialization timed out after {elapsed:.1f}s")
                # Try to kill any zombie Chrome that might be blocking
                try:
                    import subprocess
                    subprocess.run(["pkill", "-9", "-f", "chrome"], timeout=5, capture_output=True)
                    subprocess.run(["pkill", "-9", "-f", "chromedriver"], timeout=5, capture_output=True)
                    logger.info("Killed zombie Chrome/chromedriver processes")
                except Exception:
                    pass
                raise TimeoutError(f"Chrome failed to start within {timeout}s — likely a zombie process. Restart the service.")

            # Check if the driver creation thread raised an error
            if driver_result["error"]:
                raise driver_result["error"]

            driver = driver_result["driver"]
            elapsed = time.time() - start_time
            logger.info(f"✅ WebDriver created in {elapsed:.2f}s")

            self.reporter.status("Browser ready!")

            # Initialize utilities with the driver
            self.selenium_utils = SeleniumUtils(driver)
            self.url_verifier = URLVerifier(driver)

            # Start network monitoring (pass status_callback)
            self.network_monitor.start_monitoring(status_callback=status_callback)
            logger.info("Network monitoring started.")

            total_elapsed = time.time() - start_time
            logger.info(f"✅ Scraper initialization completed in {total_elapsed:.2f}s")

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Scraper initialization failed after {elapsed:.2f}s: {e}")
            # Ensure we clean up if initialization fails
            try:
                self.close()
            except Exception as close_error:
                logger.error(f"Error during cleanup after failed initialization: {close_error}")
            raise

    def load_initial_data(self, day="Today", status_callback=None):
        self.reporter.status('--- Loading main page ---')
        logger.info('--- Loading main page ---')
        self.match_loader = MatchDataLoader(self.driver, selenium_utils=self.selenium_utils)
        self.odds_loader = OddsDataLoader(self.driver, selenium_utils=self.selenium_utils)
        self.match_loader.load_main_page()
        logger.info('Main page loaded.')
        self.reporter.status('Main page loaded.')
        if day == "Tomorrow":
            logger.info("Loading tomorrow's matches...")
            self.reporter.status("Loading tomorrow's matches...")
            match_ids = self.match_loader.get_tomorrow_match_ids()
            self.reporter.status(f"Found {len(match_ids)} matches for tomorrow.")
        else:
            logger.info("Loading today's matches...")
            self.reporter.status("Loading today's matches...")
            match_ids = self.match_loader.get_today_match_ids()
            self.reporter.status(f"Found {len(match_ids)} matches for today.")
            if not match_ids:
                logger.info("No matches found for today. Checking tomorrow's schedule.")
                self.reporter.status("No matches found for today. Checking tomorrow's schedule.")
                match_ids = self.match_loader.get_tomorrow_match_ids()
                self.reporter.status(f"Found {len(match_ids)} matches for tomorrow.")
        return match_ids

    def check_and_get_processed_matches(self, day: str):
        """Return processed match ids and reasons for the given day.
        Ensures we read from the same daily file we write to.
        """
        file_date = get_ddmmyy_date(day)
        filename = f"matches_{file_date}.json"
        processed_matches = self.json_storage.get_processed_match_ids(filename=filename)
        processed_match_ids = {mid for mid, _ in processed_matches}
        processed_reasons = {mid: reason for mid, reason in processed_matches}
        return processed_match_ids, processed_reasons

    def _get_team_names_from_element(self, match_element):
        """Extract team names from a match element for better logging."""
        try:
            # Try multiple selector patterns for team names
            team_selectors = [
                # Primary selectors from config
                (SELECTORS['match']['teams']['home'], SELECTORS['match']['teams']['away']),
                # Alternative selectors that might work
                ('div.duelParticipant__home .participant__participantName', 'div.duelParticipant__away .participant__participantName'),
                ('div.event__participant--home', 'div.event__participant--away'),
                ('div.event__participant--home .event__participantName', 'div.event__participant--away .event__participantName'),
                # Fallback selectors
                ('div[class*="home"]', 'div[class*="away"]'),
                ('span[class*="home"]', 'span[class*="away"]')
            ]
            
            for home_selector, away_selector in team_selectors:
                try:
                    # Use selenium_utils instead of direct Selenium calls
                    home_team_element = self.selenium_utils.find_element_in_parent(match_element, "css", home_selector)
                    away_team_element = self.selenium_utils.find_element_in_parent(match_element, "css", away_selector)
                    
                    home_team = home_team_element.text.strip() if home_team_element and home_team_element.text else "Unknown"
                    away_team = away_team_element.text.strip() if away_team_element and away_team_element.text else "Unknown"
                    
                    # Only return if we got valid team names
                    if home_team != "Unknown" and away_team != "Unknown":
                        return f"{home_team} vs {away_team}"
                        
                except Exception:
                    # Try next selector pattern
                    continue
            
            # If no selectors worked, return None
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract team names from match element: {e}")
            return None

    def load_match_details(self, match_element, status_callback=None):
        # Create a proper UrlBuilder instance from the match element
        from src.core.url_builder import UrlBuilder
        
        try:
            # Create UrlBuilder directly from the match element
            url_builder = UrlBuilder.from_element(match_element)
            
            # Store the UrlBuilder for later use in odds and H2H loading
            self.current_url_builder = url_builder
            
            # Get match ID for logging
            element_id = match_element.get_attribute('id')
            match_id = element_id.split('_')[-1] if element_id and element_id.startswith('g_3_') else 'unknown'
            
            # Try to get team names for better logging
            team_names = self._get_team_names_from_element(match_element)
            match_display = team_names if team_names else f"match {match_id}"
            
            self.reporter.status(f"Loading match details for {match_display}...")
                
            return self.match_loader.load_match(url_builder, status_callback=status_callback)
            
        except Exception as e:
            logger.error(f"Error creating UrlBuilder from match element: {e}")
            self.reporter.status(f"Error loading match: {str(e)}")
            return False

    def extract_match_data(self, status_callback=None):
        extractor = MatchDataExtractor(self.match_loader)
        return extractor.extract_match_data(status_callback=status_callback)

    def load_home_away_odds(self, match_id, status_callback=None):
        if self.driver is None:
            return False
        
        # Use the stored UrlBuilder if available
        if not hasattr(self, 'current_url_builder') or self.current_url_builder is None:
            logger.error(f"No UrlBuilder available for match {match_id}")
            return False
            
        self.home_away_loader = OddsDataLoader(self.driver, selenium_utils=self.selenium_utils)
        
        try:
            return self.home_away_loader.load_home_away_odds(self.current_url_builder, status_callback=status_callback)
        except Exception as e:
            logger.error(f"Error loading home/away odds for match {match_id}: {e}")
            return False

    def extract_home_away_odds(self, status_callback=None):
        home_away_extractor = OddsDataExtractor(self.home_away_loader)
        # Extract the odds data properly
        odds_data = home_away_extractor.extract_home_away_odds(status_callback=status_callback)
        home_odds = float(odds_data['home_odds']) if odds_data['home_odds'] else None
        away_odds = float(odds_data['away_odds']) if odds_data['away_odds'] else None
        return home_odds, away_odds

    def load_over_under_odds(self, match_id, status_callback=None):
        if self.driver is None:
            return False
        
        # Use the stored UrlBuilder if available
        if not hasattr(self, 'current_url_builder') or self.current_url_builder is None:
            logger.error(f"No UrlBuilder available for match {match_id}")
            return False
            
        self.over_under_loader = OddsDataLoader(self.driver, selenium_utils=self.selenium_utils)
        
        try:
            return self.over_under_loader.load_over_under_odds(self.current_url_builder, status_callback=status_callback)
        except Exception as e:
            logger.error(f"Error loading over/under odds for match {match_id}: {e}")
            return False

    def extract_over_under_odds(self, status_callback=None):
        """Extract calculation line + reduced-risk lines. Returns a dict."""
        over_under_extractor = OddsDataExtractor(self.over_under_loader)
        selected = over_under_extractor.get_selected_alternative()
        if selected:
            match_total = float(selected['alternative']) if selected['alternative'] else None
            over_odds = float(selected['over']) if selected['over'] else None
            under_odds = float(selected['under']) if selected['under'] else None

            reduced_over = over_under_extractor.get_lowest_alternative()
            reduced_under = over_under_extractor.get_highest_alternative()

            return {
                'match_total': match_total,
                'over_odds': over_odds,
                'under_odds': under_odds,
                'reduced_over_total': float(reduced_over['alternative']) if reduced_over and reduced_over.get('alternative') else None,
                'reduced_over_odds': float(reduced_over['over']) if reduced_over and reduced_over.get('over') else None,
                'reduced_under_total': float(reduced_under['alternative']) if reduced_under and reduced_under.get('alternative') else None,
                'reduced_under_odds': float(reduced_under['under']) if reduced_under and reduced_under.get('under') else None,
            }
        return {
            'match_total': None, 'over_odds': None, 'under_odds': None,
            'reduced_over_total': None, 'reduced_over_odds': None,
            'reduced_under_total': None, 'reduced_under_odds': None,
        }

    def load_h2h_data(self, match_id, status_callback=None):
        if self.driver is None:
            return False
        
        # Use the stored UrlBuilder if available
        if not hasattr(self, 'current_url_builder') or self.current_url_builder is None:
            logger.error(f"No UrlBuilder available for match {match_id}")
            return False
            
        self.h2h_loader = H2HDataLoader(self.driver, selenium_utils=self.selenium_utils)
        
        try:
            return self.h2h_loader.load_h2h(self.current_url_builder, status_callback=status_callback)
        except Exception as e:
            logger.error(f"Error loading H2H data for match {match_id}: {e}")
            return False

    def extract_h2h_matches(self, match_id, status_callback=None):
        if self.h2h_loader is None:
            return [], 0
        h2h_extractor = H2HDataExtractor(self.h2h_loader)
        h2h_matches = []
        h2h_data = h2h_extractor.extract_h2h_data(status_callback=status_callback)
        for j in range(len(h2h_data)):
            date = h2h_extractor.get_date(j)
            home_team = h2h_extractor.get_home_team(j)
            away_team = h2h_extractor.get_away_team(j)
            home_score = h2h_extractor.get_home_score(j)
            away_score = h2h_extractor.get_away_score(j)
            competition = h2h_extractor.get_competition(j)
            # Validate and convert scores to integers safely
            def safe_int_conversion(score_str, field_name):
                if score_str is None:
                    return 0
                try:
                    # Check if the string contains only digits (and possibly a dash for no score)
                    if score_str.strip() and score_str.strip().replace('-', '').isdigit():
                        return int(score_str.strip())
                    else:
                        logger.debug(f"Skipping invalid {field_name} value: '{score_str}'")
                        return 0
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Error converting {field_name} '{score_str}' to int: {e}")
                    return 0
            
            home_score_int = safe_int_conversion(home_score, 'home_score')
            away_score_int = safe_int_conversion(away_score, 'away_score')
            
            h2h_match = H2HMatchModel(
                match_id=match_id,
                date=date or "",
                home_team=home_team or "",
                away_team=away_team or "",
                home_score=home_score_int,
                away_score=away_score_int,
                competition=competition or ""
            )
            h2h_matches.append(h2h_match)
        return h2h_matches, self.h2h_loader.get_h2h_count()

    def validate_odds_data(self, odds):
        missing_odds_fields = []
        # For scheduled matches: home/away odds are optional, over/under odds are compulsory
        if odds.home_odds is None:
            logger.warning("Missing home_odds - 1X2 odds unavailable")
        if odds.away_odds is None:
            logger.warning("Missing away_odds - 1X2 odds unavailable")
        
        # Over/under odds are compulsory for scheduled matches
        if odds.match_total is None:
            missing_odds_fields.append('match_total')
        if odds.over_odds is None:
            missing_odds_fields.append('over_odds')
        if odds.under_odds is None:
            missing_odds_fields.append('under_odds')
        
        return bool(missing_odds_fields), missing_odds_fields

    def compose_skip_reason(self, odds_incomplete, missing_odds_fields, h2h_count):
        reasons = []
        if odds_incomplete:
            reasons.append(f"missing or invalid odds fields: {', '.join(missing_odds_fields)}")
        if h2h_count < MIN_H2H_MATCHES:
            reasons.append(f"insufficient H2H matches ({h2h_count} found, {MIN_H2H_MATCHES} required)")
        return "; ".join(reasons)

    def save_match_data(self, match, day="Today"):
        file_date = get_ddmmyy_date(day)
        filename = f"matches_{file_date}.json"
        self.json_storage.save_matches([match], filename=filename)

    @staticmethod
    def log_match_info(match):
        lines = []
        lines.append("\nMatch Info:")
        lines.append(f"  ID: {match.match_id}")
        lines.append(f"  Country: {match.country}")
        lines.append(f"  League: {match.league}")
        lines.append(f"  Home Team: {match.home_team}")
        lines.append(f"  Away Team: {match.away_team}")
        lines.append(f"  Date: {match.date}")
        lines.append(f"  Time: {match.time}")
        lines.append(f"  Created At: {match.created_at}")
        lines.append(f"  Status: {match.status}")
        if match.skip_reason:
            lines.append(f"  Skip Reason: {match.skip_reason}")
        if match.odds:
            lines.append("  Odds:")
            lines.append(f"    Home Odds: {match.odds.home_odds}")
            lines.append(f"    Away Odds: {match.odds.away_odds}")
            lines.append(f"    Over Odds: {match.odds.over_odds}")
            lines.append(f"    Under Odds: {match.odds.under_odds}")
            lines.append(f"    Match Total: {match.odds.match_total}")
        if match.h2h_matches:
            lines.append(f"  H2H Matches ({len(match.h2h_matches)}):")
            for i, h2h in enumerate(match.h2h_matches, 1):
                lines.append(f"    H2H {i}: {h2h.date} {h2h.home_team} {h2h.home_score} - {h2h.away_score} {h2h.away_team} ({h2h.competition})")
        lines.append("")
        log_text = '\n'.join(lines)
        # Only log detailed block at INFO if explicitly enabled; otherwise, use DEBUG
        try:
            verbose_details = CONFIG.get('logging', {}).get('log_match_details', False)
        except Exception:
            verbose_details = False
        if verbose_details:
            logger.info(log_text)
        else:
            logger.debug(log_text)

    def close(self):
        """
        Close all resources and cleanup.
        Fast path for shutdown - no network calls, no window enumeration.
        """
        logger.debug("🛑 Starting scraper cleanup...")
        
        try:
            # Mark current thread as shutting down to suppress retry warnings.
            #
            # WARNING: this flag is read by retry_manager.retry_network_operation()
            # via `threading.current_thread()._is_shutting_down`. Because api_server
            # uses a ThreadPoolExecutor(max_workers=1), the SAME worker thread is
            # reused for the next scrape — so this flag MUST be cleared back to
            # False at the start of the next run, otherwise the next scrape dies
            # immediately with "Operation cancelled by shutdown".
            #
            # That clear lives in api_server.py:_run_scheduled_scrape and
            # api_server.py:_run_results_scrape. If you remove or move this
            # `= True` line, also update those clears. If you remove the clears,
            # every scrape after the first will fail. See commit 5a7a594 / 16d39a7.
            import threading
            threading.current_thread()._is_shutting_down = True
            
            # Mark scraper as closing to prevent new operations
            self._is_closing = True
            
            # Stop network monitoring with suppressed logs
            if hasattr(self, 'network_monitor') and self.network_monitor is not None:
                try:
                    self.network_monitor.stop_monitoring(suppress_logs=True)
                except Exception as e:
                    logger.debug(f"Network monitor stop failed: {e}")
            
            # Disable urllib3 retries during cleanup to prevent connection attempts
            try:
                import urllib3
                urllib3.disable_warnings()
                # Temporarily disable retries
                from urllib3.util.retry import Retry
                original_retry = urllib3.util.retry.Retry.DEFAULT
                urllib3.util.retry.Retry.DEFAULT = Retry(total=0, connect=0, read=0, redirect=0, status=0, backoff_factor=0)
            except Exception:
                pass  # If urllib3 configuration fails, continue with cleanup
            
            # Fast path: just quit the driver once, then force cleanup
            if self._driver is not None:
                try:
                    # Set a short timeout for driver operations during cleanup
                    self._driver.implicitly_wait(0.1)
                    self._driver.quit()
                except Exception as e:
                    logger.debug(f"Driver quit failed during shutdown: {e}")
                finally:
                    self._driver = None
            
            # Force close driver manager
            if hasattr(self, '_driver_manager') and self._driver_manager is not None:
                try:
                    self._driver_manager.close(force=True)
                except Exception as e:
                    logger.debug(f"Driver manager close failed: {e}")
                finally:
                    self._driver_manager = None
            
            # Clear other references
            for attr in ['selenium_utils', 'url_verifier', 'json_storage', 'retry_manager', 'network_monitor']:
                if hasattr(self, attr):
                    setattr(self, attr, None)
            
            # Clear callbacks
            if hasattr(self, 'status_callback'):
                self.status_callback = None
                
            # Restore urllib3 retries if we modified them
            try:
                if 'original_retry' in locals():
                    urllib3.util.retry.Retry.DEFAULT = original_retry
            except Exception:
                logger.debug("Non-critical error (swallowed)")
                
        except Exception as e:
            logger.debug(f"Error during cleanup: {e}")
        finally:
            logger.debug("✅ Scraper cleanup completed")

    def scrape(self, progress_callback=None, day="Today", status_callback=None, stop_callback=None, force=False):
        global scraper_log_path, chrome_log_path
        
        # Set up log file paths based on the day parameter
        file_date = get_ddmmyy_date(day)
        scraper_log_path = os.path.join(log_dir, f"scraper_{file_date}.log")
        chrome_log_path = os.path.join(log_dir, f"chrome_{file_date}.log")
        
        # Ensure logging is properly configured with the correct log file
        ensure_logging_configured(scraper_log_path)
        
        # Update the WebDriverManager with the new chrome log path
        if hasattr(self, '_driver_manager') and self._driver_manager:
            self._driver_manager.chrome_log_path = chrome_log_path
        logger.info(f"=== Starting scraping for {day} ===")
        if status_callback:
            status_callback(f"=== Starting scraping for {day} ===")
        self.initialize(status_callback=status_callback)

        # If a progress/status callback is provided at call-time, refresh the reporter to use it
        try:
            if progress_callback is not None or status_callback is not None:
                from src.reporting import CallbackReporter
                effective_status_cb = status_callback if status_callback is not None else getattr(self, 'status_callback', None)
                effective_progress_cb = progress_callback if progress_callback is not None else None
                # Preserve any existing match_finalized callback if already configured by caller
                existing_match_finalized_cb = None
                try:
                    if isinstance(self.reporter, CallbackReporter):
                        existing_match_finalized_cb = getattr(self.reporter, '_match_finalized_cb', None)
                except Exception:
                    existing_match_finalized_cb = None
                self.reporter = CallbackReporter(
                    status_callback=effective_status_cb,
                    progress_callback=effective_progress_cb,
                    match_finalized_callback=existing_match_finalized_cb
                )
        except Exception:
            logger.debug("Non-critical error (swallowed)")
        try:
            def main_scrape():
                match_ids = self.load_initial_data(day, status_callback=status_callback)
                if not match_ids:
                    self.reporter.status("No matches found for scraping.")
                    return []

                processed_match_ids, processed_reasons = self.check_and_get_processed_matches(day)

                # Check the website DB for matches that already have predictions.
                # This skips matches that have already been scraped + predicted,
                # avoiding redundant work.
                existing_db_ids = set()
                try:
                    import requests
                    website_url = os.environ.get("SCOREWISE_WEBHOOK_URL", "")
                    # Derive the website base URL from the engine webhook URL
                    # (the webhook URL points to the engine, not the website)
                    # We use a dedicated env var or the service config.
                    # For now, try the website URL from env or config.
                    from api.env_config_store import get_env_config
                    # The website's predictions endpoint is public (no auth for the exists check)
                    # We need the website URL — try WEBSITE_URL env or derive from known pattern
                    website_base = os.environ.get("WEBSITE_URL", "https://scorewise-ke.vercel.app")
                    resp = requests.get(f"{website_base}/api/predictions/exists", timeout=10)
                    if resp.ok:
                        data = resp.json()
                        existing_db_ids = set(data.get("match_ids", []))
                        if existing_db_ids:
                            logger.info(f"Found {len(existing_db_ids)} existing predictions in DB — will skip those matches")
                except Exception as e:
                    logger.debug(f"Could not check existing predictions in DB: {e}")
                    # Non-fatal — proceed with all matches if DB check fails

                if force:
                    logger.info(
                        "FORCE re-scrape: ignoring skip lists "
                        f"({len(processed_match_ids)} in day file, {len(existing_db_ids)} in website DB "
                        "would have been skipped) — re-processing everything"
                    )
                    processed_match_ids, processed_reasons = set(), {}
                    existing_db_ids = set()

                # Collect immutable URLs upfront (no fallbacks)
                url_snapshots = self.match_loader.collect_match_urls()
                # Align to ids discovered earlier: filter/keep ordering based on match_ids
                mid_to_urls = {u['mid']: u for u in url_snapshots}
                
                matches = []  # Initialize matches list inside main_scrape
                MAX_MATCHES = len(match_ids)

                for i, match_id in enumerate(match_ids[:MAX_MATCHES]):
                    if match_id not in mid_to_urls:
                        # Skip if no URL captured for this ID per 'no fallbacks' rule
                        logger.warning(f"Skipping match {match_id}: no captured URL found")
                        continue
                    # Check for stop signal
                    if stop_callback and stop_callback():
                        logger.info("🛑 Stop signal received, stopping scraper...")
                        self.reporter.status("🛑 Stop signal received, stopping scraper...")
                        break
                    
                    match_display = f"match {match_id}"
                    
                    self.reporter.progress(i+1, MAX_MATCHES, "Loading match data")
                    logger.info(f'Processing {match_display} ({i+1}/{MAX_MATCHES})')
                    if match_id in processed_match_ids:
                        msg = f"Skipping already processed match: {match_display} (reason: {processed_reasons.get(match_id, 'already processed')})"
                        logger.info(msg)
                        if status_callback:
                            status_callback(msg)
                        continue

                    # Skip matches that already have predictions in the website DB
                    if match_id in existing_db_ids:
                        msg = f"Skipping match with existing prediction in DB: {match_display}"
                        logger.info(msg)
                        if status_callback:
                            status_callback(msg)
                        continue

                    msg = f"Processing {match_display}..."
                    self.reporter.status(msg)
                    logger.info(msg)

                    # Build UrlBuilder from captured summary URL
                    from src.core.url_builder import UrlBuilder
                    summary_url = mid_to_urls[match_id]['summary']
                    self.current_url_builder = UrlBuilder.from_summary_url(summary_url)
                    self.reporter.progress(i+1, MAX_MATCHES, "Loading match page")
                    if self.match_loader.load_match(self.current_url_builder, status_callback=status_callback):
                        # For scheduled matches, we don't need to check status - we know they are scheduled
                        # and we want to process them to get odds and H2H data
                        
                        self.reporter.progress(i+1, MAX_MATCHES, "Extracting match data")
                        match_data = self.extract_match_data(status_callback=status_callback)
                        odds = OddsModel(match_id=match_id)

                        # Load odds data for scheduled matches
                        self.reporter.progress(i+1, MAX_MATCHES, "Extracting odds data")
                        if self.load_home_away_odds(match_id, status_callback=status_callback):
                            odds.home_odds, odds.away_odds = self.extract_home_away_odds(status_callback=status_callback)
                        else:
                            warn_msg = f'  - Failed to load home/away odds for {match_display}'
                            logger.warning(warn_msg)
                            self.reporter.status(warn_msg)

                        if self.load_over_under_odds(match_id, status_callback=status_callback):
                            ou = self.extract_over_under_odds(status_callback=status_callback)
                            odds.match_total = ou['match_total']
                            odds.over_odds = ou['over_odds']
                            odds.under_odds = ou['under_odds']
                            odds.reduced_over_total = ou.get('reduced_over_total')
                            odds.reduced_over_odds = ou.get('reduced_over_odds')
                            odds.reduced_under_total = ou.get('reduced_under_total')
                            odds.reduced_under_odds = ou.get('reduced_under_odds')
                            if odds.match_total is None:
                                warn_msg = f"  - No selected over/under alternative available for {match_display}"
                                logger.warning(warn_msg)
                                self.reporter.status(warn_msg)
                        else:
                            warn_msg = f'  - Failed to load over/under odds for {match_display}'
                            logger.warning(warn_msg)
                            self.reporter.status(warn_msg)

                        odds_incomplete, missing_odds_fields = self.validate_odds_data(odds)
                        if odds_incomplete:
                            warn_msg = f"  - Missing compulsory odds fields for {match_display}: {', '.join(missing_odds_fields)}"
                            logger.warning(warn_msg)
                            self.reporter.status(warn_msg)

                        # Load H2H data for scheduled matches
                        self.reporter.progress(i+1, MAX_MATCHES, "Loading H2H data")
                        h2h_matches = []
                        h2h_count = 0
                        if self.load_h2h_data(match_id, status_callback=status_callback):
                            try:
                                h2h_matches, h2h_count = self.extract_h2h_matches(match_id, status_callback=status_callback)
                                # If the loader explicitly indicated 'no H2H data' for this match,
                                # treat it as a valid empty state and do not mark it as a warning
                                try:
                                    if hasattr(self, 'h2h_loader') and self.h2h_loader is not None and self.h2h_loader.is_explicit_empty():
                                        info_msg = f"  - No H2H matches available for {match_display} (expected)"
                                        logger.info(info_msg)
                                        self.reporter.status(info_msg)
                                        # Keep h2h_matches as empty and h2h_count as 0; do not add warning
                                        explicit_empty = True
                                    else:
                                        explicit_empty = False
                                except Exception:
                                    explicit_empty = False
                            except Exception as e:
                                logger.warning(f"Failed to extract H2H data for match {match_id}: {e}")
                                self.reporter.status(f"Skipping H2H data for match {match_id} due to extraction error")
                                h2h_matches, h2h_count = [], 0
                            
                            msg = f'  - H2H matches found: {h2h_count} (required: {MIN_H2H_MATCHES})'
                            logger.info(msg)
                            self.reporter.status(msg)
                            # Only warn about insufficient H2H matches when not an explicit empty state
                            if not explicit_empty and h2h_count < MIN_H2H_MATCHES:
                                warn_msg = f'  - Insufficient H2H matches for {match_display}: {h2h_count} found, {MIN_H2H_MATCHES} required'
                                logger.warning(warn_msg)
                                self.reporter.status(warn_msg)
                        else:
                            warn_msg = f'  - Failed to load H2H data for {match_display}'
                            logger.warning(warn_msg)
                            self.reporter.status(warn_msg)

                        skip_reason = self.compose_skip_reason(odds_incomplete, missing_odds_fields, h2h_count)
                        status = "complete" if not skip_reason else "incomplete"

                        match = MatchModel(
                            match_id=match_id,
                            country=match_data.country or "",
                            league=match_data.league or "",
                            home_team=match_data.home_team or "",
                            away_team=match_data.away_team or "",
                            date=match_data.date or "",
                            time=match_data.time or "",
                            odds=odds,
                            h2h_matches=h2h_matches,
                            status=status,
                            skip_reason=skip_reason
                        )
                        matches.append(match)
                        self.reporter.progress(i+1, MAX_MATCHES, "Saving match data")
                        self.save_match_data(match, day=day)
                        # Emit match finalized event after data is saved
                        try:
                            # Pass the match dict so streaming consumers can forward
                            # it to the prediction engine without re-reading the file.
                            # Only forward complete matches (incomplete ones lack
                            # the odds/H2H data the engine needs).
                            match_payload = match.to_dict() if match.status == "complete" else None
                            self.reporter.match_finalized(match_id, match=match_payload)
                        except Exception:
                            logger.debug("Non-critical error (swallowed)")
                        # Log this match's full info immediately after processing
                        FlashscoreScraper.log_match_info(match)
                    else:
                        warn_msg = f'  - Failed to load/verify match page for {match_display}'
                        logger.warning(warn_msg)
                        if status_callback:
                            status_callback(warn_msg)
                        continue

                summary_msg = f"\n--- Summary: Collected {len(matches)} matches for {day.lower()} ---"
                logger.info(summary_msg)
                self.reporter.status(summary_msg)
                # Optionally emit detailed per-match blocks after saving
                try:
                    verbose_details = CONFIG.get('logging', {}).get('log_match_details', False)
                except Exception:
                    verbose_details = False
                if verbose_details:
                    for m in matches:
                        FlashscoreScraper.log_match_info(m)
                
                return matches  # Return the matches list

            # Run the main scrape with retry logic and get the matches
            # Pass cooperative stop checker so retries bail out during shutdown
            matches = self.retry_manager.retry_network_operation(main_scrape, stop_checker=(stop_callback if callable(stop_callback) else None))
            
            # Handle case where main_scrape returns None or empty list
            if matches is None:
                matches = []
            
            # Return the results
            return {
                'total_collected': len(matches),
                'new_matches': len(matches),
                'skipped_matches': 0,
                'complete_matches': len([m for m in matches if m.status == 'complete']),
                'incomplete_matches': len([m for m in matches if m.status != 'complete']),
                'matches': matches
            }
        finally:
            self.close()

    def scrape_results(self, date, status_callback=None, progress_callback=None):
        """
        Scrape final results for a given date. Only process matches with status 'finished'.
        Uses ResultsDataLoader and ResultsDataExtractor, and PerformanceMonitor.
        Loads match IDs from the JSON file for the given date.
        """
        results_config = _get_results_config()
        logger.info(f"=== Starting results scraping for {date} (incremental={results_config['incremental_push']}, mode={results_config['priority_mode']}) ===")
        if status_callback:
            status_callback(f"=== Starting results scraping for {date} ===")
        self.initialize(status_callback=status_callback)
        perf_monitor = PerformanceMonitor()
        try:
            def main_results_scrape():
                import threading
                from concurrent.futures import ThreadPoolExecutor, as_completed

                # ── Fetch match IDs with priority info from the website ──────
                # The website returns matches grouped by priority:
                #   high   = AWAITING_RESULT (likely finished, need final scores)
                #   medium = LIVE (in-progress, need live score updates)
                #   low    = PENDING (scheduled, haven't started yet)
                #   done   = FINAL (already has result, skip)
                match_ids = []
                priority_buckets = {"high": [], "medium": [], "low": []}

                # Strategy 1: Try local JSON file
                file_date = date.replace('.', '')
                filename = f"matches_{file_date}.json"
                try:
                    matches = self.json_storage.load_matches(filename)
                    match_ids = [m.match_id for m in matches]
                    if match_ids:
                        logger.info(f"Loaded {len(match_ids)} match IDs from {filename}")
                except Exception as e:
                    logger.warning(f"Could not load matches from {filename}: {e}")

                # Strategy 2: Fall back to website DB with priority info
                if not match_ids:
                    try:
                        from api.env_config_store import get_env_config
                        website_url = get_env_config("SCOREWISE_WEBSITE_URL")
                    except ImportError:
                        website_url = os.environ.get("SCOREWISE_WEBSITE_URL", "")

                    if website_url:
                        try:
                            import requests
                            # Fetch with priority info so we can sort by importance
                            resp = requests.get(
                                f"{website_url.rstrip('/')}/api/predictions/exists?with_priority=true&match_duration={results_config.get('match_duration_minutes', 170)}",
                                timeout=15,
                            )
                            if resp.ok:
                                data = resp.json()
                                match_ids = data.get("match_ids", [])
                                by_priority = data.get("by_priority", {})
                                priority_buckets["high"] = [m["match_id"] for m in by_priority.get("high", [])]
                                priority_buckets["medium"] = [m["match_id"] for m in by_priority.get("medium", [])]
                                priority_buckets["low"] = [m["match_id"] for m in by_priority.get("low", [])]
                                counts = data.get("priority_counts", {})
                                logger.info(
                                    f"Fetched {len(match_ids)} match IDs from website DB "
                                    f"(high={counts.get('high', 0)}, medium={counts.get('medium', 0)}, "
                                    f"low={counts.get('low', 0)}, done={counts.get('done', 0)})"
                                )
                        except Exception as fetch_err:
                            logger.error(f"Failed to fetch match IDs from website: {fetch_err}")
                    else:
                        logger.warning(
                            "SCOREWISE_WEBSITE_URL not set — cannot fall back to website DB "
                            "for match IDs. Results scrape will be empty."
                        )

                if not match_ids:
                    msg = f"No matches found for results scraping on {date}."
                    logger.info(msg)
                    if status_callback:
                        status_callback(msg)
                    return

                # ── Sort match IDs by priority ──────────────────────────────
                # If we have priority buckets from the website, ONLY process
                # non-done matches (high + medium + low). Skip "done" matches
                # (already FINAL/POSTPONED/CANCELLED) — no need to re-visit
                # Flashscore pages for matches we already have results for.
                if priority_buckets["high"] or priority_buckets["medium"] or priority_buckets["low"]:
                    match_ids = priority_buckets["high"] + priority_buckets["medium"] + priority_buckets["low"]
                    done_count = len(data.get("by_priority", {}).get("done", [])) if 'data' in locals() else 0
                    logger.info(
                        f"Sorted by priority: {len(priority_buckets['high'])} high → "
                        f"{len(priority_buckets['medium'])} medium → "
                        f"{len(priority_buckets['low'])} low "
                        f"({done_count} done — skipped)"
                    )

                found_msg = f"Found {len(match_ids)} matches for results scraping on {date}."
                logger.info(found_msg)
                if status_callback:
                    status_callback(found_msg)

                # ── Incremental push helper ────────────────────────────────
                # Push a single result to the website immediately after extraction.
                # This way users see updates in real-time instead of waiting for
                # the entire scrape to finish.
                push_lock = threading.Lock()
                push_count = [0]  # mutable counter for the closure

                def push_result_incremental(result):
                    """Push a single result to the website immediately."""
                    try:
                        from webhook_utils import forward_results_to_website
                        try:
                            from api.env_config_store import get_env_config
                            wurl = get_env_config("SCOREWISE_WEBSITE_URL")
                            wsecret = get_env_config("SCOREWISE_WEBHOOK_SECRET")
                        except ImportError:
                            wurl = os.environ.get("SCOREWISE_WEBSITE_URL", "")
                            wsecret = os.environ.get("SCOREWISE_WEBHOOK_SECRET", "")
                        if wurl and wsecret:
                            with push_lock:
                                push_count[0] += 1
                            forward_results_to_website(
                                results=[result],
                                website_url=wurl,
                                webhook_secret=wsecret,
                                date_str=date,
                                source="flashscore-scraper",
                            )
                    except Exception as e:
                        logger.debug(f"Incremental push failed for {result.get('match_id')}: {e}")

                # ── Single-browser processing (shared driver) ───────────────
                # Note: Selenium WebDriver is NOT thread-safe for the same driver
                # instance. We use a single browser and process matches sequentially
                # in priority order. The priority sorting ensures users see the most
                # important results (FINISHED) first, then LIVE updates, then PENDING.
                #
                # For true multi-instance parallelism, each thread would need its own
                # FlashscoreScraper + browser. That's memory-intensive on Railway
                # (each Chrome instance uses ~300MB). The priority ordering + incremental
                # push gives most of the benefit without the memory cost.
                results_loader = ResultsDataLoader(self.driver, selenium_utils=self.selenium_utils)
                extractor = ResultsDataExtractor(results_loader)
                all_results = []
                total = len(match_ids)
                for i, match_id in enumerate(match_ids):
                    if progress_callback:
                        progress_callback(i+1, total)
                    progress_msg = f"Processing match {i+1}/{total}: {match_id}"
                    if status_callback:
                        status_callback(progress_msg)
                    # Load match summary page
                    if isinstance(match_id, str):
                        loaded = results_loader.load_match_summary_by_id(match_id, status_callback=status_callback)
                    else:
                        loaded = results_loader.load_match_summary(match_id, status_callback=status_callback)
                    if not loaded:
                        warn_msg = f"Failed to load match summary for {match_id}"
                        logger.warning(warn_msg)
                        if status_callback:
                            status_callback(warn_msg)
                        continue
                    elements = results_loader.get_elements()
                    # Extract match status + scores for ALL matches
                    match_status = extractor.extract_match_status(elements, status_callback=status_callback)
                    home_score, away_score = extractor.extract_final_scores(elements, status_callback=status_callback)
                    result = {
                        "match_id": match_id,
                        "home_score": home_score,
                        "away_score": away_score,
                        "status": match_status or "UNKNOWN",
                    }
                    all_results.append(result)
                    status_msg = f"Match {match_id}: status='{match_status}', scores={home_score}-{away_score}"
                    logger.info(status_msg)

                    # ── Incremental push — send this result to the website NOW ──
                    # (only if RESULTS_INCREMENTAL_PUSH is enabled, which it is by default)
                    if results_config.get("incremental_push", True):
                        # Users see the update within seconds instead of waiting for
                        # all 101 matches to finish processing.
                        push_result_incremental(result)

                # Save all results to local JSON
                results_filename = f"results_{file_date}.json"
                self.json_storage.save_results(all_results, filename=results_filename)
                summary_msg = (
                    f"\n--- Results scraping summary: {len(all_results)} matches processed "
                    f"for {date} ({push_count[0]} pushed incrementally) ---"
                )
                logger.info(summary_msg)
                if status_callback:
                    status_callback(summary_msg)

                # Final batch push (catches any that failed the incremental push)
                try:
                    from webhook_utils import forward_results_to_website
                    try:
                        from api.env_config_store import get_env_config
                        website_url = get_env_config("SCOREWISE_WEBSITE_URL")
                        webhook_secret = get_env_config("SCOREWISE_WEBHOOK_SECRET")
                    except ImportError:
                        website_url = os.environ.get("SCOREWISE_WEBSITE_URL", "")
                        webhook_secret = os.environ.get("SCOREWISE_WEBHOOK_SECRET", "")
                    if website_url and webhook_secret and all_results:
                        push_msg = f"Final batch push: {len(all_results)} result(s) to website..."
                        logger.info(push_msg)
                        if status_callback:
                            status_callback(push_msg)
                        success = forward_results_to_website(
                            results=all_results,
                            website_url=website_url,
                            webhook_secret=webhook_secret,
                            date_str=date,
                            source="flashscore-scraper",
                        )
                        outcome_msg = f"Final batch push to website: {'SUCCESS' if success else 'FAILED'}"
                        logger.info(outcome_msg)
                        if status_callback:
                            status_callback(outcome_msg)
                    elif not website_url:
                        logger.info("SCOREWISE_WEBSITE_URL not set — skipping results push to website.")
                    elif not webhook_secret:
                        logger.info("SCOREWISE_WEBHOOK_SECRET not set — skipping results push to website.")
                except Exception as push_err:
                    logger.error(f"Failed to push results to website: {push_err}")
                    if status_callback:
                        status_callback(f"Failed to push results to website: {push_err}")

            # Run with retry logic
            self.retry_manager.retry_network_operation(main_results_scrape)
        finally:
            perf_monitor.stop_resource_monitoring()
            self.close()

    def scrape_results_concurrent(self, date, status_callback=None, progress_callback=None):
        """Scrape results using MULTIPLE browser instances for faster updates.

        Spawns 3 concurrent FlashscoreScraper instances, each with its own browser:
          - Instance 1: HIGH priority (AWAITING_RESULT — likely finished)
          - Instance 2: MEDIUM priority (LIVE — in-progress)
          - Instance 3: LOW priority (PENDING — scheduled)

        Each instance processes its bucket independently and pushes results
        to the website incrementally (after each match). This means:
          - Users see FINAL results within seconds (high priority bucket finishes first)
          - LIVE scores update while the high-priority bucket is still running
          - PENDING matches are checked last (lowest priority, rarely need updates)

        Falls back to single-instance scrape_results() if:
          - The website doesn't support ?with_priority=true
          - There aren't enough matches to justify 3 browsers
          - Memory is constrained (each Chrome instance uses ~300MB)

        Args:
            date: Date string in DD.MM.YYYY format
            status_callback: Optional callback for status updates
            progress_callback: Optional callback for progress updates
        """
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results_config = _get_results_config()
        logger.info(f"=== Starting CONCURRENT results scraping for {date} (max_workers={results_config['max_workers']}, incremental={results_config['incremental_push']}, mode={results_config['priority_mode']}) ===")
        if status_callback:
            status_callback(f"=== Starting concurrent results scraping for {date} ===")

        # Fetch match IDs with priority info from the website
        try:
            from api.env_config_store import get_env_config
            website_url = get_env_config("SCOREWISE_WEBSITE_URL")
        except ImportError:
            website_url = os.environ.get("SCOREWISE_WEBSITE_URL", "")

        if not website_url:
            logger.warning("SCOREWISE_WEBSITE_URL not set — falling back to single-instance scrape")
            return self.scrape_results(date, status_callback, progress_callback)

        try:
            import requests
            resp = requests.get(
                f"{website_url.rstrip('/')}/api/predictions/exists?with_priority=true&match_duration={results_config.get('match_duration_minutes', 170)}",
                timeout=15,
            )
            if not resp.ok:
                logger.warning(f"Website returned {resp.status_code} — falling back to single-instance")
                return self.scrape_results(date, status_callback, progress_callback)

            data = resp.json()
            by_priority = data.get("by_priority", {})
            high_ids = [m["match_id"] for m in by_priority.get("high", [])]
            medium_ids = [m["match_id"] for m in by_priority.get("medium", [])]
            low_ids = [m["match_id"] for m in by_priority.get("low", [])]
            done_count = len(by_priority.get("done", []))

            counts = data.get("priority_counts", {})
            logger.info(
                f"Priority buckets: high={counts.get('high', 0)}, "
                f"medium={counts.get('medium', 0)}, low={counts.get('low', 0)}, "
                f"done={done_count} (skipped)"
            )
            if status_callback:
                status_callback(
                    f"Priority: {len(high_ids)} high, {len(medium_ids)} medium, "
                    f"{len(low_ids)} low, {done_count} done"
                )
        except Exception as e:
            logger.warning(f"Failed to fetch priority buckets: {e} — falling back to single-instance")
            return self.scrape_results(date, status_callback, progress_callback)

        # If no matches need processing, exit early
        all_to_process = high_ids + medium_ids + low_ids
        if not all_to_process:
            msg = "No matches need results scraping — all are done or not yet started."
            logger.info(msg)
            if status_callback:
                status_callback(msg)
            return

        # If only one bucket has matches, use single-instance (no need for 3 browsers)
        non_empty_buckets = sum(1 for b in [high_ids, medium_ids, low_ids] if b)
        if non_empty_buckets <= 1:
            logger.info(f"Only {non_empty_buckets} bucket has matches — using single-instance scrape")
            return self.scrape_results(date, status_callback, progress_callback)

        # ── Multi-instance concurrent processing ──────────────────────
        # Each worker gets its own FlashscoreScraper + browser instance.
        # Workers push results incrementally to the website.

        def worker_fn(bucket_name, match_ids_for_bucket, worker_num):
            """Process a priority bucket on a separate browser instance."""
            if not match_ids_for_bucket:
                return {"bucket": bucket_name, "processed": 0, "results": []}

            worker_msg = f"[Worker {worker_num}/{bucket_name}] Starting with {len(match_ids_for_bucket)} matches"
            logger.info(worker_msg)
            if status_callback:
                status_callback(worker_msg)

            # Each worker creates its own scraper instance (own browser)
            worker_scraper = FlashscoreScraper(
                status_callback=lambda msg: logger.info(f"[Worker {worker_num}] {msg}"),
                progress_callback=None,
            )

            try:
                worker_scraper.initialize(status_callback=lambda msg: logger.debug(f"[Worker {worker_num}] {msg}"))
                from src.data.loader.results_data_loader import ResultsDataLoader
                from src.data.extractor.results_data_extractor import ResultsDataExtractor

                results_loader = ResultsDataLoader(
                    worker_scraper.driver,
                    selenium_utils=worker_scraper.selenium_utils,
                )
                extractor = ResultsDataExtractor(results_loader)
                worker_results = []

                for i, match_id in enumerate(match_ids_for_bucket):
                    pmsg = f"[Worker {worker_num}/{bucket_name}] Match {i+1}/{len(match_ids_for_bucket)}: {match_id}"
                    logger.info(pmsg)
                    if status_callback:
                        status_callback(pmsg)

                    loaded = results_loader.load_match_summary_by_id(match_id, status_callback=None)
                    if not loaded:
                        logger.warning(f"[Worker {worker_num}] Failed to load {match_id}")
                        continue

                    elements = results_loader.get_elements()
                    match_status = extractor.extract_match_status(elements, status_callback=None)
                    home_score, away_score = extractor.extract_final_scores(elements, status_callback=None)

                    result = {
                        "match_id": match_id,
                        "home_score": home_score,
                        "away_score": away_score,
                        "status": match_status or "UNKNOWN",
                    }
                    worker_results.append(result)
                    logger.info(f"[Worker {worker_num}] {match_id}: status='{match_status}', scores={home_score}-{away_score}")

                    # Incremental push — send this result NOW
                    try:
                        from webhook_utils import forward_results_to_website
                        try:
                            from api.env_config_store import get_env_config
                            wurl = get_env_config("SCOREWISE_WEBSITE_URL")
                            wsecret = get_env_config("SCOREWISE_WEBHOOK_SECRET")
                        except ImportError:
                            wurl = os.environ.get("SCOREWISE_WEBSITE_URL", "")
                            wsecret = os.environ.get("SCOREWISE_WEBHOOK_SECRET", "")
                        if wurl and wsecret:
                            forward_results_to_website(
                                results=[result],
                                website_url=wurl,
                                webhook_secret=wsecret,
                                date_str=date,
                                source="flashscore-scraper",
                            )
                    except Exception:
                        pass  # Final batch push will catch any misses

                done_msg = f"[Worker {worker_num}/{bucket_name}] Finished: {len(worker_results)} results"
                logger.info(done_msg)
                if status_callback:
                    status_callback(done_msg)

                return {"bucket": bucket_name, "processed": len(worker_results), "results": worker_results}
            except Exception as e:
                logger.error(f"[Worker {worker_num}/{bucket_name}] Failed: {e}")
                return {"bucket": bucket_name, "processed": 0, "results": [], "error": str(e)}
            finally:
                try:
                    worker_scraper.close()
                except Exception:
                    logger.debug("Non-critical error (swallowed)")

        # Run up to 3 concurrent workers (one per non-empty priority bucket)
        buckets = [
            ("high", high_ids, 1),
            ("medium", medium_ids, 2),
            ("low", low_ids, 3),
        ]
        # Only spawn workers for non-empty buckets
        active_workers = [(name, ids, num) for name, ids, num in buckets if ids]
        config_max = results_config.get("max_workers", 3)
        max_workers = min(len(active_workers), config_max)  # Cap at configured max

        logger.info(f"Spawning {max_workers} concurrent worker(s) for {len(active_workers)} bucket(s)")
        if status_callback:
            status_callback(f"Spawning {max_workers} concurrent browser instances...")

        all_results = []
        # If the container is out of OS threads ("can't start new thread"),
        # a ThreadPoolExecutor can't be created at all — fall back to running
        # the buckets SERIALLY in this thread so the scrape still completes.
        def _run_serial():
            for name, ids, num in active_workers:
                try:
                    res = worker_fn(name, ids, num)
                    all_results.extend(res.get("results", []))
                    logger.info(f"Bucket '{name}' complete (serial): {res.get('processed', 0)} results")
                except Exception as e:
                    logger.error(f"Bucket '{name}' failed (serial): {e}")

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(worker_fn, name, ids, num): name
                    for name, ids, num in active_workers
                }
                for future in as_completed(futures):
                    bucket_name = futures[future]
                    try:
                        result = future.result()
                        all_results.extend(result.get("results", []))
                        logger.info(
                            f"Bucket '{bucket_name}' complete: {result.get('processed', 0)} results"
                        )
                    except Exception as e:
                        logger.error(f"Bucket '{bucket_name}' failed: {e}")
        except RuntimeError as pool_err:
            if "can't start new thread" in str(pool_err).lower():
                logger.warning("Out of OS threads — running results buckets serially instead")
                try:
                    from src.driver import cleanup_stale_chrome
                    cleanup_stale_chrome(kill_processes=True)
                except Exception:
                    pass
                _run_serial()
            else:
                raise

        # Save all results locally
        file_date = date.replace('.', '')
        results_filename = f"results_{file_date}.json"
        self.json_storage.save_results(all_results, filename=results_filename)

        summary_msg = (
            f"\n--- Concurrent results scraping summary: {len(all_results)} matches processed "
            f"for {date} ---"
        )
        logger.info(summary_msg)
        if status_callback:
            status_callback(summary_msg)
