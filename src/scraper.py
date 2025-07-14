import sys
import os
import time
import logging
import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.driver_manager import WebDriverManager
from src.utils.selenium_utils import SeleniumUtils
from src.core.url_verifier import URLVerifier
from src.config import CONFIG, MIN_H2H_MATCHES
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

# Global variables for logging paths
log_dir = CONFIG.logging.log_directory
os.makedirs(log_dir, exist_ok=True)

# Note: These will be updated in the scrape method based on the day parameter
timestamp = datetime.now().strftime(CONFIG.logging.log_filename_date_format)
scraper_log_path = os.path.join(log_dir, f"scraper_{timestamp}.log")
chrome_log_path = os.path.join(log_dir, f"chrome_{timestamp}.log")

MAX_MATCHES = 3  # Limit for demo/testing

logger = logging.getLogger(__name__)

class FlashscoreScraper:
    def __init__(self, status_callback=None):
        self.driver_manager = WebDriverManager(chrome_log_path=chrome_log_path)
        self.driver = None
        self.selenium_utils = None
        self.url_verifier = None
        self.json_storage = JSONStorage()
        self.match_loader = None
        self.odds_loader = None
        self.home_away_loader = None
        self.over_under_loader = None
        self.h2h_loader = None
        # Network resilience components
        self.network_monitor = NetworkMonitor()
        self.retry_manager = NetworkRetryManager()
        self.status_callback = status_callback

    def initialize(self, status_callback=None):
        import time
        start_time = time.time()
        timeout = 90  # 90 seconds timeout for initialization
        
        logger.info("🔄 Initializing scraper components...")
        
        if status_callback is None:
            status_callback = self.status_callback
        try:
            if status_callback:
                status_callback("Launching browser and initializing driver...")
            self.driver_manager.initialize()
            elapsed = time.time() - start_time
            logger.info(f"✅ Driver manager initialized in {elapsed:.2f}s")
            
            self.driver = self.driver_manager.get_driver()
            elapsed = time.time() - start_time
            logger.info(f"✅ WebDriver created in {elapsed:.2f}s")
            if status_callback:
                status_callback("Browser ready!")
            
            self.selenium_utils = SeleniumUtils(self.driver)
            self.url_verifier = URLVerifier(self.driver)
            
            # Start network monitoring (pass status_callback)
            self.network_monitor.start_monitoring(status_callback=status_callback)
            logger.info("Network monitoring started.")
            
            total_elapsed = time.time() - start_time
            logger.info(f"✅ Scraper initialization completed in {total_elapsed:.2f}s")
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Scraper initialization failed after {elapsed:.2f}s: {e}")
            raise

    def load_initial_data(self, day="Today", status_callback=None):
        if status_callback:
            status_callback('--- Loading main page ---')
        logger.info('--- Loading main page ---')
        self.match_loader = MatchDataLoader(self.driver, selenium_utils=self.selenium_utils)
        self.odds_loader = OddsDataLoader(self.driver, selenium_utils=self.selenium_utils)
        self.match_loader.load_main_page()
        logger.info('Main page loaded.')
        if status_callback:
            status_callback('Main page loaded.')
        if day == "Tomorrow":
            logger.info("Loading tomorrow's matches...")
            if status_callback:
                status_callback("Loading tomorrow's matches...")
            match_ids = self.match_loader.get_tomorrow_match_ids()
            if status_callback:
                status_callback(f"Found {len(match_ids)} matches for tomorrow.")
        else:
            logger.info("Loading today's matches...")
            if status_callback:
                status_callback("Loading today's matches...")
            match_ids = self.match_loader.get_today_match_ids()
            if status_callback:
                status_callback(f"Found {len(match_ids)} matches for today.")
            if not match_ids:
                logger.info("No matches found for today. Checking tomorrow's schedule.")
                if status_callback:
                    status_callback("No matches found for today. Checking tomorrow's schedule.")
                match_ids = self.match_loader.get_tomorrow_match_ids()
                if status_callback:
                    status_callback(f"Found {len(match_ids)} matches for tomorrow.")
        return match_ids

    def check_and_get_processed_matches(self):
        processed_matches = self.json_storage.get_processed_match_ids()
        processed_match_ids = {mid for mid, _ in processed_matches}
        processed_reasons = {mid: reason for mid, reason in processed_matches}
        return processed_match_ids, processed_reasons

    def load_match_details(self, match_id):
        return self.match_loader.load_match(match_id)

    def extract_match_data(self, status_callback=None):
        extractor = MatchDataExtractor(self.match_loader)
        return extractor.extract_match_data(status_callback=status_callback)

    def load_home_away_odds(self, match_id, status_callback=None):
        if self.driver is None:
            return False
        self.home_away_loader = OddsDataLoader(self.driver, selenium_utils=self.selenium_utils)
        return self.home_away_loader.load_home_away_odds(match_id, status_callback=status_callback)

    def extract_home_away_odds(self, status_callback=None):
        home_away_extractor = OddsDataExtractor(self.home_away_loader)
        home_odds = float(home_away_extractor.home_odds) if home_away_extractor.home_odds else None
        away_odds = float(home_away_extractor.away_odds) if home_away_extractor.away_odds else None
        return home_odds, away_odds

    def load_over_under_odds(self, match_id, status_callback=None):
        if self.driver is None:
            return False
        self.over_under_loader = OddsDataLoader(self.driver, selenium_utils=self.selenium_utils)
        return self.over_under_loader.load_over_under_odds(match_id, status_callback=status_callback)

    def extract_over_under_odds(self, status_callback=None):
        over_under_extractor = OddsDataExtractor(self.over_under_loader)
        selected = over_under_extractor.get_selected_alternative()
        if selected:
            match_total = float(selected['alternative']) if selected['alternative'] else None
            over_odds = float(selected['over']) if selected['over'] else None
            under_odds = float(selected['under']) if selected['under'] else None
            return match_total, over_odds, under_odds
        return None, None, None

    def load_h2h_data(self, match_id, status_callback=None):
        if self.driver is None:
            return False
        self.h2h_loader = H2HDataLoader(self.driver, selenium_utils=self.selenium_utils)
        return self.h2h_loader.load_h2h(match_id, status_callback=status_callback)

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
            h2h_match = H2HMatchModel(
                match_id=match_id,
                date=date or "",
                home_team=home_team or "",
                away_team=away_team or "",
                home_score=int(home_score) if home_score is not None else 0,
                away_score=int(away_score) if away_score is not None else 0,
                competition=competition or ""
            )
            h2h_matches.append(h2h_match)
        return h2h_matches, self.h2h_loader.get_h2h_count()

    def validate_odds_data(self, odds):
        missing_odds_fields = []
        # Only these are required:
        if odds.match_total is None:
            missing_odds_fields.append('match_total')
        if odds.over_odds is None:
            missing_odds_fields.append('over_odds')
        if odds.under_odds is None:
            missing_odds_fields.append('under_odds')
        # home_odds and away_odds are optional
        return bool(missing_odds_fields), missing_odds_fields

    def compose_skip_reason(self, odds_incomplete, missing_odds_fields, h2h_count):
        reasons = []
        if odds_incomplete:
            reasons.append(f"missing or invalid odds fields: {', '.join(missing_odds_fields)}")
        if h2h_count < MIN_H2H_MATCHES:
            reasons.append(f"insufficient H2H matches ({h2h_count} found, {MIN_H2H_MATCHES} required)")
        return "; ".join(reasons)

    def save_match_data(self, match):
        self.json_storage.save_matches([match])

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
        logger.info(log_text)

    def close(self):
        self.driver_manager.close()
        # Stop network monitoring (pass status_callback if available)
        self.network_monitor.stop_monitoring()
        logger.info("Network monitoring stopped.")

    def scrape(self, progress_callback=None, day="Today", status_callback=None):
        # Update log file paths based on the day parameter
        from src.utils import get_scraping_date
        file_date = get_scraping_date(day)
        global scraper_log_path, chrome_log_path
        scraper_log_path = os.path.join(log_dir, f"scraper_{file_date}.log")
        chrome_log_path = os.path.join(log_dir, f"chrome_{file_date}.log")
        
        # Ensure logging is properly configured
        ensure_logging_configured(scraper_log_path)
        logger.info(f"=== Starting scraping for {day} ===")
        if status_callback:
            status_callback(f"=== Starting scraping for {day} ===")
        self.initialize(status_callback=status_callback)
        try:
            def main_scrape():
                match_ids = self.load_initial_data(day, status_callback=status_callback)
                if not match_ids:
                    if status_callback:
                        status_callback("No matches found for scraping.")
                    return

                processed_match_ids, processed_reasons = self.check_and_get_processed_matches()

                matches = []
                MAX_MATCHES = len(match_ids)

                for i, match_id in enumerate(match_ids[:MAX_MATCHES]):
                    if progress_callback:
                        progress_callback(i+1, MAX_MATCHES)
                    if not progress_callback:
                        logger.info(f'Processing match {match_id} ({i+1}/{MAX_MATCHES})')
                    if match_id in processed_match_ids:
                        msg = f"Skipping already processed match: {match_id} (reason: {processed_reasons.get(match_id, 'already processed')})"
                        logger.info(msg)
                        if status_callback:
                            status_callback(msg)
                        continue

                    msg = f"Processing match {match_id}..."
                    if status_callback:
                        status_callback(msg)
                    logger.info(msg)

                    if self.load_match_details(match_id):
                        match_data = self.extract_match_data(status_callback=status_callback)
                        odds = OddsModel(match_id=match_id)

                        if self.load_home_away_odds(match_id, status_callback=status_callback):
                            odds.home_odds, odds.away_odds = self.extract_home_away_odds(status_callback=status_callback)
                        else:
                            warn_msg = f'  - Failed to load home/away odds for match {match_id}'
                            logger.warning(warn_msg)
                            if status_callback:
                                status_callback(warn_msg)

                        if self.load_over_under_odds(match_id, status_callback=status_callback):
                            odds.match_total, odds.over_odds, odds.under_odds = self.extract_over_under_odds(status_callback=status_callback)
                            if odds.match_total is None:
                                warn_msg = f"  - No selected over/under alternative available for match {match_id}"
                                logger.warning(warn_msg)
                                if status_callback:
                                    status_callback(warn_msg)
                        else:
                            warn_msg = f'  - Failed to load over/under odds for match {match_id}'
                            logger.warning(warn_msg)
                            if status_callback:
                                status_callback(warn_msg)

                        odds_incomplete, missing_odds_fields = self.validate_odds_data(odds)
                        if odds_incomplete:
                            warn_msg = f"  - Missing compulsory odds fields for match {match_id}: {', '.join(missing_odds_fields)}"
                            logger.warning(warn_msg)
                            if status_callback:
                                status_callback(warn_msg)

                        h2h_matches = []
                        h2h_count = 0
                        if self.load_h2h_data(match_id, status_callback=status_callback):
                            h2h_matches, h2h_count = self.extract_h2h_matches(match_id, status_callback=status_callback)
                            msg = f'  - H2H matches found: {h2h_count} (required: {MIN_H2H_MATCHES})'
                            logger.info(msg)
                            if status_callback:
                                status_callback(msg)
                            if h2h_count < MIN_H2H_MATCHES:
                                warn_msg = f'  - Insufficient H2H matches for match {match_id}: {h2h_count} found, {MIN_H2H_MATCHES} required'
                                logger.warning(warn_msg)
                                if status_callback:
                                    status_callback(warn_msg)
                        else:
                            warn_msg = f'  - Failed to load H2H data for match {match_id}'
                            logger.warning(warn_msg)
                            if status_callback:
                                status_callback(warn_msg)

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
                        self.save_match_data(match)
                    else:
                        warn_msg = f'  - Failed to load/verify match page for {match_id}'
                        logger.warning(warn_msg)
                        if status_callback:
                            status_callback(warn_msg)
                        continue

                summary_msg = f"\n--- Summary: Collected {len(matches)} matches for {day.lower()} ---"
                logger.info(summary_msg)
                if status_callback:
                    status_callback(summary_msg)
                for m in matches:
                    FlashscoreScraper.log_match_info(m)

            # Run the main scrape with retry logic
            self.retry_manager.retry_network_operation(main_scrape)
        finally:
            self.close()
