# Flashscore Scraper Integration Guide

## URL Structure

### New URL Format

The scraper now uses a new URL structure for Flashscore matches:

```
https://www.flashscore.co.ke/match/basketball/{home_slug}-{home_id}/{away_slug}-{away_id}/{path}/?mid={mid}
```

Where:
- `{home_slug}`: Home team slug (e.g., 'instituto-de-cordoba')
- `{home_id}`: Home team short ID (e.g., 'rJPlbMMq')
- `{away_slug}`: Away team slug (e.g., 'olimpico')
- `{away_id}`: Away team short ID (e.g., 'ERbTiFhJ')
- `{path}`: The type of page (e.g., 'summary', 'h2h/overall')
- `{mid}`: The match ID (e.g., 'raxc7DVh')

### URL Builder Usage

The `UrlBuilder` class provides a convenient way to generate these URLs:

```python
from src.core.url_builder import UrlBuilder

# Full URL with all parameters
url = UrlBuilder.summary(
    mid="raxc7DVh",
    home_slug="instituto-de-cordoba",
    home_id="rJPlbMMq",
    away_slug="olimpico",
    away_id="ERbTiFhJ"
)

# Minimal URL (only match ID)
minimal_url = UrlBuilder.from_mid("raxc7DVh")

# Generate all URLs for a match
all_urls = UrlBuilder.get_all_urls(
    mid="raxc7DVh",
    home_slug="instituto-de-cordoba",
    home_id="rJPlbMMq",
    away_slug="olimpico",
    away_id="ERbTiFhJ"
)
```

## Quick Start

### 1. Basic Usage

```python
from src.prediction import PredictionService
from src.models import MatchModel

# Create prediction service
service = PredictionService()

# Generate prediction for a match
result = service.generate_prediction(match)

if result.success:
    prediction = result.prediction
    print(f"Recommendation: {prediction.recommendation.value}")
    print(f"Confidence: {prediction.confidence.value}")
    print(f"Average Rate: {prediction.average_rate:.2f}")
```

### 2. Integration with Loaders

All loader classes now accept an optional `team_info` parameter for generating canonical URLs:

```python
from src.data.loader.match_data_loader import MatchDataLoader

# Initialize loader with driver
loader = MatchDataLoader(driver)

# Load match with team info for canonical URL
match_loaded = loader.load_match(
    match_id="raxc7DVh",
    team_info={
        'home_slug': 'instituto-de-cordoba',
        'home_id': 'rJPlbMMq',
        'away_slug': 'olimpico',
        'away_id': 'ERbTiFhJ'
    }
)

# Fallback to minimal URL if team info is not available
match_loaded_minimal = loader.load_match(match_id="raxc7DVh")
```

### 3. Integration with Existing Scraper

```python
from src.prediction import PredictionService
from src.scraper import FlashscoreScraper

# Initialize scraper and prediction service
scraper = FlashscoreScraper()
prediction_service = PredictionService()

# Scrape match data
match = scraper.scrape_match(match_id)

# Generate prediction
if match and match.h2h_matches and match.odds:
    result = prediction_service.generate_prediction(match)
    if result.success:
        print(f"Prediction: {result.prediction.get_summary()}")
```

## Integration Points

### 1. API Integration

Add prediction endpoints to your existing API:

```python
# In src/api/api.py
from src.prediction import PredictionService

prediction_service = PredictionService()

@app.route('/api/predictions/<match_id>', methods=['GET'])
def get_prediction(match_id):
    """Get prediction for a specific match."""
    match = get_match_from_database(match_id)
    if not match:
        return jsonify({'error': 'Match not found'}), 404
    
    result = prediction_service.generate_prediction(match)
    return jsonify(result.to_dict())

@app.route('/api/predictions/batch', methods=['POST'])
def batch_predictions():
    """Generate predictions for multiple matches."""
    match_ids = request.json.get('match_ids', [])
    matches = [get_match_from_database(mid) for mid in match_ids]
    matches = [m for m in matches if m is not None]
    
    results = prediction_service.batch_predictions(matches)
    return jsonify([r.to_dict() for r in results])
```

### 2. CLI Integration

Add prediction commands to your CLI:

```python
# In src/cli/cli_manager.py
from src.prediction import PredictionService

def predict_match(match_id: str):
    """Generate prediction for a match."""
    match = get_match(match_id)
    if not match:
        print(f"Match {match_id} not found")
        return
    
    service = PredictionService()
    result = service.generate_prediction(match)
    
    if result.success:
        pred = result.prediction
        print(f"Prediction: {pred.recommendation.value}")
        print(f"Confidence: {pred.confidence.value}")
        print(f"Average Rate: {pred.average_rate:.2f}")
    else:
        print(f"Prediction failed: {result.error_message}")

def predict_batch(match_ids: List[str]):
    """Generate predictions for multiple matches."""
    service = PredictionService()
    matches = [get_match(mid) for mid in match_ids]
    matches = [m for m in matches if m is not None]
    
    results = service.batch_predictions(matches)
    successful = sum(1 for r in results if r.success)
    
    print(f"Generated {successful}/{len(results)} predictions")
    for i, result in enumerate(results):
        if result.success:
            pred = result.prediction
            print(f"Match {i+1}: {pred.recommendation.value} ({pred.confidence.value})")
```

### 3. UI Integration

Add prediction display to your UI:

```python
# In src/ui/components/results_view.py
from src.prediction import PredictionService

class ResultsView:
    def __init__(self):
        self.prediction_service = PredictionService()
    
    def display_prediction(self, match: MatchModel):
        """Display prediction for a match."""
        result = self.prediction_service.generate_prediction(match)
        
        if result.success:
            pred = result.prediction
            # Display prediction in UI
            self.show_prediction_card(pred)
        else:
            # Show error message
            self.show_error_message(result.error_message)
    
    def show_prediction_card(self, prediction: ScoreWisePrediction):
        """Display prediction in a card format."""
        # Implementation for UI display
        pass
```

