from .base_verifier import BaseVerifier
from ...core.url_verifier import URLVerifier
from src.config import MIN_H2H_MATCHES

class H2HDataVerifier(BaseVerifier):
    def __init__(self, driver):
        self.url_verifier = URLVerifier(driver)
        self.driver = driver

    def verify(self, data):
        required_fields = ['h2h_section', 'h2h_rows', 'h2h_row_count']
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
        return True, ""

    def verify_h2h_section(self, value):
        if value is None:
            return False, "Missing h2h_section element"
        return True, ""

    def verify_h2h_rows(self, value):
        if not value or len(value) < MIN_H2H_MATCHES:
            return False, f"Insufficient H2H matches: {len(value) if value else 0} found, {MIN_H2H_MATCHES} required"
        return True, ""

    def verify_h2h_row_count(self, value):
        if value is None or value < MIN_H2H_MATCHES:
            return False, f"Insufficient h2h_row_count (minimum {MIN_H2H_MATCHES} required)"
        return True, "" 