"""
ScoreWise Calculator Implementation

This module implements the core ScoreWise prediction algorithm as documented in docs/index.md.
The algorithm analyzes historical head-to-head (H2H) matchup data and bookmaker alternatives
to provide recommendations for Over/Under bets and team winner predictions.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from src.models import MatchModel, H2HMatchModel, OddsModel
from ..predictions.prediction_models import (
    ScoreWisePrediction, 
    PredictionResult, 
    PredictionRecommendation, 
    TeamWinnerPrediction,
    ConfidenceLevel,
    WinningStreakData
)

logger = logging.getLogger(__name__)


@dataclass
class ScoreWiseConfig:
    """Configuration for ScoreWise calculator."""
    min_h2h_matches: int = 6
    # Exact rate thresholds as specified
    over_rate_min: float = 7.0  # OVER bets need rate between +7 and +15
    over_rate_max: float = 15.0
    under_rate_min: float = -15.0  # UNDER bets need rate between -15 and -7
    under_rate_max: float = -7.0
    test_adjustment: float = 5.0  # Reduced from 7.0 for more sensitivity
    min_matches_above_threshold: int = 3  # Reduced from 4 for more flexibility
    
    # Team winner prediction thresholds
    min_h2h_wins_for_winner: int = 4  # Minimum wins out of 6 H2H games
    min_recent_wins_for_streak: int = 3  # Minimum wins in last 3 games
    min_winning_streak: int = 3  # Minimum current winning streak


class ScoreWiseCalculator:
    """
    Implements the ScoreWise prediction algorithm.
    
    Algorithm Steps (from docs/index.md):
    1. Data Collection: Gather H2H data for at least 6 previous matchups
    2. Statistical Analysis: Calculate rate values and averages
    3. Test Adjustments: Apply ±7 point adjustments
    4. Prediction Rules: Apply ScoreWise prediction rules
    5. Team Winner Analysis: Analyze H2H winning patterns and streaks
    6. Enhanced Confidence: Consider winning streaks and patterns
    """
    
    def __init__(self, config: Optional[ScoreWiseConfig] = None):
        """Initialize the ScoreWise calculator."""
        self.config = config or ScoreWiseConfig()
        logger.info(f"ScoreWise Calculator initialized with config: {self.config}")
    
    def calculate_prediction(self, match: MatchModel) -> PredictionResult:
        """
        Calculate ScoreWise prediction for a match.
        
        Args:
            match: MatchModel containing H2H data and odds
            
        Returns:
            PredictionResult with prediction or error details
        """
        try:
            # Validate input requirements
            validation_result = self._validate_input(match)
            if not validation_result['valid']:
                return PredictionResult(
                    success=False,
                    error_message="Input validation failed",
                    validation_errors=validation_result['errors']
                )
            
            # Extract required data
            h2h_matches = match.h2h_matches
            bookmaker_line = match.odds.match_total if match.odds else None
            
            # Ensure bookmaker_line is not None (should be caught by validation, but double-check)
            if bookmaker_line is None:
                return PredictionResult(
                    success=False,
                    error_message="Bookmaker line is None"
                )
            
            # Calculate H2H totals
            h2h_totals = self._calculate_h2h_totals(h2h_matches)
            
            # Calculate rate values
            rate_values = self._calculate_rate_values(h2h_totals, bookmaker_line)
            
            # Calculate average rate
            average_rate = self._calculate_average_rate(rate_values)
            
            # Count matches above/below line
            matches_above = self._count_matches_above_line(h2h_totals, bookmaker_line)
            matches_below = len(h2h_totals) - matches_above
            
            # Apply test adjustments
            decrement_test, increment_test = self._apply_test_adjustments(
                h2h_totals, bookmaker_line
            )
            
            # Analyze winning streaks and patterns
            winning_streak_data = self._analyze_winning_patterns(h2h_matches, match)
            
            # Determine recommendation
            recommendation = self._determine_recommendation(
                average_rate, matches_above, matches_below, 
                decrement_test, increment_test
            )
            
            # Determine team winner
            team_winner = self._determine_team_winner(winning_streak_data)
            
            # Determine confidence level with enhanced logic
            confidence = self._determine_enhanced_confidence(
                average_rate, matches_above, matches_below,
                recommendation, winning_streak_data
            )
            
            # Create prediction
            prediction = ScoreWisePrediction(
                match_id=match.match_id,
                recommendation=recommendation,
                team_winner=team_winner,
                confidence=confidence,
                average_rate=average_rate,
                matches_above_line=matches_above,
                matches_below_line=matches_below,
                total_matches=len(h2h_totals),
                decrement_test=decrement_test,
                increment_test=increment_test,
                winning_streak_data=winning_streak_data,
                bookmaker_line=bookmaker_line,
                h2h_totals=h2h_totals,
                rate_values=rate_values,
                calculation_details={
                    'config': self.config.__dict__,
                    'algorithm_version': '2.0.0'
                }
            )
            
            logger.info(f"Prediction calculated for match {match.match_id}: {prediction.get_summary()}")
            return PredictionResult(success=True, prediction=prediction)
            
        except Exception as e:
            logger.error(f"Error calculating prediction for match {match.match_id}: {e}")
            return PredictionResult(
                success=False,
                error_message=f"Calculation error: {str(e)}"
            )
    
    def _validate_input(self, match: MatchModel) -> Dict[str, Any]:
        """
        Validate input requirements for ScoreWise calculation.
        
        Args:
            match: MatchModel to validate
            
        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        errors = []
        
        # Check if match has H2H data
        if not match.h2h_matches:
            errors.append("No H2H matches available")
        
        # Check minimum H2H matches requirement
        if len(match.h2h_matches) < self.config.min_h2h_matches:
            errors.append(
                f"Insufficient H2H matches: {len(match.h2h_matches)} "
                f"(minimum {self.config.min_h2h_matches} required)"
            )
        
        # Check if odds data is available
        if not match.odds:
            errors.append("No odds data available")
        elif match.odds.match_total is None:
            errors.append("No bookmaker line (match_total) available")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _calculate_h2h_totals(self, h2h_matches: List[H2HMatchModel]) -> List[int]:
        """
        Calculate total scores for each H2H match.
        
        Args:
            h2h_matches: List of H2H match models
            
        Returns:
            List of total scores for each match
        """
        totals = []
        for match in h2h_matches:
            total = match.home_score + match.away_score
            totals.append(total)
        
        logger.debug(f"Calculated H2H totals: {totals}")
        return totals
    
    def _calculate_rate_values(self, h2h_totals: List[int], bookmaker_line: float) -> List[float]:
        """
        Calculate rate values for each H2H match.
        
        Rate value = actual total - bookmaker line
        
        Args:
            h2h_totals: List of total scores from H2H matches
            bookmaker_line: Bookmaker's total line
            
        Returns:
            List of rate values
        """
        rate_values = []
        for total in h2h_totals:
            rate = total - bookmaker_line
            rate_values.append(rate)
        
        logger.debug(f"Calculated rate values: {rate_values}")
        return rate_values
    
    def _calculate_average_rate(self, rate_values: List[float]) -> float:
        """
        Calculate average rate across all H2H matches.
        
        Args:
            rate_values: List of rate values
            
        Returns:
            Average rate value
        """
        if not rate_values:
            return 0.0
        
        average_rate = sum(rate_values) / len(rate_values)
        logger.debug(f"Calculated average rate: {average_rate}")
        return average_rate
    
    def _count_matches_above_line(self, h2h_totals: List[int], line: float) -> int:
        """
        Count matches with total score above the line.
        
        Args:
            h2h_totals: List of total scores
            line: Bookmaker line to compare against
            
        Returns:
            Number of matches above the line
        """
        count = sum(1 for total in h2h_totals if total > line)
        logger.debug(f"Matches above line {line}: {count}/{len(h2h_totals)}")
        return count
    
    def _apply_test_adjustments(self, h2h_totals: List[int], bookmaker_line: float) -> Tuple[int, int]:
        """
        Apply ±7 point test adjustments.
        
        Args:
            h2h_totals: List of total scores
            bookmaker_line: Original bookmaker line
            
        Returns:
            Tuple of (decrement_test, increment_test)
        """
        # Decrement test: count matches above (line - 7)
        decrement_line = bookmaker_line - self.config.test_adjustment
        decrement_test = self._count_matches_above_line(h2h_totals, decrement_line)
        
        # Increment test: count matches below (line + 7)
        increment_line = bookmaker_line + self.config.test_adjustment
        increment_test = len(h2h_totals) - self._count_matches_above_line(h2h_totals, increment_line)
        
        logger.debug(f"Test adjustments - Decrement: {decrement_test}, Increment: {increment_test}")
        return decrement_test, increment_test
    
    def _determine_recommendation(self, average_rate: float, matches_above: int, 
                                matches_below: int, decrement_test: int, 
                                increment_test: int) -> PredictionRecommendation:
        """
        Apply ScoreWise prediction rules to determine recommendation.
        
        Args:
            average_rate: Average rate value
            matches_above: Number of matches above bookmaker line
            matches_below: Number of matches below bookmaker line
            decrement_test: Result of decrement test
            increment_test: Result of increment test
            
        Returns:
            PredictionRecommendation
        """
        total_matches = matches_above + matches_below
        
        # Over Bet conditions
        over_conditions = (
            self.config.over_rate_min <= average_rate <= self.config.over_rate_max and
            matches_above >= self.config.min_matches_above_threshold and
            decrement_test >= 1
        )
        
        # Under Bet conditions
        under_conditions = (
            self.config.under_rate_min <= average_rate <= self.config.under_rate_max and
            matches_below >= self.config.min_matches_above_threshold and
            increment_test <= -1
        )
        
        if over_conditions:
            logger.info(f"OVER recommendation - Avg rate: {average_rate}, "
                       f"Matches above: {matches_above}, Decrement test: {decrement_test}")
            return PredictionRecommendation.OVER
        elif under_conditions:
            logger.info(f"UNDER recommendation - Avg rate: {average_rate}, "
                       f"Matches below: {matches_below}, Increment test: {increment_test}")
            return PredictionRecommendation.UNDER
        else:
            logger.info(f"NO BET recommendation - Avg rate: {average_rate}, "
                       f"Conditions not met for OVER or UNDER")
            return PredictionRecommendation.NO_BET
    
    def _analyze_winning_patterns(self, h2h_matches: List[H2HMatchModel], match: MatchModel) -> WinningStreakData:
        """
        Analyze winning patterns for both teams.
        
        Args:
            h2h_matches: List of H2H match models
            match: Current match model
            
        Returns:
            WinningStreakData with analysis results
        """
        home_team = match.home_team
        away_team = match.away_team
        
        # Count H2H wins for each team
        home_team_h2h_wins = 0
        away_team_h2h_wins = 0
        
        for h2h_match in h2h_matches:
            if h2h_match.home_team == home_team:
                if h2h_match.home_score > h2h_match.away_score:
                    home_team_h2h_wins += 1
                else:
                    away_team_h2h_wins += 1
            else:  # h2h_match.home_team == away_team
                if h2h_match.home_score > h2h_match.away_score:
                    away_team_h2h_wins += 1
                else:
                    home_team_h2h_wins += 1
        
        # Analyze recent form (last 3 games) - This would need recent form data
        # For now, we'll use H2H data as a proxy, but this should be enhanced
        # with actual recent form data from the scraper
        home_team_recent_wins = min(home_team_h2h_wins, 3)  # Placeholder
        away_team_recent_wins = min(away_team_h2h_wins, 3)  # Placeholder
        
        # Calculate winning streaks (simplified - would need actual streak data)
        home_team_winning_streak = min(home_team_h2h_wins, 3)  # Placeholder
        away_team_winning_streak = min(away_team_h2h_wins, 3)  # Placeholder
        
        logger.debug(f"Winning pattern analysis - Home: {home_team_h2h_wins}/{len(h2h_matches)} wins, "
                    f"Away: {away_team_h2h_wins}/{len(h2h_matches)} wins")
        
        return WinningStreakData(
            home_team_h2h_wins=home_team_h2h_wins,
            away_team_h2h_wins=away_team_h2h_wins,
            home_team_recent_wins=home_team_recent_wins,
            away_team_recent_wins=away_team_recent_wins,
            home_team_winning_streak=home_team_winning_streak,
            away_team_winning_streak=away_team_winning_streak,
            total_h2h_matches=len(h2h_matches)
        )
    
    def _determine_team_winner(self, winning_streak_data: WinningStreakData) -> TeamWinnerPrediction:
        """
        Determine team winner prediction based on H2H patterns and winning streaks.
        
        Args:
            winning_streak_data: Analysis of winning patterns
            
        Returns:
            TeamWinnerPrediction
        """
        home_wins = winning_streak_data.home_team_h2h_wins
        away_wins = winning_streak_data.away_team_h2h_wins
        home_streak = winning_streak_data.home_team_winning_streak
        away_streak = winning_streak_data.away_team_winning_streak
        
        # Check if home team has strong H2H dominance
        if (home_wins >= self.config.min_h2h_wins_for_winner and 
            home_streak >= self.config.min_winning_streak):
            logger.info(f"HOME_TEAM prediction - H2H wins: {home_wins}, Streak: {home_streak}")
            return TeamWinnerPrediction.HOME_TEAM
        
        # Check if away team has strong H2H dominance
        elif (away_wins >= self.config.min_h2h_wins_for_winner and 
              away_streak >= self.config.min_winning_streak):
            logger.info(f"AWAY_TEAM prediction - H2H wins: {away_wins}, Streak: {away_streak}")
            return TeamWinnerPrediction.AWAY_TEAM
        
        # No clear winner prediction
        else:
            logger.info(f"NO_WINNER_PREDICTION - Home wins: {home_wins}, Away wins: {away_wins}")
            return TeamWinnerPrediction.NO_WINNER_PREDICTION
    
    def _determine_team_winner_confidence(self, winning_streak_data: WinningStreakData) -> ConfidenceLevel:
        """Determine confidence for team winner predictions."""
        home_wins = winning_streak_data.home_team_h2h_wins
        away_wins = winning_streak_data.away_team_h2h_wins
        home_streak = winning_streak_data.home_team_winning_streak
        away_streak = winning_streak_data.away_team_winning_streak
        
        # High confidence: winning streak ≥3 and ≥4 H2H wins
        if ((home_wins >= 4 and home_streak >= 3) or 
            (away_wins >= 4 and away_streak >= 3)):
            return ConfidenceLevel.HIGH
        
        # Medium confidence: ≥4 H2H wins but no strong streak
        elif home_wins >= 4 or away_wins >= 4:
            return ConfidenceLevel.MEDIUM
        
        # Low confidence: weak signals
        else:
            return ConfidenceLevel.LOW
    
    def _determine_enhanced_confidence(self, average_rate: float, matches_above: int, 
                                     matches_below: int, recommendation: PredictionRecommendation,
                                     winning_streak_data: WinningStreakData) -> ConfidenceLevel:
        """
        Determine confidence level with enhanced logic considering winning streaks.
        
        Args:
            average_rate: Average rate value
            matches_above: Number of matches above line
            matches_below: Number of matches below line
            recommendation: Current prediction recommendation
            winning_streak_data: Winning streak analysis
            
        Returns:
            ConfidenceLevel
        """
        # Enhanced confidence logic based on recommendation type
        if recommendation == PredictionRecommendation.OVER:
            return self._determine_over_confidence(average_rate, matches_above, winning_streak_data)
        elif recommendation == PredictionRecommendation.UNDER:
            return self._determine_under_confidence(average_rate, matches_below, winning_streak_data)
        else:  # NO_BET
            return ConfidenceLevel.LOW
    
    def _determine_over_confidence(self, average_rate: float, matches_above: int, 
                                 winning_streak_data: WinningStreakData) -> ConfidenceLevel:
        """Determine confidence for OVER predictions."""
        # High confidence: rate 7-15, winning streak ≥3, and ≥4 H2H wins
        if (7.0 <= average_rate <= 15.0 and 
            winning_streak_data.home_team_winning_streak >= 3 and
            winning_streak_data.home_team_h2h_wins >= 4):
            return ConfidenceLevel.HIGH
        
        # Low confidence: rate 16-20
        elif 16.0 <= average_rate <= 20.0:
            return ConfidenceLevel.LOW
        
        # Medium confidence: other cases
        else:
            return ConfidenceLevel.MEDIUM
    
    def _determine_under_confidence(self, average_rate: float, matches_below: int, 
                                  winning_streak_data: WinningStreakData) -> ConfidenceLevel:
        """Determine confidence for UNDER predictions."""
        # High confidence: rate -7 to -15, winning streak ≥3, and ≥4 H2H wins
        if (-15.0 <= average_rate <= -7.0 and 
            winning_streak_data.away_team_winning_streak >= 3 and
            winning_streak_data.away_team_h2h_wins >= 4):
            return ConfidenceLevel.HIGH
        
        # Low confidence: rate -16 to -20
        elif -20.0 <= average_rate <= -16.0:
            return ConfidenceLevel.LOW
        
        # Medium confidence: other cases
        else:
            return ConfidenceLevel.MEDIUM 