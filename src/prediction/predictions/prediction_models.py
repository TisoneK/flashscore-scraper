"""
Prediction Models for ScoreWise Algorithm

This module defines the data models for prediction results and calculations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class PredictionRecommendation(Enum):
    """Enumeration for prediction recommendations."""
    OVER = "OVER"
    UNDER = "UNDER"
    NO_BET = "NO_BET"


class TeamWinnerPrediction(Enum):
    """Enumeration for team winner predictions."""
    HOME_TEAM = "HOME_TEAM"
    AWAY_TEAM = "AWAY_TEAM"
    NO_WINNER_PREDICTION = "NO_WINNER_PREDICTION"


class ConfidenceLevel(Enum):
    """Enumeration for confidence levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class WinningStreakData:
    """Data about winning streaks and patterns."""
    home_team_h2h_wins: int
    away_team_h2h_wins: int
    home_team_recent_wins: int  # Last 3 games
    away_team_recent_wins: int  # Last 3 games
    home_team_winning_streak: int  # Current streak
    away_team_winning_streak: int  # Current streak
    total_h2h_matches: int


@dataclass
class ScoreWisePrediction:
    """Result of ScoreWise prediction calculation."""
    
    # Basic prediction info
    match_id: str
    recommendation: PredictionRecommendation
    team_winner: TeamWinnerPrediction
    confidence: ConfidenceLevel
    
    # Algorithm calculations
    average_rate: float
    matches_above_line: int
    matches_below_line: int
    total_matches: int
    
    # Test adjustments
    decrement_test: int
    increment_test: int
    
    # Winning streak data
    winning_streak_data: WinningStreakData
    
    # Input data
    bookmaker_line: float
    h2h_totals: List[int]
    rate_values: List[float]
    
    # Additional details
    calculation_details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prediction to dictionary format."""
        return {
            'match_id': self.match_id,
            'recommendation': self.recommendation.value,
            'team_winner': self.team_winner.value,
            'confidence': self.confidence.value,
            'average_rate': self.average_rate,
            'matches_above_line': self.matches_above_line,
            'matches_below_line': self.matches_below_line,
            'total_matches': self.total_matches,
            'decrement_test': self.decrement_test,
            'increment_test': self.increment_test,
            'winning_streak_data': {
                'home_team_h2h_wins': self.winning_streak_data.home_team_h2h_wins,
                'away_team_h2h_wins': self.winning_streak_data.away_team_h2h_wins,
                'home_team_recent_wins': self.winning_streak_data.home_team_recent_wins,
                'away_team_recent_wins': self.winning_streak_data.away_team_recent_wins,
                'home_team_winning_streak': self.winning_streak_data.home_team_winning_streak,
                'away_team_winning_streak': self.winning_streak_data.away_team_winning_streak,
                'total_h2h_matches': self.winning_streak_data.total_h2h_matches
            },
            'bookmaker_line': self.bookmaker_line,
            'h2h_totals': self.h2h_totals,
            'rate_values': self.rate_values,
            'calculation_details': self.calculation_details,
            'created_at': self.created_at.isoformat()
        }
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the prediction."""
        return (
            f"ScoreWise Prediction: {self.recommendation.value} "
            f"(Team Winner: {self.team_winner.value}, "
            f"Confidence: {self.confidence.value}, "
            f"Avg Rate: {self.average_rate:.2f})"
        )


@dataclass
class PredictionResult:
    """Container for prediction results with metadata."""
    
    success: bool
    prediction: Optional[ScoreWisePrediction] = None
    error_message: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if the prediction result is valid."""
        return self.success and self.prediction is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        result = {
            'success': self.success,
            'error_message': self.error_message,
            'validation_errors': self.validation_errors
        }
        
        if self.prediction:
            result['prediction'] = self.prediction.to_dict()
        
        return result 