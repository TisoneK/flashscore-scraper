# Flashscore Basketball Scraper

A powerful basketball match data scraper with a modern GUI interface, designed to extract comprehensive match data from Flashscore.co.ke.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Internet connection (for automatic driver download)

### Installation

1. **Clone and install:**
```bash
git clone https://github.com/TisoneK/flashscore-scraper.git
cd flashscore-scraper
pip install -e .
```

2. **Set up drivers:**
```bash
fss --init
```

3. **Start scraping:**
```bash
fss -u    # Launch GUI (recommended)
# or
fss -c    # Launch CLI
```

## 🖥️ Usage

### Basic Scraping

#### GUI Mode (Recommended)
```bash
fss -u
```
The GUI provides:
- **Dashboard**: Overview of recent scraping activity
- **Scraper Control**: Start/stop scraping with real-time progress
- **Results View**: Browse and filter scraped data
- **Settings**: Configure scraping parameters
- **Export**: Download data as JSON

#### CLI Mode
```bash
fss -c
```
Interactive CLI with:
- **Menu-driven interface**: Easy navigation
- **Real-time progress**: Live scraping status
- **Data export**: Save results to files
- **Configuration**: Adjust settings on the fly
- **Driver Management**: Configure browser drivers through settings menu

### CLI Settings Menu
The CLI includes a comprehensive settings menu accessible via "Configure Settings":

#### Browser Settings
- **Headless Mode**: Run browser in background (configurable via CLI settings)
- **Window Size**: Browser window dimensions
- **Image Loading**: Enable/disable image loading for performance

#### Driver Management
- **Check Driver Status**: Verify current driver installation
- **List Installed Drivers**: View all available Chrome versions
- **Set Default Driver**: Choose which version to use by default
- **Install New Driver**: Install a specific Chrome version

#### Output Settings
- **File Format**: Choose JSON or CSV output format
- **Log Level**: Set logging detail level (INFO, DEBUG, WARNING, ERROR)

#### Logging Settings
- **Log Level**: Configure console and file logging detail
- **Output Directory**: Set where logs and data are saved

### Advanced Usage

#### Driver Management
```bash
# Install specific Chrome version
fss --init chrome 138

# Install Firefox drivers
fss --init firefox

# Install drivers only (if already set up)
fss --install-drivers

# List available Chrome versions
fss --list-versions
```

#### Alternative Launch Methods
```bash
# Full command names
flashscore-scraper --ui
flashscore-scraper --cli

# Direct Python execution
python main.py
python -m src.ui.main
python -m src.cli.cli_manager
```

## 📚 Tutorial

### First Time Setup
1. **Install and initialize:**
   ```bash
   git clone https://github.com/TisoneK/flashscore-scraper.git
   cd flashscore-scraper
   pip install -e .
   fss --init
   ```

2. **Launch the GUI:**
   ```bash
   fss -u
   ```

3. **Configure settings:**
   - Go to Settings page
   - Adjust scraping limits, timeouts, and data fields
   - Save your preferences

4. **Start scraping:**
   - Go to Scraper Control page
   - Click "Start Scraping"
   - Watch real-time progress
   - View results in Results page

### Data Output
- **Location**: `output/json/` directory
- **Format**: JSON files with match data
- **Organization**: Daily files with timestamps
- **Content**: Match details, odds, head-to-head data

### Configuration
The scraper can be configured through:
- **GUI Settings**: Interactive configuration panel
- **src/config.json**: Direct file editing
- **CLI**: Command-line options

Key settings include:
- **Scraping limits**: Max matches, timeouts
- **Browser options**: Headless mode, window size
- **Data fields**: Which information to extract
- **Output settings**: File organization and naming

## 🎯 Features

### Core Scraping
- **Live & Upcoming Matches**: Scrapes current and scheduled basketball matches
- **Comprehensive Data**: Extracts match details, odds, and head-to-head statistics
- **Multiple Data Sources**: Match information, betting odds, and historical H2H data
- **Smart Filtering**: Processes matches based on data completeness criteria

