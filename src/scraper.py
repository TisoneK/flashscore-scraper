import sys
import os
import time
import logging
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

MAX_MATCHES = 3  # Limit for demo/testing

# Setup logging
log_dir = os.path.join("output", "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"scraper_{time.strftime('%y%m%d')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FlashscoreScraper:
    def __init__(self):
        self.driver_manager = WebDriverManager()
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

    def initialize(self):
        self.driver_manager.initialize()
        self.driver = self.driver_manager.get_driver()
        self.selenium_utils = SeleniumUtils(self.driver)
        self.url_verifier = URLVerifier(self.driver)
        # Start network monitoring
        self.network_monitor.start_monitoring()
        logger.info("Network monitoring started.")

    def load_initial_data(self):
        logger.info('--- Loading main page ---')
        self.match_loader = MatchDataLoader(self.driver, selenium_utils=self.selenium_utils)
        self.odds_loader = OddsDataLoader(self.driver, selenium_utils=self.selenium_utils)
        self.match_loader.load_main_page()
        logger.info('Main page loaded.')
        
        match_ids = self.match_loader.get_today_match_ids()
        if not match_ids:
            logger.info("No matches found for today. Checking tomorrow's schedule.")
            match_ids = self.match_loader.get_tomorrow_match_ids()
        return match_ids

    def check_and_get_processed_matches(self):
        processed_matches = self.json_storage.get_processed_match_ids()
        processed_match_ids = {mid for mid, _ in processed_matches}
        processed_reasons = {mid: reason for mid, reason in processed_matches}
        return processed_match_ids, processed_reasons

    def load_match_details(self, match_id):
        return self.match_loader.load_match(match_id)

    def extract_match_data(self):
        extractor = MatchDataExtractor(self.match_loader)
        return extractor.extract_match_data()

    def load_home_away_odds(self, match_id):
        self.home_away_loader = OddsDataLoader(self.driver, selenium_utils=self.selenium_utils)
        return self.home_away_loader.load_home_away_odds(match_id)

    def extract_home_away_odds(self):
        home_away_extractor = OddsDataExtractor(self.home_away_loader)
        home_away_extractor.extract_home_away_odds()
        home_odds = float(home_away_extractor.home_odds) if home_away_extractor.home_odds else None
        away_odds = float(home_away_extractor.away_odds) if home_away_extractor.away_odds else None
        return home_odds, away_odds

    def load_over_under_odds(self, match_id):
        self.over_under_loader = OddsDataLoader(self.driver, selenium_utils=self.selenium_utils)
        return self.over_under_loader.load_over_under_odds(match_id)

    def extract_over_under_odds(self):
        over_under_extractor = OddsDataExtractor(self.over_under_loader)
        over_under_extractor.extract_over_under_odds()
        selected = over_under_extractor.get_selected_alternative()
        if selected:
            match_total = float(selected['alternative']) if selected['alternative'] else None
            over_odds = float(selected['over']) if selected['over'] else None
            under_odds = float(selected['under']) if selected['under'] else None
            return match_total, over_odds, under_odds
        return None, None, None

    def load_h2h_data(self, match_id):
        self.h2h_loader = H2HDataLoader(self.driver, selenium_utils=self.selenium_utils)
        return self.h2h_loader.load_h2h(match_id)

    def extract_h2h_matches(self, match_id):
        h2h_extractor = H2HDataExtractor(self.h2h_loader)
        h2h_matches = []
        h2h_data = h2h_extractor.extract_h2h_data()
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
        if odds.home_odds is None:
            missing_odds_fields.append('home_odds')
        if odds.away_odds is None:
            missing_odds_fields.append('away_odds')
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
        # Stop network monitoring
        self.network_monitor.stop_monitoring()
        logger.info("Network monitoring stopped.")

    def scrape(self, progress_callback=None):
        self.initialize()
        try:
            def main_scrape():
                match_ids = self.load_initial_data()
                logger.info(f'Found {len(match_ids)} scheduled matches.')
                if not match_ids:
                    return

                processed_match_ids, processed_reasons = self.check_and_get_processed_matches()
                if processed_match_ids:
                    logger.info(f"Found {len(processed_match_ids)} previously processed matches.")

                matches = []
                MAX_MATCHES = len(match_ids)

                for i, match_id in enumerate(match_ids[:MAX_MATCHES]):
                    if progress_callback:
                        progress_callback(i+1, MAX_MATCHES)
                    if not progress_callback:
                        logger.info(f'Processing match {match_id} ({i+1}/{MAX_MATCHES})')

                    if match_id in processed_match_ids:
                        logger.info(f"Skipping already processed match: {match_id} (reason: {processed_reasons.get(match_id, 'already processed')})")
                        continue

                    if self.load_match_details(match_id):
                        logger.info(f'  - Match page loaded and verified for {match_id}')
                        match_data = self.extract_match_data()
                        odds = OddsModel(match_id=match_id)

                        if self.load_home_away_odds(match_id):
                            logger.info(f'  - Home/Away odds loaded for match {match_id}')
                            odds.home_odds, odds.away_odds = self.extract_home_away_odds()
                        else:
                            logger.warning(f'  - Failed to load home/away odds for match {match_id}')

                        if self.load_over_under_odds(match_id):
                            logger.info(f'  - Over/Under odds loaded for match {match_id}')
                            odds.match_total, odds.over_odds, odds.under_odds = self.extract_over_under_odds()
                            if odds.match_total is None:
                                logger.warning(f"  - No selected over/under alternative available for match {match_id}")
                        else:
                            logger.warning(f'  - Failed to load over/under odds for match {match_id}')

                        odds_incomplete, missing_odds_fields = self.validate_odds_data(odds)
                        if odds_incomplete:
                            logger.warning(f"  - Missing compulsory odds fields for match {match_id}: {', '.join(missing_odds_fields)}")

                        h2h_matches = []
                        h2h_count = 0
                        if self.load_h2h_data(match_id):
                            logger.info(f'  - H2H data loaded for match {match_id}')
                            h2h_matches, h2h_count = self.extract_h2h_matches(match_id)
                            logger.info(f'  - H2H matches found: {h2h_count} (required: {MIN_H2H_MATCHES})')
                            if h2h_count < MIN_H2H_MATCHES:
                                logger.warning(f'  - Insufficient H2H matches for match {match_id}: {h2h_count} found, {MIN_H2H_MATCHES} required')
                        else:
                            logger.warning(f'  - Failed to load H2H data for match {match_id}')

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
                        logger.warning(f'  - Failed to load/verify match page for {match_id}')
                        continue

                logger.info(f"\n--- Summary: Collected {len(matches)} matches ---")
                for m in matches:
                    FlashscoreScraper.log_match_info(m)

            # Run the main scrape with retry logic
            self.retry_manager.retry_network_operation(main_scrape)
        finally:
            self.close()
