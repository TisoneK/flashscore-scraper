"""Data models for the Flashscore scraper."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from src.config import MIN_H2H_MATCHES

@dataclass
class OddsModel:
    match_id: str = ""  # FK to MatchModel.match_id
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    match_total: Optional[float] = None
    # Add more fields as needed

@dataclass
class H2HMatchModel:
    match_id: str = ""  # FK to MatchModel.match_id
    date: str = ""
    home_team: str = ""
    away_team: str = ""
    home_score: int = 0
    away_score: int = 0
    competition: Optional[str] = ""

@dataclass
class MatchModel:
    match_id: str
    country: str
    league: str
    home_team: str
    away_team: str
    date: str
    time: str
    created_at: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    odds: Optional[OddsModel] = None
    h2h_matches: List[H2HMatchModel] = field(default_factory=list)
    status: str = "complete"  # 'complete' or 'incomplete'
    skip_reason: Optional[str] = None  # Reason for being incomplete

    @classmethod
    def create(cls, **kwargs) -> 'MatchModel':
        # Accept status and skip_reason if present
        return cls(
            match_id=kwargs.get('match_id', ''),
            country=kwargs.get('country', ''),
            league=kwargs.get('league', ''),
            home_team=kwargs.get('home_team', ''),
            away_team=kwargs.get('away_team', ''),
            date=kwargs.get('date', ''),
            time=kwargs.get('time', ''),
            created_at=kwargs.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            odds=kwargs.get('odds', None),
            h2h_matches=kwargs.get('h2h_matches', []),
            status=kwargs.get('status', 'complete'),
            skip_reason=kwargs.get('skip_reason', None)
        )

    def to_dict(self) -> dict:
        base_dict = {
            'match_id': self.match_id,
            'country': self.country,
            'league': self.league,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'date': self.date,
            'time': self.time,
            'created_at': self.created_at,
            'status': self.status,
            'skip_reason': self.skip_reason,
        }
        if self.odds:
            base_dict['odds'] = self.odds.__dict__
        base_dict['h2h_matches'] = [h2h.__dict__ for h2h in self.h2h_matches]
        return base_dict

@dataclass
class DetailedMatchModel(MatchModel):
    """Represents a match with detailed statistics."""
    quarter_scores: Dict[str, str] = field(default_factory=dict)
    team_stats: Dict[str, Dict[str, str]] = field(default_factory=dict)
    player_stats: Dict[str, Dict[str, str]] = field(default_factory=dict)
    team_fouls: Dict[str, int] = field(default_factory=dict)
    timeouts: Dict[str, int] = field(default_factory=dict)
    last_update: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    @classmethod
    def from_basic_match(cls, match: MatchModel) -> 'DetailedMatchModel':
        """Create a DetailedMatchModel from a basic MatchModel."""
        return cls(
            country=match.country,
            league=match.league,
            home_team=match.home_team,
            away_team=match.away_team,
            date=match.date,
            time=match.time,
            match_id=match.match_id,
            odds=match.odds,
            h2h_matches=match.h2h_matches
        )
    
    def to_dict(self) -> dict:
        """Convert detailed match to dictionary format."""
        base_dict = super().to_dict()
        base_dict.update({
            'quarter_scores': self.quarter_scores,
            'team_stats': self.team_stats,
            'player_stats': self.player_stats,
            'team_fouls': self.team_fouls,
            'timeouts': self.timeouts,
            'last_update': self.last_update
        })
        return base_dict

@dataclass
class TotalOddsModel:
    """Represents odds for a specific total (match, home, or away)."""
    alternative: float  # Bookie's total (nearest to 1.85 for over odds)
    over_odds: float
    under_odds: float

    def to_dict(self) -> dict:
        """Convert total odds to dictionary format."""
        return {
            'alternative': self.alternative,
            'over_odds': self.over_odds,
            'under_odds': self.under_odds
        }

@dataclass
class MatchOddsModel:
    """Represents betting odds for a match."""
    home_away: Dict[str, float] = field(default_factory=dict)  # {"home": 1.85, "away": 1.95}
    match_total: Optional[TotalOddsModel] = None
    home_total: Optional[TotalOddsModel] = None
    away_total: Optional[TotalOddsModel] = None
    all_totals: List[Dict[str, float]] = field(default_factory=list)  # List of all total alternatives
    last_update: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    def to_dict(self) -> dict:
        """Convert odds to dictionary format."""
        odds_dict = {
            'home_away': self.home_away,
            'last_update': self.last_update,
            'all_totals': self.all_totals
        }
        
        if self.match_total:
            odds_dict['match_total'] = self.match_total.to_dict()
        if self.home_total:
            odds_dict['home_total'] = self.home_total.to_dict()
        if self.away_total:
            odds_dict['away_total'] = self.away_total.to_dict()
            
        return odds_dict

@dataclass
class MatchCollectionModel:
    """Collection of matches with utility methods."""
    matches: List[MatchModel] = field(default_factory=list)

    def add_match(self, match: MatchModel):
        """Add a match to the collection."""
        self.matches.append(match)

    def get_match_ids(self) -> List[str]:
        """Get all match IDs from the collection."""
        return [match.match_id for match in self.matches if match.match_id]

    def get_upcoming_matches(self) -> List[MatchModel]:
        """Get all upcoming matches."""
        return [match for match in self.matches if match.date >= datetime.now().strftime('%Y-%m-%d')]

    def get_matches_by_country(self, country: str) -> List[MatchModel]:
        """Get all matches for a specific country."""
        return [match for match in self.matches if match.country.lower() == country.lower()]

    def get_matches_by_league(self, league: str) -> List[MatchModel]:
        """Get all matches for a specific league."""
        return [match for match in self.matches if match.league.lower() == league.lower()]

    def get_matches_with_odds(self) -> List[MatchModel]:
        """Get all matches that have odds data."""
        return [match for match in self.matches if match.odds is not None]

    def get_matches_with_h2h(self, min_h2h: int = MIN_H2H_MATCHES) -> List[MatchModel]:
        """Get all matches that have at least min_h2h H2H matches."""
        return [match for match in self.matches if len(match.h2h_matches) >= min_h2h]

class MatchDetailsModel:
    """Model for storing detailed match information."""
    
    def __init__(self, match_id: str, home_team: str, away_team: str, 
                 match_time: str, match_date: str, match_status: str):
        """Initialize match details.
        
        Args:
            match_id: ID of the match
            home_team: Name of the home team
            away_team: Name of the away team
            match_time: Time of the match
            match_date: Date of the match
            match_status: Status of the match
        """
        self.match_id = match_id
        self.home_team = home_team
        self.away_team = away_team
        self.match_time = match_time
        self.match_date = match_date
        self.match_status = match_status
        
    def __str__(self) -> str:
        """Return string representation of match details."""
        return (f"Match {self.match_id}: {self.home_team} vs {self.away_team} "
                f"on {self.match_date} at {self.match_time} ({self.match_status})") 
    