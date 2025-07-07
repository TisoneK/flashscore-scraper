"""
ScoreWise Calculator Implementation

This module implements the core ScoreWise prediction algorithm as documented in docs/index.md.
The algorithm analyzes historical head-to-head (H2H) matchup data and bookmaker alternatives
to provide recommendations for Over/Under bets.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from src.models import MatchModel, H2HMatchModel, OddsModel
from ..predictions.prediction_models import (
    ScoreWisePrediction, 
    PredictionResult, 
    PredictionRecommendation, 
    ConfidenceLevel
)

logger = logging.getLogger(__name__)


@dataclass
class ScoreWiseConfig:
    """Configuration for ScoreWise calculator."""
    min_h2h_matches: int = 6
    over_rate_min: float = 7.0
    over_rate_max: float = 20.0
    under_rate_min: float = -20.0
    under_rate_max: float = -7.0
    test_adjustment: float = 7.0
    min_matches_above_threshold: int = 4


class ScoreWiseCalculator:
    """
    Implements the ScoreWise prediction algorithm.
    
    Algorithm Steps (from docs/index.md):
    1. Data Collection: Gather H2H data for at least 6 previous matchups
    2. Statistical Analysis: Calculate rate values and averages
    3. Test Adjustments: Apply ±7 point adjustments
    4. Prediction Rules: Apply ScoreWise prediction rules
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
            bookmaker_line = match.odds.match_total
            
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
            
            # Determine recommendation
            recommendation = self._determine_recommendation(
                average_rate, matches_above, matches_below, 
                decrement_test, increment_test
            )
            
            # Determine confidence level
            confidence = self._determine_confidence(
                average_rate, matches_above, matches_below
            )
            
            # Create prediction
            prediction = ScoreWisePrediction(
                match_id=match.match_id,
                recommendation=recommendation,
                confidence=confidence,
                average_rate=average_rate,
                matches_above_line=matches_above,
                matches_below_line=matches_below,
                total_matches=len(h2h_totals),
                decrement_test=decrement_test,
                increment_test=increment_test,
                bookmaker_line=bookmaker_line,
                h2h_totals=h2h_totals,
                rate_values=rate_values,
                calculation_details={
                    'config': self.config.__dict__,
                    'algorithm_version': '1.0.0'
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
    
    def _determine_confidence(self, average_rate: float, matches_above: int, 
                            matches_below: int) -> ConfidenceLevel:
        """
        Determine confidence level based on prediction strength.
        
        Args:
            average_rate: Average rate value
            matches_above: Number of matches above line
            matches_below: Number of matches below line
            
        Returns:
            ConfidenceLevel
        """
        total_matches = matches_above + matches_below
        
        # High confidence: strong rate and clear majority
        if (abs(average_rate) >= 15 and 
            (matches_above >= 5 or matches_below >= 5)):
            return ConfidenceLevel.HIGH
        
        # Medium confidence: moderate rate and majority
        elif (abs(average_rate) >= 10 and 
              (matches_above >= 4 or matches_below >= 4)):
            return ConfidenceLevel.MEDIUM
        
        # Low confidence: weak signals
        else:
            return ConfidenceLevel.LOW 