### Modern UI Interface
- **Dashboard Overview**: Quick stats and recent activity
- **Real-time Progress**: Live scraping progress with detailed logging
- **Data Visualization**: Filterable results table with detailed match views
- **Configuration Management**: Easy settings adjustment for all scraper parameters
- **Export Functionality**: Export filtered data to JSON format

### Data Output
- **JSON Storage**: Structured data storage with metadata
- **Daily Files**: Automatic daily file organization
- **Complete/Incomplete Tracking**: Separate handling of successful and failed scrapes
- **Metadata Tracking**: File information, processing statistics, and timestamps

## 📁 Project Structure

```
flashscore-scraper/
├── main.py                 # Main entry point (UI by default)
├── src/config.json        # Configuration file
├── requirements.txt       # Dependencies
├── pyproject.toml        # Project configuration
├── src/                   # Core scraper logic
│   ├── scraper.py         # Main scraper class
│   ├── config.py          # Configuration management
│   ├── models.py          # Data models
│   ├── driver.py          # WebDriver management (legacy)
│   ├── cli/               # CLI interface
│   │   ├── cli_manager.py # Main CLI manager
│   │   ├── display.py     # Console display
│   │   ├── progress.py    # Progress tracking
│   │   ├── prompts.py     # User prompts
│   │   └── cli_settings.json # CLI-specific settings
│   ├── core/              # Core functionality
│   │   ├── batch_processor.py
│   │   ├── error_handler.py
│   │   ├── network_monitor.py
│   │   ├── performance_monitor.py
│   │   ├── tab_manager.py
│   │   └── url_verifier.py
│   ├── data/              # Data processing
│   │   ├── elements_model.py
│   │   ├── extractor/     # Data extractors
│   │   ├── loader/        # Data loaders
│   │   └── verifier/      # Data verifiers
│   ├── driver_manager/    # Driver management system
│   │   ├── web_driver_manager.py # Main WebDriver manager
│   │   ├── chrome_driver.py     # Chrome driver management
│   │   ├── firefox_driver.py    # Firefox driver management
│   │   └── driver_installer.py  # Driver installation
│   ├── storage/           # Data storage
│   │   ├── database.py
│   │   └── json_storage.py
│   ├── utils/             # Utilities
│   │   ├── driver_manager.py # Legacy driver management
│   │   ├── progress_monitor.py
│   │   ├── selenium_utils.py
│   │   └── utils.py
│   ├── scripts/           # Utility scripts
│   │   ├── run_ui.py      # UI launcher
│   │   ├── run_cli.py     # CLI launcher
│   │   ├── setup_platform.py # Platform setup
│   │   └── activate_and_run.py # Environment activation
│   ├── ui/                # GUI interface
│   │   ├── main.py        # UI application
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Application pages
│   │   └── utils/         # UI utilities
│   └── api/               # API interface
├── docs/                  # Documentation
│   ├── index.md           # Main documentation
│   └── issues.md          # Known issues
├── tests/                 # Test suite
│   ├── test_headless.py   # Headless mode test
│   ├── test_data_extractors.py
│   ├── test_data_loaders.py
│   ├── test_data_verifiers.py
│   ├── test_driver.py
│   ├── test_elements_model.py
│   ├── test_models.py
│   ├── test_odds_data_extractor.py
│   ├── test_scraper.py
│   └── run_tests.py
├── output/                # Scraped data (gitignored)
│   ├── json/              # JSON output files
│   └── logs/              # Scraping logs
└── drivers/               # WebDriver executables (auto-downloaded)
    ├── windows/           # Windows drivers
    │   └── chrome/        # Chrome versions
    ├── linux/            # Linux drivers
    └── mac/              # macOS drivers
```

## ⚙️ Configuration

The scraper can be configured through the UI settings or by editing `src/config.json`:

### Browser Settings
- **Headless Mode**: Run browser in background (configurable via CLI settings)
- **Window Size**: Browser window dimensions
- **Image Loading**: Enable/disable image loading for performance

