import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.driver_manager import WebDriverManager
from src.utils.selenium_utils import SeleniumUtils
from src.core.url_verifier import URLVerifier
from src.config import CONFIG
from .match_data_loader import MatchDataLoader
from src.data.extractor.match_data_extractor import MatchDataExtractor
from src.data.loader.odds_data_loader import OddsDataLoader
from src.data.extractor.odds_data_extractor import OddsDataExtractor
from src.data.loader.h2h_data_loader import H2HDataLoader
from src.data.extractor.h2h_data_extractor import H2HDataExtractor

# --- CONFIGURE THESE ---
MAX_MATCHES = 3  # Limit for demo/testing
# -----------------------


def main():
    driver_manager = WebDriverManager()
    driver_manager.initialize()
    driver = driver_manager.get_driver()
    selenium_utils = SeleniumUtils(driver)
    url_verifier = URLVerifier(driver)

    try:
        print('--- Loading main page ---')
        match_loader = MatchDataLoader(driver, selenium_utils=selenium_utils)
        odds_loader = OddsDataLoader(driver, selenium_utils=selenium_utils)
        match_loader.load_main_page()
        print('Main page loaded.')

        extractor = MatchDataExtractor(match_loader)
        odds_extractor = OddsDataExtractor(odds_loader)

        print('--- Fetching scheduled match IDs ---')
        match_ids = match_loader.get_today_match_ids()
        print(f'Found {len(match_ids)} scheduled matches.')
        if not match_ids:
            print('No matches found.')
            return

        print(f'--- Processing up to {MAX_MATCHES} matches ---')
        for i, match_id in enumerate(match_ids[:MAX_MATCHES]):
            print(f'[{i+1}] Match ID: {match_id}')

            success = match_loader.load_match(match_id)

            if success:
                print(f'  - Match page loaded and verified for {match_id}')
                extractor.extract_match_data()
                print("  - Extracted Data:")
                print(f"    Country: {extractor.country}")
                print(f"    League: {extractor.league}")
                print(f"    Home Team: {extractor.home_team}")
                print(f"    Away Team: {extractor.away_team}")
                print(f"    Date: {extractor.date}")
                print(f"    Time: {extractor.time}")
                print(f"    Match ID: {extractor.match_id}")

                # Home/Away odds
                home_away_loader = OddsDataLoader(driver, selenium_utils=selenium_utils)
                home_away_extractor = OddsDataExtractor(home_away_loader)
                if home_away_loader.load_home_away_odds(match_id):
                    print(f'  - Home/Away odds loaded for match {match_id}')
                    home_away_extractor.extract_odds_data()
                    print("  - Home/Away Odds Data:")
                    print(f"    Home Odds: {home_away_extractor.home_odds}")
                    print(f"    Away Odds: {home_away_extractor.away_odds}")
                else:
                    print(f'  - Failed to load home/away odds for match {match_id}')

                # Over/Under odds
                over_under_loader = OddsDataLoader(driver, selenium_utils=selenium_utils)
                over_under_extractor = OddsDataExtractor(over_under_loader)
                if over_under_loader.load_over_under_odds(match_id):
                    print(f'  - Over/Under odds loaded for match {match_id}')
                    over_under_extractor.extract_odds_data()
                    total_alternatives = over_under_extractor.get_total_alternatives()
                    print(f"  - Total Over/Under Alternatives: {total_alternatives}")
                    selected = over_under_extractor.get_selected_alternative()
                    print("  - Selected Over/Under Alternative:")
                    if selected:
                        print(f"    Alternative: {selected['alternative']}")
                        print(f"    Over: {selected['over']}")
                        print(f"    Under: {selected['under']}")
                    else:
                        print("    No selected alternative available.")
                else:
                    print(f'  - Failed to load over/under odds for match {match_id}')

                # H2H data
                h2h_loader = H2HDataLoader(driver, selenium_utils=selenium_utils)
                h2h_extractor = H2HDataExtractor(h2h_loader)
                if h2h_loader.load_h2h(match_id):
                    print(f'  - H2H data loaded for match {match_id}')
                    h2h_matches = h2h_extractor.extract_h2h_data()
                    print("  - H2H Matches:")
                    for i in range(len(h2h_matches)):
                        print(f"    H2H Match {i+1}:")
                        print(f"      Date: {h2h_extractor.get_date(i)}")
                        print(f"      Home Team: {h2h_extractor.get_home_team(i)}")
                        print(f"      Away Team: {h2h_extractor.get_away_team(i)}")
                        print(f"      Home Score: {h2h_extractor.get_home_score(i)}")
                        print(f"      Away Score: {h2h_extractor.get_away_score(i)}")
                        print(f"      Competition: {h2h_extractor.get_competition(i)}")
                else:
                    print(f'  - Failed to load H2H data for match {match_id}')
            else:
                print(f'  - Failed to load/verify match page for {match_id}')
                continue

            time.sleep(5)

    finally:
        driver_manager.close()


if __name__ == '__main__':
    main() 
