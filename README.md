# Flashscore Basketball Scraper

A powerful command-line basketball match data scraper designed to extract comprehensive match data from Flashscore.

## Quick Start

### Prerequisites
- Python 3.8+
- Internet connection (for automatic driver download)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/TisoneK/flashscore-scraper.git
cd flashscore-scraper
```

2. **Create and activate virtual environment:**
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

3. **Install the package:**
```bash
pip install -e .
```

4. **Initialize drivers:**
```bash
fss --init                 # default: chrome 138
# or specify browser/version
fss --init chrome 139
fss --init firefox
```

5. **Start scraping:**
```bash
fss    # or: fss -c
```

### Railway Deployment

This project is deployed on [Railway](https://railway.app) at **[flashscore-scraper.up.railway.app](https://flashscore-scraper.up.railway.app/)**.

1. **Push this repo to GitHub** (or any Git provider)
2. **Create a new Railway project** from your repository
3. **Railway auto-detects** the `railway.toml` — the scraper runs daily on schedule
4. **Set environment variables** (optional):
   - `SCOREWISE_WEBHOOK_URL` — endpoint to POST scraped data
   - `SCOREWISE_API_KEY` — API key for the webhook
5. **Deploy** — Railway builds the Docker image and runs the cron jobs

The scraper runs twice daily (6:00 and 6:30 UTC) and outputs JSON to `output/json/`.

### Troubleshooting Installation Issues

If you encounter corrupted package installations (e.g., `ModuleNotFoundError: No module named 'src'`), use the cleanup utility:

```bash
# Method 1: Using the cleanup command (if package is installed)
fss-cleanup

# Method 2: Emergency cleanup via main.py (most reliable fallback)
python main.py --cleanup

# Method 3: Direct module execution (if main.py fails)
python -m src.utils.cleanup
python -m src.utils.cleanup --clean  # Clean only (no reinstall)
```

**Common signs of corrupted installation:**
- `fss` command not found or fails to run
- Import errors when running the scraper
- Warning messages about "invalid distribution"

---

## CLI Quick Reference

| Command | Description |
|---------|-------------|
| `fss` or `fss -c` | Launch the interactive CLI |
| `fss --init [BROWSER] [VERSION]` | Initialize project, set up venv, install drivers (chrome/firefox) |
| `fss --install-drivers [BROWSER] [VERSION]` | Install browser drivers only |
| `fss --list-versions` | List available Chrome versions |
| `fss --results-update JSON_FILE --output OUTPUT_FILE` | Update match results from a JSON file |
| `--version`, `-v` | Show version |
| `--debug` | Enable debug output |

---

## Features

- **CLI Interface**: Intuitive command-line interface with interactive menus and rich output
- **Multi-threaded Scraping**: Efficient parallel processing of matches
- **Data Export**: Save results in multiple formats (JSON, CSV)
- **Configurable**: Customize scraping behavior through configuration files
- **Scheduled Scraping**: Set up recurring scraping sessions with custom intervals
- **Performance Monitoring**: Live resource and progress tracking

---

## Settings

Accessible via the CLI "Configure Settings" menu:
- **Browser Settings:**
  - Headless mode (run browser in background)
- **Driver Management:**
  - Check driver status
  - List installed drivers
  - Set default driver
  - Install new driver
- **Output Settings:**
  - File format: JSON or CSV
- **Logging Settings:**
  - Log level: INFO, DEBUG, WARNING, ERROR
- **Day Selection:**
  - Default day to scrape (Today, Tomorrow, etc.)
- **Terminal Clearing:**
  - Enable/disable auto-clear of terminal

---

## Data Output

- **JSON Storage:** Structured data written under `output/json/`
- **Daily Files:** Files named like `matches_DDMMYY.json` and `results_DDMMYY.json`
- **Complete/Incomplete Tracking:** Separate handling of successful and skipped matches (with reasons)
- **Metadata Tracking:** File info, processing statistics, timestamps

### Output Schema

Each match record includes:
- Match metadata: `match_id`, `home_team`, `away_team`, `date`, `league`, `status`
- Odds: `over_under` line + bookmaker odds
- H2H history: last N completed matches between the two teams
- Results: final scores (when available)

External tools consume this JSON directly — no API server required.

---

## Project Structure

```
flashscore-scraper/
├── main.py                 # Main entry point (CLI + cleanup)
├── requirements.txt        # Dependencies
├── pyproject.toml          # Project configuration (entry points: fss, fss-cleanup)
├── drivers/                # Browser drivers storage
├── output/                 # Outputs
│   ├── json/               # `matches_DDMMYY.json`, `results_DDMMYY.json`
│   └── logs/               # `scraper_*.log`, `chrome_*.log`
└── src/                    # Core scraper logic
    ├── __init__.py
    ├── config.json         # Runtime configuration
    ├── driver.py           # WebDriver bootstrap
    ├── models.py           # Data models
    ├── scraper.py          # Main scraping workflows
    ├── cli/                # CLI interface (menus, display, prompts, colors, progress)
    ├── core/               # Core utilities (batch, retry, network, tabs, URLs)
    ├── data/               # Data layer (extractors, loaders, verifiers)
    ├── driver_manager/     # Chrome/Firefox driver management
    ├── reporting/          # Reporter interface
    ├── scripts/            # Setup and run scripts
    ├── storage/            # JSON and database storage
    └── utils/              # Selenium utils, config loader, cleanup
```

---

## Troubleshooting

- **Driver issues:**
  - `fss --install-drivers chrome [VERSION]`
  - `fss --list-versions`
- **Permission errors:** Run as administrator or check file permissions
- **Network timeouts:** Increase timeout settings in `src/config.json`
- **Logs location:** Check `output/logs/` for `scraper_*.log` and `chrome_*.log`
- **Memory issues:** Reduce batch size in settings

---

## Documentation

See the `docs/` directory for more detailed guides and technical documentation.
