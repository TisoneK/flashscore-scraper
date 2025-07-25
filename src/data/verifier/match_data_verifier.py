from .base_verifier import BaseVerifier
from src.core.url_verifier import URLVerifier

class MatchDataVerifier(BaseVerifier):
    def __init__(self, driver):
        self.url_verifier = URLVerifier(driver)
        self.driver = driver

    def verify(self, data, status_callback=None):
        required_fields = ['country', 'league', 'home_team', 'away_team', 'date', 'time', 'match_id']
        # If data is a string, treat as field name for field-specific validation
        if isinstance(data, str):
            method = getattr(self, f'verify_{data}', None)
            if method:
                return method(None, status_callback)
            else:
                return False, f"No verifier for field: {data}"
        # Otherwise, validate all required fields
        for field in required_fields:
            if status_callback:
                status_callback(f"Verifying {field}...")
            method = getattr(self, f'verify_{field}', None)
            if method:
                is_valid, error = method(getattr(data, field, None), status_callback)
                if not is_valid:
                    return False, f"{field}: {error}"
            else:
                value = getattr(data, field, None)
                if value is None:
                    return False, f"Missing field: {field}"
        if status_callback:
            status_callback("Match data verification completed.")
        return True, ""

    def verify_country(self, value, status_callback=None):
        if value is None:
            return False, "Missing country element"
        return True, ""

    def verify_league(self, value, status_callback=None):
        if value is None:
            return False, "Missing league element"
        return True, ""

    def verify_home_team(self, value, status_callback=None):
        if value is None:
            return False, "Missing home_team element"
        return True, ""

    def verify_away_team(self, value, status_callback=None):
        if value is None:
            return False, "Missing away_team element"
        return True, ""

    def verify_date(self, value, status_callback=None):
        if value is None:
            return False, "Missing date element"
        return True, ""

    def verify_time(self, value, status_callback=None):
        if value is None:
            return False, "Missing time element"
        return True, ""

    def verify_match_id(self, value, status_callback=None):
        if value is None:
            return False, "Missing match_id"
        if not isinstance(value, str) or not value:
            return False, "Invalid match_id"
        return True, "" 