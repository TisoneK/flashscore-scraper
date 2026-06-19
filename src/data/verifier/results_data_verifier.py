from typing import Tuple, Optional
from selenium.webdriver.remote.webdriver import WebDriver
import re

class ResultsDataVerifier:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def verify_home_score(self, home_score: int) -> Tuple[bool, str]:
        """
        Verify that home score is valid.
        Returns (is_valid, error_message)
        """
        try:
            if not isinstance(home_score, int):
                return False, "Home score must be an integer"
            
            if home_score < 0:
                return False, "Home score cannot be negative"
            
            if home_score > 200:
                return False, "Home score seems unreasonably high for basketball"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error validating home score: {str(e)}"

    def verify_away_score(self, away_score: int) -> Tuple[bool, str]:
        """
        Verify that away score is valid.
        Returns (is_valid, error_message)
        """
        try:
            if not isinstance(away_score, int):
                return False, "Away score must be an integer"
            
            if away_score < 0:
                return False, "Away score cannot be negative"
            
            if away_score > 200:
                return False, "Away score seems unreasonably high for basketball"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error validating away score: {str(e)}"

    def verify_scores(self, home_score: int, away_score: int) -> Tuple[bool, str]:
        """
        Verify that both scores are valid and reasonable.
        Returns (is_valid, error_message)
        """
        try:
            # Verify individual scores
            home_valid, home_error = self.verify_home_score(home_score)
            if not home_valid:
                return False, home_error
            
            away_valid, away_error = self.verify_away_score(away_score)
            if not away_valid:
                return False, away_error
            
            # Check if at least one team scored (to avoid 0-0 draws in finished games)
            if home_score == 0 and away_score == 0:
                return False, "Both teams cannot have 0 points in a finished game"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error validating scores: {str(e)}"

    def verify_match_status(self, status: str) -> Tuple[bool, str]:
        """
        Verify that match status is valid.
        Returns (is_valid, error_message)
        """
        try:
            if not status:
                return False, "Match status cannot be empty"
            
            valid_statuses = ["scheduled", "live", "finished", "cancelled", "postponed"]
            status_lower = status.lower().strip()
            
            if status_lower not in valid_statuses:
                return False, f"Invalid match status: {status}. Valid statuses are: {valid_statuses}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Error validating match status: {str(e)}"

    def verify_score_text(self, score_text: str) -> Tuple[bool, str]:
        """
        Verify that score text format is valid (e.g., "84-117").
        Returns (is_valid, error_message)
        """
        try:
            if not score_text:
                return False, "Score text cannot be empty"
            
            # Pattern to match score format like "84-117" or "84 - 117"
            score_pattern = r'^\s*(\d+)\s*[-:]\s*(\d+)\s*$'
            match = re.match(score_pattern, score_text.strip())
            
            if not match:
                return False, f"Invalid score format: {score_text}. Expected format: 'home_score-away_score'"
            
            home_score = int(match.group(1))
            away_score = int(match.group(2))
            
            # Verify the parsed scores
            return self.verify_scores(home_score, away_score)
            
        except Exception as e:
            return False, f"Error validating score text: {str(e)}" 