import glob
import json
import os
import logging
from typing import List, Optional
from src.models import MatchModel, OddsModel, H2HMatchModel

def load_matches(date_filter: Optional[str] = None, status: str = "complete", debug: bool = False) -> List[MatchModel]:
    """
    Load matches from JSON files in output/json/.
    Optionally filter by date (format: 'dd.mm.yyyy') and status (default: 'complete').
    Returns a list of MatchModel objects.
    """
    logger = logging.getLogger(__name__)
    
    # Always resolve path relative to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_dir = os.path.join(base_dir, "output", "json")
    
    if debug:
        logger.debug(f"date_filter: {date_filter}")
        logger.debug(f"status: {status}")
    
    # Pre-filter files by date if date_filter is provided
    if date_filter:
        # Convert date filter to file pattern (ddmmyy format)
        try:
            day, month, year = date_filter.split('.')
            file_pattern = f"matches_{day.zfill(2)}{month.zfill(2)}{year[-2:]}.json"
            match_files = glob.glob(os.path.join(json_dir, file_pattern))
            if debug:
                logger.debug(f"Looking for files matching pattern: {file_pattern}")
        except ValueError:
            logger.error(f"Invalid date format: {date_filter}. Expected format: dd.mm.yyyy")
            return []
    else:
        # Load all files if no date filter
        match_files = glob.glob(os.path.join(json_dir, "matches_*.json"))
    
    if debug:
        logger.info(f"Found files: {match_files}")
    
    all_matches = []
    for file in match_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                matches = data.get("matches", [])
                if debug:
                    logger.debug(f"{file}: {len(matches)} matches loaded")
                
                # Filter matches by status and date
                for m in matches:
                    if debug:
                        logger.debug(f"Match {m.get('match_id')}: date={m.get('date')}, status={m.get('status')}")
                    
                    # Check status first
                    if m.get("status") != status:
                        continue
                    
                    # Check date if filter is provided
                    if date_filter and m.get("date") != date_filter:
                        continue
                    
                    all_matches.append(m)
                    
        except Exception as e:
            logger.error(f"Error loading {file}: {e}")
    
    if debug:
        logger.debug(f"Total matches after filtering: {len(all_matches)}")
        if all_matches:
            logger.debug(f"Dates of filtered matches: {[m.get('date') for m in all_matches]}")
    
    # Convert to MatchModel objects
    match_models = []
    for m in all_matches:
        odds = m.get("odds", {})
        h2h = m.get("h2h_matches", [])
        try:
            match = MatchModel(
                match_id=m.get("match_id", ""),
                country=m.get("country", ""),
                league=m.get("league", ""),
                home_team=m.get("home_team", ""),
                away_team=m.get("away_team", ""),
                date=m.get("date", ""),
                time=m.get("time", ""),
                odds=OddsModel(
                    match_id=odds.get("match_id", ""),
                    home_odds=odds.get("home_odds"),
                    away_odds=odds.get("away_odds"),
                    over_odds=odds.get("over_odds"),
                    under_odds=odds.get("under_odds"),
                    match_total=odds.get("match_total")
                ),
                h2h_matches=[
                    H2HMatchModel(
                        match_id=hm.get("match_id", ""),
                        date=hm.get("date", ""),
                        home_team=hm.get("home_team", ""),
                        away_team=hm.get("away_team", ""),
                        home_score=hm.get("home_score", 0),
                        away_score=hm.get("away_score", 0),
                        competition=hm.get("competition", "")
                    ) for hm in h2h
                ],
                status=m.get("status", status),
                skip_reason=m.get("skip_reason", None)
            )
            match_models.append(match)
        except Exception as e:
            logger.error(f"Error parsing match {m.get('match_id')}: {e}")
    
    return match_models 