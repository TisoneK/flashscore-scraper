"""
Prediction Service for ScoreWise Algorithm

This module provides high-level services for managing ScoreWise predictions.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.models import MatchModel
from .prediction_models import ScoreWisePrediction, PredictionResult
from ..calculator.scorewise_calculator import ScoreWiseCalculator, ScoreWiseConfig

logger = logging.getLogger(__name__)


class PredictionService:
    """
    High-level service for managing ScoreWise predictions.
    
    This service provides methods for generating predictions, batch processing,
    and managing prediction history.
    """
    
    def __init__(self, config: Optional[ScoreWiseConfig] = None):
        """Initialize the prediction service."""
        self.calculator = ScoreWiseCalculator(config)
        self.prediction_history: Dict[str, List[ScoreWisePrediction]] = {}
        logger.info("Prediction Service initialized")
    
    def generate_prediction(self, match: MatchModel) -> PredictionResult:
        """
        Generate ScoreWise prediction for a single match.
        
        Args:
            match: MatchModel containing H2H data and odds
            
        Returns:
            PredictionResult with prediction or error details
        """
        logger.info(f"Generating prediction for match {match.match_id}")
        
        # Validate prediction requirements
        if not self.validate_prediction_requirements(match):
            return PredictionResult(
                success=False,
                error_message="Match does not meet prediction requirements",
                validation_errors=["Insufficient data for prediction"]
            )
        
        # Calculate prediction
        result = self.calculator.calculate_prediction(match)
        
        # Store prediction in history if successful
        if result.success and result.prediction:
            self._store_prediction(result.prediction)
        
        return result
    
    def batch_predictions(self, matches: List[MatchModel]) -> List[PredictionResult]:
        """
        Generate predictions for multiple matches.
        
        Args:
            matches: List of MatchModel instances
            
        Returns:
            List of PredictionResult instances
        """
        logger.info(f"Generating batch predictions for {len(matches)} matches")
        
        results = []
        for match in matches:
            result = self.generate_prediction(match)
            results.append(result)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch prediction complete: {successful}/{len(matches)} successful")
        
        return results
    
    def get_prediction_history(self, match_id: str) -> List[ScoreWisePrediction]:
        """
        Get prediction history for a specific match.
        
        Args:
            match_id: ID of the match
            
        Returns:
            List of ScoreWisePrediction instances
        """
        return self.prediction_history.get(match_id, [])
    
    def get_latest_prediction(self, match_id: str) -> Optional[ScoreWisePrediction]:
        """
        Get the latest prediction for a specific match.
        
        Args:
            match_id: ID of the match
            
        Returns:
            Latest ScoreWisePrediction or None
        """
        history = self.get_prediction_history(match_id)
        return history[-1] if history else None
    
    def validate_prediction_requirements(self, match: MatchModel) -> bool:
        """
        Check if a match meets the requirements for prediction.
        
        Args:
            match: MatchModel to validate
            
        Returns:
            True if match meets requirements, False otherwise
        """
        # Check for H2H data
        if not match.h2h_matches or len(match.h2h_matches) < 6:
            logger.debug(f"Match {match.match_id}: Insufficient H2H data")
            return False
        
        # Check for odds data
        if not match.odds or match.odds.match_total is None:
            logger.debug(f"Match {match.match_id}: Missing odds data")
            return False
        
        # Check for valid scores in H2H matches
        for h2h_match in match.h2h_matches:
            if h2h_match.home_score < 0 or h2h_match.away_score < 0:
                logger.debug(f"Match {match.match_id}: Invalid scores in H2H data")
                return False
        
        logger.debug(f"Match {match.match_id}: Meets prediction requirements")
        return True
    
    def get_prediction_summary(self, match_id: str) -> Dict[str, Any]:
        """
        Get a summary of predictions for a match.
        
        Args:
            match_id: ID of the match
            
        Returns:
            Dictionary with prediction summary
        """
        history = self.get_prediction_history(match_id)
        
        if not history:
            return {
                'match_id': match_id,
                'has_predictions': False,
                'total_predictions': 0
            }
        
        latest = history[-1]
        
        # Count recommendations
        recommendations = {}
        for pred in history:
            rec = pred.recommendation.value
            recommendations[rec] = recommendations.get(rec, 0) + 1
        
        return {
            'match_id': match_id,
            'has_predictions': True,
            'total_predictions': len(history),
            'latest_prediction': latest.to_dict(),
            'recommendation_counts': recommendations,
            'latest_recommendation': latest.recommendation.value,
            'latest_confidence': latest.confidence.value,
            'latest_average_rate': latest.average_rate
        }
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the prediction service.
        
        Returns:
            Dictionary with service statistics
        """
        total_predictions = sum(len(predictions) for predictions in self.prediction_history.values())
        total_matches = len(self.prediction_history)
        
        # Count recommendations across all predictions
        all_recommendations = {}
        for predictions in self.prediction_history.values():
            for pred in predictions:
                rec = pred.recommendation.value
                all_recommendations[rec] = all_recommendations.get(rec, 0) + 1
        
        return {
            'total_predictions': total_predictions,
            'total_matches': total_matches,
            'recommendation_distribution': all_recommendations,
            'service_uptime': datetime.now().isoformat()
        }
    
    def _store_prediction(self, prediction: ScoreWisePrediction) -> None:
        """
        Store a prediction in the history.
        
        Args:
            prediction: ScoreWisePrediction to store
        """
        match_id = prediction.match_id
        if match_id not in self.prediction_history:
            self.prediction_history[match_id] = []
        
        self.prediction_history[match_id].append(prediction)
        logger.debug(f"Stored prediction for match {match_id}")
    
    def clear_history(self, match_id: Optional[str] = None) -> None:
        """
        Clear prediction history.
        
        Args:
            match_id: Specific match ID to clear, or None to clear all
        """
        if match_id:
            if match_id in self.prediction_history:
                del self.prediction_history[match_id]
                logger.info(f"Cleared prediction history for match {match_id}")
        else:
            self.prediction_history.clear()
            logger.info("Cleared all prediction history") 