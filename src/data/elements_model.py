from dataclasses import dataclass, field
from typing import Optional, Any, List

@dataclass
class MatchElements:
    country: Optional[Any] = None
    league: Optional[Any] = None
    home_team: Optional[Any] = None
    away_team: Optional[Any] = None
    date: Optional[Any] = None
    time: Optional[Any] = None
    match_id: Optional[Any] = None
    # Add more fields as needed for match details

@dataclass
class OddsElements:
    home_odds: Optional[Any] = None
    away_odds: Optional[Any] = None
    match_total: Optional[Any] = None
    over_odds: Optional[Any] = None
    under_odds: Optional[Any] = None
    all_totals: List[Any] = field(default_factory=list)
    # Add more fields as needed for odds details

@dataclass
class H2HElements:
    h2h_section: Optional[Any] = None
    h2h_rows: List[Any] = field(default_factory=list)
    h2h_row_count: int = 0
    # Add more fields as needed for h2h details
    # Each row dict can now include a 'competition' field 