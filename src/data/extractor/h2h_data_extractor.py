from typing import Optional, List, Dict
from src.data.elements_model import H2HElements
from src.utils.utils import format_date
from src.data.verifier.h2h_data_verifier import H2HDataVerifier
from src.utils.config_loader import MIN_H2H_MATCHES
from src.core.exceptions import DataNotFoundError, DataParseError, DataValidationError, DataUnavailableWarning
import logging

logger = logging.getLogger(__name__)

class H2HDataExtractor:
    def __init__(self, loader):
        """
        :param loader: An instance of H2HDataLoader or similar, with an 'elements' attribute and attribute getter methods.
        """
        try:
            self._loader = loader
            self._last_extracted_data: Optional[List[Dict[str, Optional[str]]]] = None
            self.h2h_data_verifier = H2HDataVerifier(getattr(loader, 'driver', None))
        except Exception as e:
            print(f"Error initializing H2HDataExtractor: {e}")
            self._loader = None
            self._last_extracted_data = None

    def _extract_date(self, row) -> Optional[str]:
        if self._loader is None:
            return None
        el = self._loader.get_date(row)
        return el.text.strip() if el and hasattr(el, 'text') else None

    def _extract_home_team(self, row) -> Optional[str]:
        if self._loader is None:
            return None
        el = self._loader.get_home_team(row)
        return el.text.strip() if el and hasattr(el, 'text') else None

    def _extract_away_team(self, row) -> Optional[str]:
        if self._loader is None:
            return None
        el = self._loader.get_away_team(row)
        return el.text.strip() if el and hasattr(el, 'text') else None

    def _extract_result(self, row) -> Optional[str]:
        if self._loader is None:
            return None
        el = self._loader.get_result(row)
        return el.text.strip() if el and hasattr(el, 'text') else None

    def _extract_competition(self, row) -> Optional[str]:
        if self._loader is None:
            return None
        el = self._loader.get_competition(row) if hasattr(self._loader, 'get_competition') else row.get('competition')
        return el.text.strip() if el and hasattr(el, 'text') else None

    def _extract_home_score(self, row) -> Optional[str]:
        el = row.get('home_score')
        return el.text.strip() if el and hasattr(el, 'text') else None

    def _extract_away_score(self, row) -> Optional[str]:
        el = row.get('away_score')
        return el.text.strip() if el and hasattr(el, 'text') else None

    def extract_h2h_data(self, elements: Optional[H2HElements] = None, status_callback=None) -> List[Dict[str, Optional[str]]]:
        try:
            if status_callback:
                status_callback("Extracting H2H data...")
            
            elements = elements or (self._loader.elements if self._loader else None)
            if elements is None:
                print("Error: No elements available for H2H extraction")
                return []
            
            h2h_matches = []
            if elements.h2h_rows:
                if status_callback:
                    status_callback(f"Processing {len(elements.h2h_rows)} H2H matches...")
                
                for row in elements.h2h_rows[:MIN_H2H_MATCHES]:
                    try:
                        if status_callback:
                            status_callback("Extracting H2H match details...")
                        
                        date = self._extract_date(row)
                        date = format_date(date)
                        home_team = self._extract_home_team(row)
                        away_team = self._extract_away_team(row)
                        home_score = self._extract_home_score(row)
                        away_score = self._extract_away_score(row)
                        competition = self._extract_competition(row)
                        # Verify compulsory fields (all except competition)
                        for field_name, value in [
                            ('date', date),
                            ('home_team', home_team),
                            ('away_team', away_team),
                            ('home_score', home_score),
                            ('away_score', away_score),
                        ]:
                            if value is None:
                                print(f"Error: Missing compulsory field '{field_name}' in H2H row")
                        h2h_matches.append({
                            'date': date,
                            'home_team': home_team,
                            'away_team': away_team,
                            'home_score': home_score,
                            'away_score': away_score,
                            'competition': competition  # optional
                        })
                    except Exception as e:
                        print(f"Error extracting h2h row: {e}")
                        continue
            self._last_extracted_data = h2h_matches
            
            if status_callback:
                status_callback(f"H2H data extraction completed. Found {len(h2h_matches)} matches.")
            
            return h2h_matches
        except Exception as e:
            print(f"Error extracting h2h data: {e}")
            self._last_extracted_data = None
            return []

    def get_last_extracted_data(self) -> Optional[List[Dict[str, Optional[str]]]]:
        try:
            return self._last_extracted_data
        except Exception as e:
            print(f"Error getting last extracted h2h data: {e}")
            return None

    def extract(self, field: str, index: int) -> Optional[str]:
        if self._last_extracted_data and 0 <= index < len(self._last_extracted_data):
            return self._last_extracted_data[index].get(field)
        return None

    def get_home_team(self, index: int) -> Optional[str]:
        return self.extract('home_team', index)

    def get_away_team(self, index: int) -> Optional[str]:
        return self.extract('away_team', index)

    def get_date(self, index: int) -> Optional[str]:
        return self.extract('date', index)

    def get_home_score(self, index: int) -> Optional[str]:
        return self.extract('home_score', index)

    def get_away_score(self, index: int) -> Optional[str]:
        return self.extract('away_score', index)

    def get_competition(self, index: int) -> Optional[str]:
        return self.extract('competition', index)

    # Make previous index-based extract_* methods private or remove them for clarity
    # (e.g., _extract_date, _extract_home_team, etc. if not used internally) 