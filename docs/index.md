# Flashscore Scraper — Documentation Index

> **Note:** The Flashscore Basketball Scraper is a CLI-only tool focused on structured match data extraction. All prediction/ScoreWise functionality has been moved to a separate repository.

---

## Scraper Output Schema

The scraper produces structured JSON files under `output/<date>/matches_<date>.json`. Each match record contains:

### Match Metadata
| Field | Type | Description |
|-------|------|-------------|
| `match_id` | `str` | Unique Flashscore match identifier |
| `home_team` | `str` | Home team name |
| `away_team` | `str` | Away team name |
| `date` | `str` | Match date (DD.MM.YYYY) |
| `time` | `str` | Match time (HH:MM) |
| `league` | `str` | League/tournament name |
| `country` | `str` | Country |
| `status` | `str` | Match status (scheduled, in-progress, completed, etc.) |

### Odds Data
| Field | Type | Description |
|-------|------|-------------|
| `match_total` | `float` | Bookmaker over/under line |
| `over_odds` | `float` | Over odds value |
| `under_odds` | `float` | Under odds value |
| `home_odds` | `float` | Home team moneyline odds |
| `away_odds` | `float` | Away team moneyline odds |

### H2H (Head-to-Head) History
| Field | Type | Description |
|-------|------|-------------|
| `date` | `str` | H2H match date |
| `home_team` | `str` | Home team in H2H match |
| `away_team` | `str` | Away team in H2H match |
| `home_score` | `int` | Home team score |
| `away_score` | `int` | Away team score |
| `competition` | `str` | Competition/league name |

### Results (Final Scores)
| Field | Type | Description |
|-------|------|-------------|
| `home_score` | `int` | Final home team score |
| `away_score` | `int` | Final away team score |
| `match_status` | `str` | Final match status |

---

## Data Consumption

External tools (e.g., ScoreWise) consume scraper output by reading the JSON files directly. No API server is required — the scraper writes structured data to disk, and downstream systems read from there.

### Example: Reading match data programmatically

```python
import json
from pathlib import Path

# Load the latest match output
output_dir = Path("output")
date_dirs = sorted(output_dir.iterdir())
latest = date_dirs[-1] if date_dirs else None

if latest:
    match_files = sorted(latest.glob("matches_*.json"))
    if match_files:
        with open(match_files[-1]) as f:
            data = json.load(f)

        for match in data.get("matches", []):
            print(f"{match['home_team']} vs {match['away_team']}")
            if match.get("odds"):
                print(f"  Line: {match['odds'].get('match_total', 'N/A')}")
            if match.get("h2h_matches"):
                print(f"  H2H games: {len(match['h2h_matches'])}")
```

---

## Related Documentation

- [Fragile Selectors Watchlist](fragile_selectors_watchlist.md) — CSS selectors that may break with Flashscore UI updates
- [Integration Guide](integration_guide.md) — Output schema and URL structure reference
- [Results Update Guide](results_update_guide.md) — Workflow for updating match results
- [Development Plan](dev/plan.md) — Scraper-only roadmap and priorities
