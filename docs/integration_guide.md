# Flashscore Scraper Integration Guide

## URL Structure

### URL Format

The scraper uses the following URL structure for Flashscore matches:

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

### 1. Basic Usage (Programmatic)

```python
from src.scraper import FlashscoreScraper

# Initialize scraper
scraper = FlashscoreScraper()

# Scrape match data
match = scraper.scrape_match(match_id)

if match:
    print(f"Home: {match.home_team}")
    print(f"Away: {match.away_team}")
    if match.odds:
        print(f"Line: {match.odds.match_total}")
    if match.h2h_matches:
        print(f"H2H games: {len(match.h2h_matches)}")
```

### 2. Integration with Loaders

All loader classes accept an optional `team_info` parameter for generating canonical URLs:

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

### 3. Consuming Output Files

The primary integration method is reading the JSON output files:

```python
import json
from pathlib import Path

output_dir = Path("output")
date_dirs = sorted(output_dir.iterdir())
latest = date_dirs[-1] if date_dirs else None

if latest:
    match_files = sorted(latest.glob("matches_*.json"))
    for match_file in match_files:
        with open(match_file) as f:
            data = json.load(f)
        for match in data.get("matches", []):
            # Process each match record
            process_match(match)
```

## Integration Patterns

### 1. Library Usage

Use the scraper as a Python library in your own scripts:

```python
from src.scraper import FlashscoreScraper
from src.models import MatchModel

scraper = FlashscoreScraper()

# Scrape today's matches
results = scraper.scrape_day("Today")

for match in results:
    if match.odds and match.h2h_matches:
        # Do something with the match data
        print(f"{match.home_team} vs {match.away_team}")
        print(f"  Line: {match.odds.match_total}")
```

### 2. CLI Output Consumption

Run the scraper via CLI and read the output files:

```bash
# Run the scraper
fss --cli

# Then read the output in your downstream tool
# Output is in: output/<date>/matches_<date>.json
```

### 3. Scheduled Scraping

Set up recurring scraping sessions through the CLI "Scheduled Matches" menu, then consume the output files on a schedule that matches your scraping interval.

## Data Requirements

### Match Data Structure

Your `MatchModel` provides:

```python
match = MatchModel(
    match_id="unique_id",
    home_team="Team A",
    away_team="Team B",
    date="12.07.2025",
    time="12:00",
    country="USA",
    league="NBA",
    odds=OddsModel(
        match_total=176.5,
        over_odds=1.85,
        under_odds=1.95,
        home_odds=1.75,
        away_odds=2.10
    ),
    h2h_matches=[
        H2HMatchModel(
            home_score=85,
            away_score=92,
            home_team="Team A",
            away_team="Team B",
            date="01.06.2025",
            competition="NBA"
        ),
    ]
)
```

### Validation Checklist

Before processing scraped data, ensure:

- Match has a valid `match_id`
- All H2H matches have valid scores (>= 0)
- Match has odds data with `match_total` when odds are present
- Data is recent and relevant for your use case

## Error Handling

### Common Errors

```python
# Insufficient H2H data
if len(match.h2h_matches) < 6:
    print("Need at least 6 H2H matches for reliable analysis")

# Missing odds data
if not match.odds or match.odds.match_total is None:
    print("Missing bookmaker line")

# Invalid scores
for h2h in match.h2h_matches:
    if h2h.home_score < 0 or h2h.away_score < 0:
        print("Invalid scores in H2H data")
```

## Support

For issues or questions:
1. Check the documentation in `docs/`
2. Review the output schema in `docs/index.md`
3. Check logs in `output/logs/` for detailed error information
4. Validate input data requirements against the schema