### Timeout Settings
- **Page Load Timeout**: Maximum time to load pages

## 🔧 Troubleshooting

### Driver Issues
If you encounter browser driver problems:

```bash
# Reinstall drivers
fss --install-drivers

# Install specific Chrome version
fss --install-drivers chrome 138

# List available versions
fss --list-versions
```

### Common Problems
- **Chrome version mismatch**: Use `fss --init chrome 138` to match your Chrome version
- **Permission errors**: Run as administrator or check file permissions
- **Network timeouts**: Increase timeout settings in src/config.json
- **Memory issues**: Reduce batch size in settings
- **Element Timeout**: Maximum time to find elements
- **Retry Settings**: Number of retries and delay between attempts

### Output Settings
- **Output Directory**: Where to save scraped data
- **Log Level**: Detail level for logging
- **Batch Processing**: Batch size and adaptive delays

## 📊 Data Format

### Match Data Structure
```json
{
  "match_id": "unique_match_id",
  "country": "Country Name",
  "league": "League Name",
  "home_team": "Home Team",
  "away_team": "Away Team",
  "date": "Match Date",
  "time": "Match Time",
  "status": "complete|incomplete",
  "odds": {
    "home_odds": 1.85,
    "away_odds": 1.95,
    "over_odds": 1.90,
    "under_odds": 1.90,
    "match_total": 180.5
  },
  "h2h_matches": [
    {
      "date": "Previous Match Date",
      "home_team": "Home Team",
      "away_team": "Away Team",
      "home_score": 85,
      "away_score": 92,
      "competition": "Competition Name"
    }
  ]
}
```

## 🔧 Advanced Usage

### Command Line Options
```bash
# Launch UI (default)
python main.py

# Launch UI explicitly
python main.py --ui

# Run CLI scraper
python main.py --cli

# Run CLI scraper (short form)
python main.py -c
```

### Programmatic Usage
```python
from src.scraper import FlashscoreScraper

# Initialize scraper
scraper = FlashscoreScraper()

# Run scraping
scraper.scrape()
```

## 🐛 Troubleshooting

### Common Issues

1. **WebDriver Issues**
   - Ensure Chrome/Firefox is installed
   - Run `python setup_drivers.py` to install drivers
   - Check webdriver-manager is working
   - Try updating browser drivers

2. **Import Errors**
   - Verify all dependencies are installed
   - Check Python path includes project root
   - Ensure virtual environment is activated

3. **No Data Scraped**
   - Check internet connection
   - Verify Flashscore.co.ke is accessible
   - Review log files for errors

## 🤖 Automated Driver Management

