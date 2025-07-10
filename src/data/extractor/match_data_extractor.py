from typing import Optional, Dict
from ..elements_model import MatchElements
from src.utils.utils import format_date, split_date_time
from src.data.verifier.match_data_verifier import MatchDataVerifier
from ...models import MatchModel

class MatchDataExtractor:
    def __init__(self, loader):
        """
        :param loader: An instance of MatchDataLoader or similar, with an 'elements' attribute.
        """
        try:
            self._loader = loader
            self._last_extracted_data: Optional[Dict[str, Optional[str]]] = None
            self.match_data_verifier = MatchDataVerifier(getattr(loader, 'driver', None))
        except Exception as e:
            print(f"Error initializing MatchDataExtractor: {e}")
            self._loader = None
            self._last_extracted_data = None

    def extract_match_data(self, elements: Optional[MatchElements] = None) -> MatchModel:
        """
        Extracts match data from the loader's elements or from a provided elements object.
        :param elements: Optionally, a MatchElements object to extract from.
        :return: A MatchModel object with the extracted data.
        """
        try:
            elements = elements or self._loader.elements

            def normalize(value):
                if value is None:
                    return None
                value = value.strip() if isinstance(value, str) else value
                return value if value else None

            # Extract and verify each field
            country = normalize(elements.country.text) if elements.country and getattr(elements.country, 'text', None) else None
            is_valid, error = self.match_data_verifier.verify_country(country)
            if not is_valid:
                print(f"Error verifying country: {error}")
                country = None

            league = normalize(elements.league.text) if elements.league and getattr(elements.league, 'text', None) else None
            is_valid, error = self.match_data_verifier.verify_league(league)
            if not is_valid:
                print(f"Error verifying league: {error}")
                league = None

            home_team = normalize(elements.home_team.text) if elements.home_team and getattr(elements.home_team, 'text', None) else None
            is_valid, error = self.match_data_verifier.verify_home_team(home_team)
            if not is_valid:
                print(f"Error verifying home_team: {error}")
                home_team = None

            away_team = normalize(elements.away_team.text) if elements.away_team and getattr(elements.away_team, 'text', None) else None
            is_valid, error = self.match_data_verifier.verify_away_team(away_team)
            if not is_valid:
                print(f"Error verifying away_team: {error}")
                away_team = None

            date_time_str = normalize(elements.date.text) if elements.date and getattr(elements.date, 'text', None) else None
            date, time = split_date_time(date_time_str) if date_time_str else (None, None)

            is_valid, error = self.match_data_verifier.verify_date(date)
            if not is_valid:
                print(f"Error verifying date: {error}")
                date = None

            is_valid, error = self.match_data_verifier.verify_time(time)
            if not is_valid:
                print(f"Error verifying time: {error}")
                time = None

            match_id = elements.match_id if elements.match_id else None
            is_valid, error = self.match_data_verifier.verify_match_id(match_id)
            if not is_valid:
                print(f"Error verifying match_id: {error}")
                match_id = None

            # Create a MatchModel instance
            match_data = MatchModel(
                country=country,
                league=league,
                home_team=home_team,
                away_team=away_team,
                date=date,
                time=time,
                match_id=match_id
            )
            
            # For compatibility with existing property setters, we can store the dict representation
            self._last_extracted_data = match_data.to_dict()

            return match_data
        except Exception as e:
            print(f"Error extracting match data: {e}")
            self._last_extracted_data = None
            return MatchModel() # Return an empty model on error

    def get_last_extracted_data(self) -> Optional[Dict[str, Optional[str]]]:
        """Returns the last extracted match data, or None if not extracted yet."""
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
    def country(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('country') if self._last_extracted_data else None
        except Exception as e:
            print(f"Error getting country: {e}")
            return None

    @country.setter
    def country(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['country'] = value
        except Exception as e:
            print(f"Error setting country: {e}")

    @property
    def league(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('league') if self._last_extracted_data else None
        except Exception as e:
            print(f"Error getting league: {e}")
            return None

    @league.setter
    def league(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['league'] = value
        except Exception as e:
            print(f"Error setting league: {e}")

    @property
    def home_team(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('home_team') if self._last_extracted_data else None
        except Exception as e:
            print(f"Error getting home_team: {e}")
            return None

    @home_team.setter
    def home_team(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['home_team'] = value
        except Exception as e:
            print(f"Error setting home_team: {e}")

    @property
    def away_team(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('away_team') if self._last_extracted_data else None
        except Exception as e:
            print(f"Error getting away_team: {e}")
            return None

    @away_team.setter
    def away_team(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['away_team'] = value
        except Exception as e:
            print(f"Error setting away_team: {e}")

    @property
    def date(self) -> Optional[str]:
        try:
            raw_date = self._last_extracted_data.get('date') if self._last_extracted_data else None
            date_part, _ = split_date_time(raw_date)
            return format_date(date_part)
        except Exception as e:
            print(f"Error getting date: {e}")
            return None

    @date.setter
    def date(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['date'] = value
        except Exception as e:
            print(f"Error setting date: {e}")

    @property
    def time(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('time') if self._last_extracted_data else None
        except Exception as e:
            print(f"Error getting time: {e}")
            return None

    @time.setter
    def time(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['time'] = value
        except Exception as e:
            print(f"Error setting time: {e}")

    @property
    def match_id(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('match_id') if self._last_extracted_data else None
        except Exception as e:
            print(f"Error getting match_id: {e}")
            return None

    @match_id.setter
    def match_id(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['match_id'] = value
        except Exception as e:
            print(f"Error setting match_id: {e}")

    def extract(self, attribute_name: str) -> Optional[str]:
        """
        Returns the value of the specified attribute from the last extracted data.
        :param attribute_name: The name of the attribute to retrieve.
        :return: The value of the attribute, or None if not found.
        """
        try:
            if self._last_extracted_data is None:
                return None
            return self._last_extracted_data.get(attribute_name)
        except Exception as e:
            print(f"Error extracting attribute '{attribute_name}': {e}")
            return None 