## Configuration

### 1. Custom Algorithm Parameters

```python
from src.prediction import ScoreWiseConfig, PredictionService

# Custom configuration
config = ScoreWiseConfig(
    min_h2h_matches=8,        # Require more H2H matches
    over_rate_min=10.0,       # Higher threshold for OVER
    over_rate_max=25.0,       # Wider range
    test_adjustment=5.0       # Smaller test adjustment
)

service = PredictionService(config)
```

### 2. Environment Configuration

Add to your config files:

```python
# In src/config.py
PREDICTION_CONFIG = {
    'min_h2h_matches': 6,
    'over_rate_min': 7.0,
    'over_rate_max': 20.0,
    'under_rate_min': -20.0,
    'under_rate_max': -7.0,
    'test_adjustment': 7.0,
    'min_matches_above_threshold': 4
}
```

## Data Requirements

### 1. Match Data Structure

Your `MatchModel` must have:

```python
match = MatchModel(
    match_id="unique_id",
    # ... other fields ...
    odds=OddsModel(
        match_total=176.5,  # Required: Bookmaker line
        # ... other odds fields ...
    ),
    h2h_matches=[
        H2HMatchModel(
            home_score=85,   # Required: Valid scores
            away_score=92,   # Required: Valid scores
            # ... other fields ...
        ),
        # ... minimum 6 H2H matches ...
    ]
)
```

### 2. Validation Checklist

Before generating predictions, ensure:

- ✅ Match has at least 6 H2H matches
- ✅ All H2H matches have valid scores (≥ 0)
- ✅ Match has odds data with `match_total`
- ✅ H2H matches are for the same teams
- ✅ Data is recent and relevant

## Error Handling

### 1. Common Errors

```python
# Insufficient H2H data
if len(match.h2h_matches) < 6:
    print("Need at least 6 H2H matches")

# Missing odds data
if not match.odds or match.odds.match_total is None:
    print("Missing bookmaker line")

# Invalid scores
for h2h in match.h2h_matches:
    if h2h.home_score < 0 or h2h.away_score < 0:
        print("Invalid scores in H2H data")
```

### 2. Result Validation

```python
result = service.generate_prediction(match)

if result.success:
    prediction = result.prediction
    # Use prediction
else:
    # Handle error
    print(f"Error: {result.error_message}")
    for error in result.validation_errors:
        print(f"Validation: {error}")
```

## Performance Optimization

### 1. Batch Processing

```python
# Process multiple matches efficiently
matches = get_matches_with_predictions()
results = service.batch_predictions(matches)

# Filter successful results
successful_predictions = [
    r.prediction for r in results 
    if r.success and r.prediction
]
```

### 2. Caching Predictions

```python
# Store predictions for reuse
prediction_cache = {}

def get_cached_prediction(match_id: str):
    if match_id in prediction_cache:
        return prediction_cache[match_id]
    
    match = get_match(match_id)
    result = service.generate_prediction(match)
    
    if result.success:
        prediction_cache[match_id] = result.prediction
    
    return result.prediction
```

## Testing

### 1. Unit Tests

```python
# test_prediction.py
import unittest
from src.prediction import PredictionService, ScoreWiseCalculator
from src.models import MatchModel, H2HMatchModel, OddsModel

class TestPrediction(unittest.TestCase):
    def setUp(self):
        self.service = PredictionService()
    
    def test_basic_prediction(self):
        match = self.create_test_match()
        result = self.service.generate_prediction(match)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.prediction)
        self.assertIn(result.prediction.recommendation.value, ['OVER', 'UNDER', 'NO_BET'])
    
    def create_test_match(self):
        # Create test match with valid data
        pass
```

### 2. Integration Tests

```python
# test_integration.py
def test_scraper_integration():
    scraper = FlashscoreScraper()
    prediction_service = PredictionService()
    
    # Scrape real data
    match = scraper.scrape_match("test_match_id")
    
    # Generate prediction
    result = prediction_service.generate_prediction(match)
    
    # Validate result
    assert result.success or result.error_message
```

## Monitoring and Analytics

### 1. Service Statistics

```python
# Get service performance metrics
stats = service.get_service_stats()
print(f"Total predictions: {stats['total_predictions']}")
print(f"Recommendation distribution: {stats['recommendation_distribution']}")
```

### 2. Prediction History

```python
# Get prediction history for a match
history = service.get_prediction_history(match_id)
for pred in history:
    print(f"{pred.created_at}: {pred.recommendation.value}")
```

## Troubleshooting

### 1. Common Issues

**Issue**: "No H2H matches available"
- **Solution**: Ensure match has sufficient H2H data

**Issue**: "No bookmaker line available"
- **Solution**: Check that odds data includes `match_total`

**Issue**: "Invalid scores in H2H data"
- **Solution**: Validate H2H match scores are non-negative

### 2. Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging for troubleshooting
service = PredictionService()
result = service.generate_prediction(match)
```

## Next Steps

1. **Database Integration**: Store predictions in database
2. **API Endpoints**: Add RESTful API endpoints
3. **UI Components**: Create prediction display components
4. **Performance Monitoring**: Add metrics and monitoring
5. **Advanced Features**: Implement additional prediction algorithms

## Support

For issues or questions:
1. Check the algorithm documentation in `docs/index.md`
2. Review the example usage in `src/prediction/example_usage.py`
3. Test with the provided example data
4. Validate input data requirements 