The scraper now includes an automated driver management system that uses the [Chrome for Testing API](https://googlechromelabs.github.io/chrome-for-testing/#stable) to automatically download and install the correct Chrome and ChromeDriver versions for your platform.

### Features
- **Cross-platform Support**: Automatically detects Windows, Linux, and macOS
- **Latest Versions**: Always downloads the latest stable Chrome for Testing versions
- **Automatic Installation**: Downloads and installs both Chrome binary and ChromeDriver
- **Platform Detection**: Automatically detects your system architecture (x64, ARM64, etc.)

### Usage
```bash
# Install drivers automatically
fss --install-drivers

# Check driver installation status
python -m src.driver_manager.driver_installer --check

# Manual driver installation
python -m src.driver_manager.driver_installer --install
```

### Supported Platforms
- **Windows**: x64 and x86 architectures
- **Linux**: x64 and ARM64 architectures  
- **macOS**: x64 and ARM64 (Apple Silicon) architectures

### What Gets Installed
- **Chrome Binary**: Latest stable Chrome for Testing version
- **ChromeDriver**: Matching ChromeDriver version
- **Platform-specific**: Correct binaries for your operating system

The automated driver manager ensures compatibility and eliminates manual driver management across different platforms.

## 📝 Notes

- This scraper is for educational purposes only
- Please respect Flashscore's terms of service
- Use responsibly and avoid overwhelming the server
- Consider implementing delays between requests

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is for educational purposes. Please respect the terms of service of any websites you scrape.

# Prediction Calculator Algorithm

## Overview

The prediction calculator algorithm is designed to estimate the likely outcome of a sports match using a combination of:
- Historical head-to-head (H2H) results
- Current betting odds (home, away, over/under, total)
- Statistical analysis of recent team performance

This document outlines the algorithmic steps, data requirements, and logic used to generate predictions.

---

## 1. Data Requirements

- **Match Odds**: Home odds, away odds, over/under odds, match total
- **H2H History**: List of previous matches between the two teams, including scores and dates
- **Recent Form (optional)**: Last N matches for each team, with scores

---

## 2. Algorithm Steps

### Step 1: Data Collection

- Gather the latest odds for the match (home, away, over, under, total).
- Retrieve at least the last 5 H2H matches between the teams.
- Optionally, collect recent form for each team (last 5 matches).

### Step 2: H2H Analysis

- Calculate the average total points scored in H2H matches.
- Calculate win rates for each team in H2H.
- Calculate average margin of victory.

### Step 3: Odds Analysis

- Identify the bookmaker's expected total (match_total).
- Compare the average H2H total to the bookmaker's total.
- Analyze the over/under odds:
  - If over_odds < under_odds, the market expects a higher-scoring game.
  - If under_odds < over_odds, the market expects a lower-scoring game.

### Step 4: Recent Form Adjustment (optional)

- Calculate each team's average points scored and conceded in their last N matches.
- Adjust the H2H averages based on recent form trends.

### Step 5: Prediction Calculation

- **Total Prediction**:
  - If H2H average total and recent form both exceed the bookmaker's total, lean towards "Over".
  - If both are below, lean towards "Under".
  - If mixed, use odds as a tiebreaker.

- **Winner Prediction**:
  - Combine H2H win rates, recent form, and odds (implied probability).
  - Calculate implied probability from odds:
    - `implied_prob = 1 / odds`
  - Adjust for recent form and H2H dominance.

### Step 6: Confidence Scoring

- Assign a confidence score based on:
  - Agreement between H2H, recent form, and odds
  - Number of H2H matches available
  - Magnitude of difference between calculated and bookmaker's total

---

## 3. Example Calculation

Suppose:
- H2H average total: 180
- Bookmaker total: 176.5
- Over odds: 1.85, Under odds: 1.95
- Recent form average total: 182

**Prediction**: Over 176.5  
**Confidence**: High (all indicators agree)

---

## 4. Pseudocode

```python
def predict(match, h2h_matches, odds, recent_form=None):
    h2h_total = average([m.home_score + m.away_score for m in h2h_matches])
    h2h_win_rate_home = sum(1 for m in h2h_matches if m.home_score > m.away_score) / len(h2h_matches)
    bookmaker_total = odds.match_total
    over_odds = odds.over_odds
    under_odds = odds.under_odds

    # Recent form adjustment
    if recent_form:
        recent_total = average([m.home_score + m.away_score for m in recent_form])
        avg_total = (h2h_total + recent_total) / 2
    else:
        avg_total = h2h_total

    # Total prediction
    if avg_total > bookmaker_total:
        total_pred = "Over"
    else:
        total_pred = "Under"

    # Winner prediction (simplified)
    home_prob = 1 / odds.home_odds
    away_prob = 1 / odds.away_odds
    winner_pred = "Home" if home_prob > away_prob else "Away"

    # Confidence
    confidence = "High" if abs(avg_total - bookmaker_total) > 3 else "Medium"

    return {"total_pred": total_pred, "winner_pred": winner_pred, "confidence": confidence}
```

---

## 5. Notes

- The algorithm can be extended with more advanced statistical or machine learning models.
- Always validate predictions against real outcomes to improve the model.

---

## 6. References

- [Implied Probability from Odds](https://www.sportsbookreview.com/betting-odds/converter/)
- [Sports Prediction Models](https://www.kaggle.com/competitions/ncaam-march-mania-2021/overview)

---

*This document serves as a blueprint for implementing or improving the prediction calculator in your project.* 