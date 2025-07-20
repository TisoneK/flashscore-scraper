from typing import Optional, Dict, Tuple
from src.data.elements_model import ResultsElements
from src.data.verifier.results_data_verifier import ResultsDataVerifier
from src.models import MatchModel
import re

class ResultsDataExtractor:
    def __init__(self, loader):
        """
        :param loader: An instance of ResultsDataLoader or similar, with an 'elements' attribute.
        """
        try:
            self._loader = loader
            self._last_extracted_data: Optional[Dict[str, Optional[int]]] = None
            self.results_data_verifier = ResultsDataVerifier(getattr(loader, 'driver', None))
        except Exception as e:
            print(f"Error initializing ResultsDataExtractor: {e}")
            self._loader = None
            self._last_extracted_data = None

    def extract_final_scores(self, elements: Optional[ResultsElements] = None, status_callback=None) -> Tuple[Optional[int], Optional[int]]:
        """
        Extracts final scores from the loader's elements or from a provided elements object.
        :param elements: Optionally, a ResultsElements object to extract from.
        :param status_callback: Optional callback function for status updates.
        :return: A tuple of (home_score, away_score) or (None, None) if not available.
        """
        try:
            if status_callback:
                status_callback("Extracting final scores...")
            
            elements = elements or (self._loader.elements if self._loader else None)
            
            if elements is None:
                print("Error: No elements available for extraction")
                return None, None

            def normalize(value):
                if value is None:
                    return None
                value = value.strip() if isinstance(value, str) else value
                return value if value else None

            # Extract home score
            if status_callback:
                status_callback("Extracting home score...")
            home_score_text = normalize(elements.home_score.text) if elements.home_score and getattr(elements.home_score, 'text', None) else None
            
            if home_score_text:
                try:
                    home_score = int(home_score_text)
                    is_valid, error = self.results_data_verifier.verify_home_score(home_score)
                    if not is_valid:
                        print(f"Error verifying home score: {error}")
                        home_score = None
                except (ValueError, TypeError):
                    print(f"Error parsing home score: {home_score_text}")
                    home_score = None
            else:
                home_score = None

            # Extract away score
            if status_callback:
                status_callback("Extracting away score...")
            away_score_text = normalize(elements.away_score.text) if elements.away_score and getattr(elements.away_score, 'text', None) else None
            
            if away_score_text:
                try:
                    away_score = int(away_score_text)
                    is_valid, error = self.results_data_verifier.verify_away_score(away_score)
                    if not is_valid:
                        print(f"Error verifying away score: {error}")
                        away_score = None
                except (ValueError, TypeError):
                    print(f"Error parsing away score: {away_score_text}")
                    away_score = None
            else:
                away_score = None

            # Verify both scores together
            if home_score is not None and away_score is not None:
                is_valid, error = self.results_data_verifier.verify_scores(home_score, away_score)
                if not is_valid:
                    print(f"Error verifying scores: {error}")
                    home_score = None
                    away_score = None

            # Store the extracted data
            self._last_extracted_data = {
                'home_score': home_score,
                'away_score': away_score
            }

            if status_callback:
                status_callback("Final scores extraction completed.")

            return home_score, away_score
            
        except Exception as e:
            print(f"Error extracting final scores: {e}")
            self._last_extracted_data = None
            return None, None

    def extract_match_status(self, elements: Optional[ResultsElements] = None, status_callback=None) -> Optional[str]:
        """
        Extracts match status from the loader's elements or from a provided elements object.
        :param elements: Optionally, a ResultsElements object to extract from.
        :param status_callback: Optional callback function for status updates.
        :return: Match status string or None if not available.
        """
        try:
            if status_callback:
                status_callback("Extracting match status...")
            
            elements = elements or (self._loader.elements if self._loader else None)
            
            if elements is None:
                print("Error: No elements available for extraction")
                return None

            def normalize(value):
                if value is None:
                    return None
                value = value.strip() if isinstance(value, str) else value
                return value if value else None

            # Extract match status
            match_status = normalize(elements.match_status.text) if elements.match_status and getattr(elements.match_status, 'text', None) else None
            
            if match_status:
                is_valid, error = self.results_data_verifier.verify_match_status(match_status)
                if not is_valid:
                    print(f"Error verifying match status: {error}")
                    match_status = None

            if status_callback:
                status_callback("Match status extraction completed.")

            return match_status
            
        except Exception as e:
            print(f"Error extracting match status: {e}")
            return None

    def extract_from_final_score_text(self, score_text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract home and away scores from a combined score text (e.g., "84-117").
        :param score_text: The combined score text.
        :return: A tuple of (home_score, away_score) or (None, None) if invalid.
        """
        try:
            if not score_text:
                return None, None
            
            # Pattern to match score format like "84-117" or "84 - 117"
            score_pattern = r'^\s*(\d+)\s*[-:]\s*(\d+)\s*$'
            match = re.match(score_pattern, score_text.strip())
            
            if not match:
                print(f"Invalid score format: {score_text}")
                return None, None
            
            home_score = int(match.group(1))
            away_score = int(match.group(2))
            
            # Verify the scores
            is_valid, error = self.results_data_verifier.verify_scores(home_score, away_score)
            if not is_valid:
                print(f"Error verifying scores: {error}")
                return None, None
            
            return home_score, away_score
            
        except Exception as e:
            print(f"Error parsing score text: {e}")
            return None, None

    def get_last_extracted_data(self) -> Optional[Dict[str, Optional[int]]]:
        """Returns the last extracted results data, or None if not extracted yet."""
        try:
            return self._last_extracted_data
        except Exception as e:
            print(f"Error getting last extracted data: {e}")
            return None

    def set_loader(self, loader):
        """Sets a new loader for the extractor."""
        try:
            self._loader = loader
        except Exception as e:
            print(f"Error setting loader: {e}")

    def get_loader(self):
        """Returns the current loader."""
        try:
            return self._loader
        except Exception as e:
            print(f"Error getting loader: {e}")
            return None

    # Property-based getters and setters for each attribute
    @property
    def home_score(self) -> Optional[int]:
        try:
            return self._last_extracted_data.get('home_score') if self._last_extracted_data else None
        except Exception as e:
            print(f"Error getting home_score: {e}")
            return None

    @home_score.setter
    def home_score(self, value: Optional[int]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['home_score'] = value
        except Exception as e:
            print(f"Error setting home_score: {e}")

    @property
    def away_score(self) -> Optional[int]:
        try:
            return self._last_extracted_data.get('away_score') if self._last_extracted_data else None
        except Exception as e:
            print(f"Error getting away_score: {e}")
            return None

    @away_score.setter
    def away_score(self, value: Optional[int]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['away_score'] = value
        except Exception as e:
            print(f"Error setting away_score: {e}")

    def extract(self, attribute_name: str) -> Optional[int]:
        """Generic extract method for getting any extracted attribute."""
        try:
            return self._last_extracted_data.get(attribute_name) if self._last_extracted_data else None
        except Exception as e:
            print(f"Error extracting {attribute_name}: {e}")
            return None 