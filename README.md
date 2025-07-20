# Flashscore Basketball Scraper

A powerful basketball match data scraper with a modern CLI interface, designed to extract comprehensive match data from Flashscore.co.ke.

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
fss    # or: fss -c
```

---

## 🖥️ CLI Quick Reference

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

## 💡 Example CLI Session

### Launching the CLI
```bash
$ fss
Flashscore Basketball Scraper
Interactive CLI for scraping basketball match data

Features:
• One-click scraping with defaults
• Interactive configuration
• Real-time progress tracking
• Rich console output

What would you like to do?
> Start Scraping
  Configure Settings
  View Status
  Prediction
  Exit
```

### Scraping Flow
```bash
> Start Scraping

🚀 Scraping Mode
Extract basketball match data from Flashscore

Select day to scrape:
> Today
  Tomorrow
  Back

🚀 Starting scraping for today...

[Progress bars and live status updates appear here]

✅ Scraping completed successfully!
Successfully collected 24 matches!
============================================================
```

### Configuring Settings
```bash
> Configure Settings

⚙️  Settings Configuration
Configure your scraper settings and preferences

What would you like to configure?
> Browser Settings
  Driver Management
  Output Settings
  Logging Settings
  Day Selection
  Terminal Clearing

Run browser in headless mode? (Y/n): Y
✅ Settings saved successfully!
```

### Prediction Menu
```bash
> Prediction

🔮 Match Predictions
Analyze match data and generate predictions

Prediction - Select range:
> Today
  Yesterday
  Tomorrow
  All
  Back

[Prediction tables with actionable OVER/UNDER and HOME/AWAY results appear here]

What would you like to do?
> Filter Results
  Sort Results
  View Details/Export
  Back
```

### Viewing Status
```bash
> View Status

📊 Scraper Status
View current scraper status and statistics

Current Status:
• Output files: 12
• Output directory: output/
```

### Exiting
```bash
> Exit

👋 Goodbye!
```

---

## 🏀 Features

- **Interactive CLI:** Menu-driven interface for scraping, configuration, and predictions
- **Real-time Progress:** Live progress bars and status updates
- **Driver Management:** Install, list, and set default browser drivers
- **Settings Management:** Configure browser, output, logging, and more
- **Prediction Module:** ScoreWise algorithm for match predictions
- **Rich Console Output:** Enhanced visuals using Rich
- **Performance Monitoring:** Track scraping and system performance
- **Data Export:** Save results to JSON or CSV

---

## ⚙️ Settings

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

## 🔮 Prediction (ScoreWise)

- Access the Prediction menu from the CLI main menu
- Select prediction range: Yesterday, Today, Tomorrow, All
- Uses the ScoreWise algorithm to analyze match data and generate predictions for Over/Under bets
- View prediction results directly in the CLI

---

## 📊 Data Output

- **JSON Storage:** Structured data storage with metadata
- **Daily Files:** Automatic daily file organization
- **Complete/Incomplete Tracking:** Separate handling of successful and failed scrapes
- **Metadata Tracking:** File information, processing statistics, and timestamps

---

## 📁 Project Structure

```
flashscore-scraper/
├── main.py                 # Main entry point (CLI only)
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
│   │   ├── run_cli.py     # CLI launcher
│   │   ├── setup_platform.py # Platform setup
│   │   └── activate_and_run.py # Environment activation
│   └── api/               # API interface
├── docs/                  # Documentation
│   ├── index.md           # Main documentation
│   └── issues.md          # Known issues
```

---

## ℹ️ Troubleshooting

- **Driver Issues:**
  - Use `fss --install-drivers` to reinstall drivers
  - Use `fss --list-versions` to see available Chrome versions
- **Permission errors:** Run as administrator or check file permissions
- **Network timeouts:** Increase timeout settings in `src/config.json`
- **Memory issues:** Reduce batch size in settings

---

## 📚 Documentation

See the `docs/` directory for more detailed guides and technical documentation. 