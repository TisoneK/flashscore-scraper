# Results Update Feature Guide

## Overview

The Results Update feature allows you to update existing match data with final scores from Flashscore. This feature reads a JSON file containing match data, fetches the final scores for each match, and updates the JSON file with the results.

## Features

- **Read JSON Files**: Load existing match data from JSON files
- **Fetch Final Scores**: Extract home and away scores from match summary pages
- **Update Match Data**: Add `home_score` and `away_score` fields to matches
- **Validation**: Verify score data integrity and format
- **Progress Tracking**: Real-time status updates during processing
- **Error Handling**: Graceful handling of network issues and missing data

## Usage

### Command Line Interface

```bash
# Basic usage - update results from a JSON file
fss --results-update output/json/matches_170725.json

# Specify custom output file
fss --results-update matches.json --output results_updated.json

# With debug output
fss --results-update matches.json --debug
```

### Programmatic Usage

```python
from src.data.processor.results_update_processor import ResultsUpdateProcessor

# Create processor
processor = ResultsUpdateProcessor()

# Define status callback
def status_callback(message: str):
    print(f"Status: {message}")

# Process JSON file
success = processor.process_json_file(
    "input_matches.json", 
    "output_matches.json", 
    status_callback
)

if success:
    print("Results update completed successfully!")
else:
    print("Results update failed!")
```

## Input JSON Format

The feature expects JSON files with the following structure:

```json
{
  "matches": [
    {
      "match_id": "reYcCrUi",
      "country": "CANADA",
      "league": "CEBL",
      "home_team": "Niagara River Lions",
      "away_team": "Brampton Honey Badgers",
      "date": "17.07.2025",
      "time": "02:00",
      "created_at": "2025-07-16 09:52:19",
      "status": "complete",
      "odds": {...},
      "h2h_matches": [...]
    }
  ]
}
```

## Output JSON Format

After processing, the JSON file will be updated with score information:

```json
{
  "matches": [
    {
      "match_id": "reYcCrUi",
      "country": "CANADA",
      "league": "CEBL",
      "home_team": "Niagara River Lions",
      "away_team": "Brampton Honey Badgers",
      "date": "17.07.2025",
      "time": "02:00",
      "created_at": "2025-07-16 09:52:19",
      "status": "complete",
      "odds": {...},
      "h2h_matches": [...],
      "home_score": 95,
      "away_score": 87,
      "results_updated_at": "2025-07-17 14:30:00"
    }
  ],
  "processing_info": {
    "total_matches": 1,
    "successful_updates": 1,
    "failed_updates": 0,
    "processed_at": "2025-07-17 14:30:00"
  }
}
```

## Architecture

### Components

1. **ResultsDataLoader** (`src/data/loader/results_data_loader.py`)
   - Loads match summary pages
   - Extracts score elements using Selenium
   - Handles network resilience and retries

2. **ResultsDataExtractor** (`src/data/extractor/results_data_extractor.py`)
   - Extracts final scores from elements
   - Parses score text into separate home/away scores
   - Validates data format

3. **ResultsDataVerifier** (`src/data/verifier/results_data_verifier.py`)
   - Validates score integrity
   - Checks for reasonable basketball scores
   - Handles edge cases

4. **ResultsUpdateProcessor** (`src/data/processor/results_update_processor.py`)
   - Main orchestrator for the process
   - Handles JSON file reading/writing
   - Manages batch processing and error handling

### Selectors

The feature uses the following CSS selectors to extract score data:

```json
{
  "results": {
    "final_score": "div.duelParticipant__score div.detailScore__wrapper",
    "match_status": "div.duelParticipant__score div.detailScore__status span.fixedHeaderDuel__detailStatus",
    "home_score": "div.duelParticipant__score div.detailScore__wrapper span:first-child",
    "away_score": "div.duelParticipant__score div.detailScore__wrapper span:last-child"
  }
}
```

## Error Handling

The feature includes comprehensive error handling:

- **Network Issues**: Automatic retry logic with exponential backoff
- **Missing Data**: Graceful handling when scores are not available
- **Invalid Scores**: Validation of score format and reasonableness
- **Partial Failures**: Continue processing other matches if one fails

## Validation Rules

### Score Validation

- Scores must be integers
- Scores cannot be negative
- Scores must be reasonable for basketball (0-200 range)
- At least one team must have scored in finished games

### Status Validation

Valid match statuses:
- `scheduled`
- `live`
- `finished`
- `cancelled`
- `postponed`

## Performance Considerations

- **Batch Processing**: Processes matches sequentially to avoid overwhelming the server
- **Network Resilience**: Built-in retry logic and timeout handling
- **Memory Management**: Efficient handling of large JSON files
- **Progress Tracking**: Real-time status updates for long-running operations

## Testing

Run the test script to verify functionality:

```bash
python test_results_update.py
```

This will:
1. Create a test JSON file
2. Test the results update processor
3. Test the CLI command
4. Display results and statistics

## Troubleshooting

### Common Issues

1. **No scores found**: Match may not have finished or scores not available
2. **Network errors**: Check internet connection and try again
3. **Invalid JSON**: Ensure input file has correct format
4. **Driver issues**: Ensure Chrome/ChromeDriver is properly installed

### Debug Mode

Enable debug output for detailed logging:

```bash
fss --results-update matches.json --debug
```

## Future Enhancements

- **Batch Size Configuration**: Configurable batch sizes for processing
- **Parallel Processing**: Multi-threaded processing for faster updates
- **Score History**: Track score changes over time
- **Advanced Filtering**: Filter matches by date, league, or status
- **API Integration**: Direct API calls for faster data retrieval 