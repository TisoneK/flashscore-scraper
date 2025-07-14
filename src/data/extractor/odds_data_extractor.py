import logging
from typing import Optional, Dict
from src.data.elements_model import OddsElements
from src.data.verifier.odds_data_verifier import OddsDataVerifier
from src.core.exceptions import DataNotFoundError, DataParseError, DataValidationError, DataUnavailableWarning

logger = logging.getLogger(__name__)

class OddsDataExtractor:
    def __init__(self, loader):
        """
        :param loader: An instance of OddsDataLoader or similar, with an 'elements' attribute.
        """
        try:
            self._loader = loader
            self._last_extracted_data: Optional[Dict[str, Optional[str]]] = None
            self.odds_data_verifier = OddsDataVerifier(getattr(loader, 'driver', None))
        except Exception as e:
            logger.error(f"Error initializing OddsDataExtractor: {e}")
            self._loader = None
            self._last_extracted_data = None

    def extract_home_away_odds(self, elements: Optional[OddsElements] = None, status_callback=None) -> Dict[str, Optional[str]]:
        try:
            if status_callback:
                status_callback("Extracting home/away odds...")
            
            elements = elements or (self._loader.elements if self._loader else None)
            
            if elements is None:
                logger.error("No elements available for home/away odds extraction")
                return {
                    'home_odds': None,
                    'away_odds': None,
                }
            
            # Extract and verify only home_odds and away_odds
            home_odds = elements.home_odds.text.strip() if elements.home_odds and getattr(elements.home_odds, 'text', None) else None
            self.home_odds = home_odds
            away_odds = elements.away_odds.text.strip() if elements.away_odds and getattr(elements.away_odds, 'text', None) else None
            self.away_odds = away_odds
            data = {
                'home_odds': self.home_odds,
                'away_odds': self.away_odds,
            }
            self._last_extracted_data = data
            
            if status_callback:
                status_callback("Home/away odds extraction completed.")
            
            return data
        except Exception as e:
            logger.error(f"Error extracting home/away odds data: {e}")
            self._last_extracted_data = None
            return {
                'home_odds': None,
                'away_odds': None,
            }

    def extract_over_under_odds(self, elements: Optional[OddsElements] = None, status_callback=None) -> Dict[str, Optional[str]]:
        try:
            if status_callback:
                status_callback("Extracting over/under odds...")
            
            elements = elements or (self._loader.elements if self._loader else None)
            
            if elements is None:
                logger.error("No elements available for over/under odds extraction")
                return {
                    'match_total': None,
                    'over_odds': None,
                    'under_odds': None,
                }
            
            # Extract and verify only match_total, over_odds, under_odds
            match_total = elements.match_total.text.strip() if elements.match_total and getattr(elements.match_total, 'text', None) else None
            is_valid, error = self.odds_data_verifier.verify_match_total(match_total)
            if not is_valid:
                logger.warning(f"Error verifying match_total: {error}")
                match_total = None
            self.match_total = match_total

            over_odds = elements.over_odds.text.strip() if elements.over_odds and getattr(elements.over_odds, 'text', None) else None
            is_valid, error = self.odds_data_verifier.verify_over_odds(over_odds)
            if not is_valid:
                logger.warning(f"Error verifying over_odds: {error}")
                over_odds = None
            self.over_odds = over_odds

            under_odds = elements.under_odds.text.strip() if elements.under_odds and getattr(elements.under_odds, 'text', None) else None
            is_valid, error = self.odds_data_verifier.verify_under_odds(under_odds)
            if not is_valid:
                logger.warning(f"Error verifying under_odds: {error}")
                under_odds = None
            self.under_odds = under_odds

            data = {
                'match_total': self.match_total,
                'over_odds': self.over_odds,
                'under_odds': self.under_odds,
            }
            self._last_extracted_data = data
            
            if status_callback:
                status_callback("Over/under odds extraction completed.")
            
            return data
        except Exception as e:
            logger.error(f"Error extracting over/under odds data: {e}")
            self._last_extracted_data = None
            return {
                'match_total': None,
                'over_odds': None,
                'under_odds': None,
            }

    def extract_odds_data(self, elements: Optional[OddsElements] = None, status_callback=None) -> Dict[str, Optional[str]]:
        """
        Extracts odds data from the loader's elements or from a provided elements object.
        :param elements: Optionally, an OddsElements object to extract from.
        :param status_callback: Optional callback function for status updates.
        :return: Dictionary with odds data.
        """
        try:
            if status_callback:
                status_callback("Extracting complete odds data...")
            
            elements = elements or (self._loader.elements if self._loader else None)
            
            if elements is None:
                logger.error("No elements available for complete odds extraction")
                return {
                    'home_odds': None,
                    'away_odds': None,
                    'match_total': None,
                    'over_odds': None,
                    'under_odds': None,
                }

            # Extract and verify each field, then assign via property setter
            if status_callback:
                status_callback("Extracting home/away odds...")
            home_odds = elements.home_odds.text.strip() if elements.home_odds and getattr(elements.home_odds, 'text', None) else None
            # home_odds is optional
            self.home_odds = home_odds

            away_odds = elements.away_odds.text.strip() if elements.away_odds and getattr(elements.away_odds, 'text', None) else None
            # away_odds is optional
            self.away_odds = away_odds

            if status_callback:
                status_callback("Extracting over/under odds...")
            match_total = elements.match_total.text.strip() if elements.match_total and getattr(elements.match_total, 'text', None) else None
            is_valid, error = self.odds_data_verifier.verify_match_total(match_total)
            if not is_valid:
                logger.warning(f"Error verifying match_total: {error}")
                match_total = None
            self.match_total = match_total

            over_odds = elements.over_odds.text.strip() if elements.over_odds and getattr(elements.over_odds, 'text', None) else None
            is_valid, error = self.odds_data_verifier.verify_over_odds(over_odds)
            if not is_valid:
                logger.warning(f"Error verifying over_odds: {error}")
                over_odds = None
            self.over_odds = over_odds

            under_odds = elements.under_odds.text.strip() if elements.under_odds and getattr(elements.under_odds, 'text', None) else None
            is_valid, error = self.odds_data_verifier.verify_under_odds(under_odds)
            if not is_valid:
                logger.warning(f"Error verifying under_odds: {error}")
                under_odds = None
            self.under_odds = under_odds

            # Build the return dictionary using property getters
            data = {
                'home_odds': self.home_odds,
                'away_odds': self.away_odds,
                'match_total': self.match_total,
                'over_odds': self.over_odds,
                'under_odds': self.under_odds,
            }
            self._last_extracted_data = data
            
            if status_callback:
                status_callback("Complete odds data extraction finished.")
            
            return data
        except Exception as e:
            logger.error(f"Error extracting odds data: {e}")
            self._last_extracted_data = None
            return {
                'home_odds': None,
                'away_odds': None,
                'match_total': None,
                'over_odds': None,
                'under_odds': None,
            }

    def get_last_extracted_data(self) -> Optional[Dict[str, Optional[str]]]:
        try:
            return self._last_extracted_data
        except Exception as e:
            logger.error(f"Error getting last extracted data: {e}")
            return None

    def set_loader(self, loader):
        try:
            self._loader = loader
        except Exception as e:
            logger.error(f"Error setting loader: {e}")

    def get_loader(self):
        try:
            return self._loader
        except Exception as e:
            logger.error(f"Error getting loader: {e}")
            return None

    @property
    def home_odds(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('home_odds') if self._last_extracted_data else None
        except Exception as e:
            logger.error(f"Error getting home_odds: {e}")
            return None

    @home_odds.setter
    def home_odds(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['home_odds'] = value
        except Exception as e:
            logger.error(f"Error setting home_odds: {e}")

    @property
    def away_odds(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('away_odds') if self._last_extracted_data else None
        except Exception as e:
            logger.error(f"Error getting away_odds: {e}")
            return None

    @away_odds.setter
    def away_odds(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['away_odds'] = value
        except Exception as e:
            logger.error(f"Error setting away_odds: {e}")

    @property
    def match_total(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('match_total') if self._last_extracted_data else None
        except Exception as e:
            logger.error(f"Error getting match_total: {e}")
            return None

    @match_total.setter
    def match_total(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['match_total'] = value
        except Exception as e:
            logger.error(f"Error setting match_total: {e}")

    @property
    def over_odds(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('over_odds') if self._last_extracted_data else None
        except Exception as e:
            logger.error(f"Error getting over_odds: {e}")
            return None

    @over_odds.setter
    def over_odds(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['over_odds'] = value
        except Exception as e:
            logger.error(f"Error setting over_odds: {e}")

    @property
    def under_odds(self) -> Optional[str]:
        try:
            return self._last_extracted_data.get('under_odds') if self._last_extracted_data else None
        except Exception as e:
            logger.error(f"Error getting under_odds: {e}")
            return None

    @under_odds.setter
    def under_odds(self, value: Optional[str]):
        try:
            if self._last_extracted_data is None:
                self._last_extracted_data = {}
            self._last_extracted_data['under_odds'] = value
        except Exception as e:
            logger.error(f"Error setting under_odds: {e}")

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
            logger.error(f"Error extracting attribute '{attribute_name}': {e}")
            return None

    def get_all_totals(self):
        elements = self._loader.elements
        totals = []
        for row in elements.all_totals:
            alternative = row['alternative'].text.strip() if row['alternative'] and hasattr(row['alternative'], 'text') else None
            over = row['over'].text.strip() if row['over'] and hasattr(row['over'], 'text') else None
            under = row['under'].text.strip() if row['under'] and hasattr(row['under'], 'text') else None
            totals.append({'alternative': alternative, 'over': over, 'under': under})
        return totals

    def get_total_alternatives(self):
        """Return the total number of available over/under alternatives (lines)."""
        return len(self.get_all_totals())

    @property
    def best_alternative_target(self):
        return getattr(self, '_best_alternative_target', 1.85)

    @best_alternative_target.setter
    def best_alternative_target(self, value):
        self._best_alternative_target = value

    def has_half_point(self, alternative):
        """Check if the alternative has a .5 (half point)."""
        try:
            if alternative is None:
                return False
            # Convert to float and check if it has a decimal part of 0.5
            value = float(alternative)
            return value % 1 == 0.5
        except (ValueError, TypeError):
            return False

    def get_selected_alternative(self, index=None):
        """
        Return the best alternative based on priority:
        1. First priority: Over odds closest to 1.85 among alternatives with .5
        2. Second priority: Over odds closest to 1.85 among all alternatives (fallback)
        
        Always returns the best available alternative, never None.
        If index is given, use that index instead.
        """
        totals = self.get_all_totals()
        if not totals:
            return None
        if index is not None:
            if 0 <= index < len(totals):
                return totals[index]
            return None
        
        # Use the property for the target value
        target = self.best_alternative_target
        best_with_half = None
        best_overall = None
        min_diff_with_half = float('inf')
        min_diff_overall = float('inf')
        
        # Find the best alternative with .5 and the best overall
        for alt in totals:
            try:
                over = float(alt['over']) if alt['over'] is not None else 0.0
                alternative = alt['alternative']
                diff = abs(over - target)
                
                # Check if alternative has .5
                has_half = self.has_half_point(alternative)
                
                # Track best overall alternative
                if diff < min_diff_overall:
                    min_diff_overall = diff
                    best_overall = alt
                
                # Track best alternative with .5
                if has_half and diff < min_diff_with_half:
                    min_diff_with_half = diff
                    best_with_half = alt
                        
            except (ValueError, TypeError):
                continue
        
        # Return the best alternative with .5 if available, otherwise return best overall
        if best_with_half is not None:
            return best_with_half
        else:
            return best_overall

    def get_best_alternative(self):
        """
        Return the best available alternative based on priority:
        1. First priority: Over odds >= 1.85 AND alternative has .5
        2. Second priority: Over odds >= 1.85 (any alternative)
        3. Third priority: Closest over odds to 1.85 among all alternatives
        
        Always returns the best available alternative, never None.
        """
        totals = self.get_all_totals()
        if not totals:
            return None
            
        target = self.best_alternative_target
        best_with_half_and_target = None
        best_with_target = None
        best_overall = None
        min_diff_overall = float('inf')
        
        for alt in totals:
            try:
                over = float(alt['over']) if alt['over'] is not None else 0.0
                alternative = alt['alternative']
                diff = abs(over - target)
                has_half = self.has_half_point(alternative)
                
                # Track best overall alternative
                if diff < min_diff_overall:
                    min_diff_overall = diff
                    best_overall = alt
                
                # Track best alternative with over odds >= target
                if over >= target:
                    if best_with_target is None:
                        best_with_target = alt
                    # If it also has .5, it's even better
                    if has_half and best_with_half_and_target is None:
                        best_with_half_and_target = alt
                        
            except (ValueError, TypeError):
                continue
        
        # Return in order of priority
        if best_with_half_and_target is not None:
            logger.info(f"Best alternative with .5 and over >= {target}: {best_with_half_and_target['alternative']}")
            return best_with_half_and_target
        elif best_with_target is not None:
            logger.info(f"Best alternative with over >= {target}: {best_with_target['alternative']}")
            return best_with_target
        else:
            logger.warning(f"No alternative with over >= {target}, using closest overall: {best_overall['alternative']}")
            return best_overall

    def set_best_alternative_checker(self, target_over_odds=1.85):
        """Set the target over odds value for selecting the best alternative (default 1.85)."""
        self._best_alternative_target = target_over_odds 