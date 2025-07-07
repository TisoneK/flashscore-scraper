"""
ScoreWise Prediction Module

This module implements the ScoreWise prediction algorithm for basketball score prediction.
It analyzes historical head-to-head (H2H) matchup data and bookmaker alternatives 
to provide recommendations for Over/Under bets.

Based on the ScoreWise algorithm documented in docs/index.md
"""

from .predictions.prediction_models import ScoreWisePrediction, PredictionResult
from .predictions.prediction_service import PredictionService
from .calculator.scorewise_calculator import ScoreWiseCalculator, ScoreWiseConfig

__all__ = [
    'ScoreWisePrediction',
    'PredictionResult', 
    'PredictionService',
    'ScoreWiseCalculator',
    'ScoreWiseConfig'
]

__version__ = "1.0.0"
__author__ = "ScoreWise Implementation" 