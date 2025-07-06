from .base_verifier import BaseVerifier
from ...core.url_verifier import URLVerifier

class OddsDataVerifier(BaseVerifier):
    def __init__(self, driver):
        self.url_verifier = URLVerifier(driver)
        self.driver = driver

    def verify(self, data):
        required_fields = ['match_total', 'over_odds', 'under_odds', 'all_totals']
        optional_fields = ['home_odds', 'away_odds']
        if isinstance(data, str):
            method = getattr(self, f'verify_{data}', None)
            if method:
                return method(None)
            else:
                return False, f"No verifier for field: {data}"
        for field in required_fields:
            method = getattr(self, f'verify_{field}', None)
            if method:
                is_valid, error = method(getattr(data, field, None))
                if not is_valid:
                    return False, f"{field}: {error}"
            else:
                value = getattr(data, field, None)
                if value is None:
                    return False, f"Missing field: {field}"
        # Optional fields: do not fail if missing
        return True, ""

    def verify_home_odds(self, value):
        # Optional: just warn, do not fail
        return True, ""

    def verify_away_odds(self, value):
        # Optional: just warn, do not fail
        return True, ""

    def verify_match_total(self, value):
        if value is None:
            return False, "Missing match_total element"
        return True, ""

    def verify_over_odds(self, value):
        if value is None:
            return False, "Missing over_odds element"
        return True, ""

    def verify_under_odds(self, value):
        if value is None:
            return False, "Missing under_odds element"
        return True, ""

    def verify_all_totals(self, value):
        if value is None:
            return False, "Missing all_totals list"
        return True, "" 