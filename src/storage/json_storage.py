"""JSON storage operations for the Flashscore scraper."""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path

from ..models import MatchModel
from src.config import MIN_H2H_MATCHES

logger = logging.getLogger(__name__)

class JSONStorage:
    """Handles saving and loading match data to/from JSON files."""
    
    def __init__(self, base_dir: str = "output/json"):
        """Initialize JSON storage.
        
        Args:
            base_dir: Base directory for storing JSON files
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_daily_filepath(self) -> Path:
        """Get the filepath for today's JSON file.
        
        Returns:
            Path: Path to today's JSON file
        """
        today = datetime.now().strftime("%d%m%y")
        return self.base_dir / f"matches_{today}.json"
        
    def _load_existing_matches(self, filepath: Path) -> Dict[str, dict]:
        """Load existing matches from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Dictionary of matches keyed by match_id
        """
        if not filepath.exists() or filepath.stat().st_size == 0:
            return {}
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {match['match_id']: match for match in data.get('matches', [])}
        except Exception as e:
            logger.error(f"Error loading existing matches from {filepath}: {str(e)}")
            return {}
            
    def save_matches(self, matches: List[MatchModel], filename: Optional[str] = None) -> bool:
        print(f"[DEBUG] JSONStorage.save_matches called with {len(matches)} match(es). First match_id: {getattr(matches[0], 'match_id', None) if matches else None}")
        try:
            filepath = self._get_daily_filepath() if filename is None else self.base_dir / filename

            # Load existing data structure or create a new one
            if filepath.exists() and filepath.stat().st_size > 0:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    'metadata': {'skipped_matches': {'details': []}},
                    'matches': []
                }

            # Use dictionaries for efficient lookup and updates
            existing_complete = {m['match_id']: m for m in data.get('matches', [])}
            existing_skipped = {sm['match_id']: sm for sm in data.get('metadata', {}).get('skipped_matches', {}).get('details', [])}

            for match in matches:
                match_id = match.match_id
                print(f"[DEBUG] Processing match for JSON output: match_id={match_id}, status={getattr(match, 'status', None)}")
                if match.status == "complete":
                    existing_complete[match_id] = match.to_dict()
                    if match_id in existing_skipped:
                        del existing_skipped[match_id]
                else:
                    if match_id not in existing_complete:
                        existing_skipped[match_id] = {
                            "match_id": match_id,
                            "reason": match.skip_reason or "unknown"
                        }
            
            final_complete_list = list(existing_complete.values())
            final_skipped_list = list(existing_skipped.values())
            print(f"[DEBUG] Saving {len(final_complete_list)} complete matches and {len(final_skipped_list)} skipped matches to {filepath}")

            data['matches'] = final_complete_list
            data['metadata'].update({
                'total_matches': len(final_complete_list),
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'skipped_matches': {
                    'total': len(final_skipped_list),
                    'details': final_skipped_list
                }
            })
            if 'file_info' not in data['metadata']:
                data['metadata']['file_info'] = {}
            data['metadata']['file_info']['filename'] = filepath.name
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            size_bytes = filepath.stat().st_size
            data['metadata']['file_info']['size_bytes'] = size_bytes
            data['metadata']['file_info']['created_at'] = datetime.fromtimestamp(filepath.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S')

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"[DEBUG] JSON file updated for match {matches[0].match_id if matches else None}. Total complete: {len(final_complete_list)}, total skipped: {len(final_skipped_list)}.")
            logger.info(f"JSON file updated for match {matches[0].match_id}. Total complete: {len(final_complete_list)}, total skipped: {len(final_skipped_list)}.")
            return True
        except Exception as e:
            print(f"[DEBUG] Error saving matches to {filepath}: {str(e)}")
            logger.error(f"Error saving matches to {filepath}: {str(e)}")
            return False

    def get_processed_match_ids(self, filename: Optional[str] = None) -> set:
        """Return a set of (match_id, skip_reason) tuples for all processed matches (complete and incomplete) from the JSON file."""
        filepath = self._get_daily_filepath() if filename is None else self.base_dir / filename
        processed = set()
        if not filepath.exists() or filepath.stat().st_size == 0:
            return processed
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Add all complete match ids with their skip_reason (or a default)
            for match in data.get('matches', []):
                match_id = match.get('match_id')
                if match_id:
                    # 'processed successfully' is a good default for complete matches
                    skip_reason = match.get('skip_reason', 'processed successfully')
                    processed.add((match_id, skip_reason))
            # Add all skipped match ids with their reason
            skipped = data.get('metadata', {}).get('skipped_matches', {}).get('details', [])
            for entry in skipped:
                match_id = entry.get('match_id')
                if match_id:
                    reason = entry.get('reason', 'unknown')
                    processed.add((match_id, reason))
        except Exception as e:
            logger.error(f"Error loading processed match ids from {filepath}: {str(e)}")
        return processed
            
    def load_matches(self, filename: str) -> List[MatchModel]:
        """Load matches from a JSON file.
        
        Args:
            filename: Name of the JSON file to load
            
        Returns:
            List[MatchModel]: List of loaded matches
        """
        filepath = self.base_dir / filename
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            matches = []
            for match_data in data["matches"]:
                match = MatchModel.create(
                    country=match_data["country"],
                    league=match_data["league"],
                    home_team=match_data["home_team"],
                    away_team=match_data["away_team"],
                    date=match_data["match_date"],
                    time=match_data["match_time"],
                    match_id=match_data["match_id"]
                )
                matches.append(match)
                
            logger.info(f"Loaded {len(matches)} matches from {filepath}")
            return matches
            
        except Exception as e:
            logger.error(f"Error loading matches from JSON: {e}")
            raise 