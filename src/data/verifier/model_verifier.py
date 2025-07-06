from .base_verifier import BaseVerifier
from .match_data_verifier import MatchDataVerifier
from .h2h_data_verifier import H2HDataVerifier
from .odds_data_verifier import OddsDataVerifier

class ModelVerifier(BaseVerifier):
    def __init__(self, driver):
        self.match_verifier = MatchDataVerifier(driver)
        self.h2h_verifier = H2HDataVerifier(driver)
        self.odds_verifier = OddsDataVerifier(driver)

    def verify(self, data):
        # Dispatch to the correct verifier based on data type
        if hasattr(data, 'match_id'):
            return self.match_verifier.verify(data)
        elif hasattr(data, 'h2h_rows'):
            return self.h2h_verifier.verify(data)
        elif hasattr(data, 'home_odds') and hasattr(data, 'away_odds'):
            return self.odds_verifier.verify(data)
        else:
            return False, 'Unknown data type for model verification.' 