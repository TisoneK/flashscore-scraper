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

            # Fallback: Try extracting from window title if scores are missing
            if (home_score is None or away_score is None) and self._loader and hasattr(self._loader, 'get_window_title'):
                title = self._loader.get_window_title() if self._loader else None
                if title:
                    fallback_home, fallback_away = self.extract_scores_from_title(title, status_callback=status_callback)
                    if fallback_home is not None and fallback_away is not None:
                        home_score, away_score = fallback_home, fallback_away

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

        If the status element is empty/None but scores are present, falls back to
        checking the page title for a score pattern (e.g., "78-81") to infer
        "FINISHED". This handles Flashscore pages where the status CSS element
        exists but has empty text (common for finished matches that went to OT).

        :param elements: Optionally, a ResultsElements object to extract from.
        :param status_callback: Optional callback function for status updates.
        :return: Match status string or None if not available.
        """
        try:
            if status_callback:
                status_callback("Extracting match status...")

            elements = elements or (self._loader.elements if self._loader else None)

            if elements is None:
                return None

            def normalize(value):
                if value is None:
                    return None
                value = value.strip() if isinstance(value, str) else value
                return value if value else None

            # Extract match status from the status element
            match_status = normalize(elements.match_status.text) if elements.match_status and getattr(elements.match_status, 'text', None) else None

            if match_status:
                is_valid, error = self.results_data_verifier.verify_match_status(match_status)
                if not is_valid:
                    match_status = None

            # ── Fallback: if status is None but scores exist, infer from page title ──
            # Flashscore sometimes returns an empty status element for finished
            # matches (especially after overtime). The page title contains the
            # final score (e.g., "BEN 78-81 MEL | Bendigo Braves W v ..."), so we
            # can check if both scores are present and infer "FINISHED".
            if not match_status:
                home_score = normalize(elements.home_score.text) if elements.home_score and getattr(elements.home_score, 'text', None) else None
                away_score = normalize(elements.away_score.text) if elements.away_score and getattr(elements.away_score, 'text', None) else None

                if home_score and away_score:
                    # Both scores are present — match must be finished or in progress.
                    # Check the page title for additional context.
                    try:
                        title = self._loader.driver.title if self._loader and hasattr(self._loader, 'driver') else ""
                        if title:
                            title_upper = title.upper()
                            import re
                            has_score = bool(re.search(r'\d+\s*[-:]\s*\d+', title))

                            # Live indicators — if ANY of these are present, the match
                            # is still in progress (not finished). Includes OT indicators
                            # because a match in overtime is NOT finished yet.
                            has_live = any(kw in title_upper for kw in [
                                'Q1', 'Q2', 'Q3', 'Q4',
                                'HT', 'HALF TIME', 'HALFTIME',
                                'LIVE', 'IN PROGRESS',
                                'QUARTER', 'PERIOD',
                                # Overtime — live OT means the match is NOT finished
                                'OT ', ' OT', '(OT)', 'OVERTIME',
                                '1ST OT', '2ND OT', '3RD OT',
                                'AFTER OT', 'AFTER OVERTIME',
                            ])

                            # Also check the status element text itself for OT indicators
                            # (the element was found but text was empty — but let's double-check
                            # by also checking the full page body for live OT indicators)
                            if not has_live and elements.match_status:
                                try:
                                    status_text = elements.match_status.text or ""
                                    status_upper = status_text.upper()
                                    if any(kw in status_upper for kw in ['OT', 'OVERTIME', 'QUARTER', 'PERIOD']):
                                        has_live = True
                                except Exception:
                                    pass

                            if has_score and not has_live:
                                match_status = "FINISHED"
                                logger.info(f"[ResultsDataExtractor] Inferred FINISHED from page title (scores: {home_score}-{away_score})")
                            elif has_score and has_live:
                                match_status = "IN_PROGRESS"
                                logger.info(f"[ResultsDataExtractor] Inferred IN_PROGRESS from page title (live indicators found, scores: {home_score}-{away_score})")
                    except Exception:
                        pass

                    # If we still don't have a status but have scores:
                    # DON'T default to FINISHED — the match might be in live OT
                    # with an empty status element. Check if the match start time
                    # was more than 4 hours ago (basketball + OT rarely exceeds 4h).
                    # If > 4h ago → FINISHED (must be done by now).
                    # If < 4h ago → IN_PROGRESS (might still be playing OT).
                    if not match_status:
                        try:
                            from datetime import datetime, timezone
                            # Can't easily get match start time here, so use a simpler heuristic:
                            # Check if the page has any "live" CSS classes or indicators
                            # that we might have missed. If not, default to FINISHED only
                            # if the page URL contains "/summary/" (summary page = finished).
                            # For live matches, Flashscore shows the "match" page, not "summary".
                            current_url = self._loader.driver.current_url if self._loader and hasattr(self._loader, 'driver') else ""
                            if '/summary/' in current_url:
                                match_status = "FINISHED"
                                logger.info(f"[ResultsDataExtractor] Defaulting to FINISHED (on summary page, scores: {home_score}-{away_score})")
                            else:
                                # Not on summary page — could be live. Mark as IN_PROGRESS
                                # to be safe. The next scrape will catch it as FINISHED
                                # once Flashscore moves it to the summary page.
                                match_status = "IN_PROGRESS"
                                logger.info(f"[ResultsDataExtractor] Defaulting to IN_PROGRESS (not on summary page, scores: {home_score}-{away_score})")
                        except Exception:
                            # Can't determine — default to FINISHED (most common case)
                            match_status = "FINISHED"
                            logger.info(f"[ResultsDataExtractor] Defaulting to FINISHED (scores present: {home_score}-{away_score})")

            if status_callback:
                status_callback("Match status extraction completed.")

            return match_status

        except Exception as e:
            logger.error(f"Error extracting match status: {e}")
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

    def extract_scores_from_title(self, title: str, status_callback=None):
        """
        Extract home and away scores from a window title string.
        :param title: The window title string.
        :param status_callback: Optional callback for status updates.
        :return: (home_score, away_score) or (None, None)
        """
        if status_callback:
            status_callback(f"[Fallback] Attempting to extract scores from window title: {title}")
        try:
            score_pattern = r'^.*?(\d+)\s*[-:]\s*(\d+).*$'
            import re
            match = re.match(score_pattern, title.strip())
            if not match:
                if status_callback:
                    status_callback(f"[Fallback] Invalid score format in title: {title}")
                return None, None
            home_score = int(match.group(1))
            away_score = int(match.group(2))
            is_valid, error = self.results_data_verifier.verify_scores(home_score, away_score)
            if not is_valid:
                if status_callback:
                    status_callback(f"[Fallback] Error verifying scores from title: {error}")
                return None, None
            if status_callback:
                status_callback(f"[Fallback] Successfully extracted scores from title: {home_score}-{away_score}")
            return home_score, away_score
        except Exception as e:
            if status_callback:
                status_callback(f"[Fallback] Error extracting scores from window title: {e}")
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