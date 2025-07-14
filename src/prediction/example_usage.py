#!/usr/bin/env python3
"""
Example usage of the ScoreWise prediction algorithm.
"""

import logging
from src.models import MatchModel, OddsModel, H2HMatchModel
from src.prediction.predictions.prediction_service import PredictionService

logger = logging.getLogger(__name__)

def create_example_match() -> MatchModel:
    """Create an example match with H2H data and odds for testing."""
    
    # Create H2H matches
    h2h_matches = [
        H2HMatchModel(
            match_id="h2h_1",
            date="2024-01-15",
            home_team="Team A",
            away_team="Team B",
            home_score=85,
            away_score=92,
            competition="League"
        ),
        H2HMatchModel(
            match_id="h2h_2",
            date="2024-02-10",
            home_team="Team B",
            away_team="Team A",
            home_score=88,
            away_score=95,
            competition="League"
        ),
        H2HMatchModel(
            match_id="h2h_3",
            date="2024-03-05",
            home_team="Team A",
            away_team="Team B",
            home_score=91,
            away_score=89,
            competition="League"
        ),
        H2HMatchModel(
            match_id="h2h_4",
            date="2024-04-12",
            home_team="Team B",
            away_team="Team A",
            home_score=94,
            away_score=87,
            competition="League"
        ),
        H2HMatchModel(
            match_id="h2h_5",
            date="2024-05-20",
            home_team="Team A",
            away_team="Team B",
            home_score=96,
            away_score=93,
            competition="League"
        ),
        H2HMatchModel(
            match_id="h2h_6",
            date="2024-06-08",
            home_team="Team B",
            away_team="Team A",
            home_score=90,
            away_score=98,
            competition="League"
        )
    ]
    
    # Create odds data
    odds = OddsModel(
        match_id="match_123",
        home_odds=1.85,
        away_odds=1.95,
        over_odds=1.87,
        under_odds=1.79,
        match_total=176.5  # Bookmaker line
    )
    
    # Create match
    match = MatchModel(
        match_id="match_123",
        country="Example Country",
        league="Example League",
        home_team="Team A",
        away_team="Team B",
        date="2024-07-15",
        time="20:00",
        odds=odds,
        h2h_matches=h2h_matches
    )
    
    return match


def demonstrate_prediction():
    """Demonstrate the ScoreWise prediction algorithm."""
    
    logger.info("=== ScoreWise Prediction Demo ===")
    
    # Create example match
    match = create_example_match()
    logger.info(f"Created example match: {match.home_team} vs {match.away_team}")
    logger.info(f"Bookmaker line: {match.odds.match_total}")
    logger.info(f"H2H matches: {len(match.h2h_matches)}")
    
    # Create prediction service
    service = PredictionService()
    
    # Generate prediction
    result = service.generate_prediction(match)
    
    if result.success and result.prediction:
        prediction = result.prediction
        logger.info("=== Prediction Result ===")
        logger.info(f"Recommendation: {prediction.recommendation.value}")
        logger.info(f"Confidence: {prediction.confidence.value}")
        logger.info(f"Average Rate: {prediction.average_rate:.2f}")
        logger.info(f"Matches Above Line: {prediction.matches_above_line}")
        logger.info(f"Matches Below Line: {prediction.matches_below_line}")
        logger.info(f"Decrement Test: {prediction.decrement_test}")
        logger.info(f"Increment Test: {prediction.increment_test}")
        logger.info(f"H2H Totals: {prediction.h2h_totals}")
        logger.info(f"Rate Values: {[f'{r:.2f}' for r in prediction.rate_values]}")
        
        # Show calculation details
        logger.info("=== Calculation Details ===")
        for key, value in prediction.calculation_details.items():
            logger.info(f"{key}: {value}")
            
    else:
        logger.error("Prediction failed:")
        logger.error(f"Error: {result.error_message}")
        if result.validation_errors:
            for error in result.validation_errors:
                logger.error(f"Validation Error: {error}")


def demonstrate_batch_predictions():
    """Demonstrate batch prediction processing."""
    
    logger.info("=== Batch Prediction Demo ===")
    
    # Create multiple example matches
    matches = []
    for i in range(3):
        match = create_example_match()
        match.match_id = f"match_{i+1}"
        match.odds.match_total = 175.0 + i  # Different bookmaker lines
        matches.append(match)
    
    # Create prediction service
    service = PredictionService()
    
    # Generate batch predictions
    results = service.batch_predictions(matches)
    
    # Show results
    successful = 0
    for i, result in enumerate(results):
        if result.success:
            successful += 1
            prediction = result.prediction
            logger.info(f"Match {i+1}: {prediction.recommendation.value} "
                       f"({prediction.confidence.value})")
        else:
            logger.warning(f"Match {i+1}: Failed - {result.error_message}")
    
    logger.info(f"Batch complete: {successful}/{len(matches)} successful")


def demonstrate_service_features():
    """Demonstrate additional service features."""
    
    logger.info("=== Service Features Demo ===")
    
    # Create service
    service = PredictionService()
    
    # Create and predict match
    match = create_example_match()
    result = service.generate_prediction(match)
    
    if result.success:
        # Get prediction summary
        summary = service.get_prediction_summary(match.match_id)
        logger.info("=== Prediction Summary ===")
        for key, value in summary.items():
            logger.info(f"{key}: {value}")
        
        # Get service stats
        stats = service.get_service_stats()
        logger.info("=== Service Stats ===")
        for key, value in stats.items():
            logger.info(f"{key}: {value}")


if __name__ == "__main__":
    """Run the demonstration."""
    
    try:
        # Demonstrate basic prediction
        demonstrate_prediction()
        logger.info("\n" + "="*50 + "\n")
        
        # Demonstrate batch predictions
        demonstrate_batch_predictions()
        logger.info("\n" + "="*50 + "\n")
        
        # Demonstrate service features
        demonstrate_service_features()
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise 