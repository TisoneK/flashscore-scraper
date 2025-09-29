# Flashscore Basketball Scraper

A powerful command-line basketball match data scraper designed to extract comprehensive match data from Flashscore.

## 🚀 Quick Start

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

### 🛠️ Troubleshooting Installation Issues

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

## 🎯 Features

- **CLI Interface**: Intuitive command-line interface with interactive menus and rich output
- **Multi-threaded Scraping**: Efficient parallel processing of matches
- **Data Export**: Save results in multiple formats (JSON, CSV)
- **Configurable**: Customize scraping behavior through configuration files

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

- **JSON Storage:** Structured data written under `output/json/`
- **Daily Files:** Files named like `matches_DDMMYY.json` and `results_DDMMYY.json`
- **Complete/Incomplete Tracking:** Separate handling of successful and skipped matches (with reasons)
- **Metadata Tracking:** File info, processing statistics, timestamps

---

## 📁 Project Structure

```
flashscore-scraper/
├── main.py                 # Main entry point (CLI + cleanup)
├── config.py               # Root configuration (legacy hooks)
├── requirements.txt        # Dependencies
├── pyproject.toml          # Project configuration (entry points: fss, fss-cleanup)
├── scripts/                # Root utilities
│   ├── test_large_download.py
│   ├── update_config_imports.py
│   └── update_config_imports_to_utils.py
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
    │
    ├── cli/
    │   ├── __init__.py
    │   ├── cli_manager.py  # CLI entry (also exposed as `fss`)
    │   ├── cli_settings.json
    │   ├── colors.py
    │   ├── display.py
    │   ├── performance_display.py
    │   ├── progress.py
    │   └── prompts.py
    │
    ├── core/
    │   ├── __init__.py
    │   ├── batch_processor.py
    │   ├── error_handler.py
    │   ├── exceptions.py
    │   ├── graceful_degradation.py
    │   ├── network_monitor.py
    │   ├── performance_monitor.py
    │   ├── resource_manager.py
    │   ├── retry_manager.py
    │   ├── tab_manager.py
    │   ├── url_builder.py
    │   ├── url_verifier.py
    │   └── worker_pool.py
    │
    ├── data/
    │   ├── __init__.py
    │   ├── elements_model.py
    │   ├── extractor/
    │   ├── loader/
    │   └── verifier/
    │
    ├── driver_manager/
    │   ├── __init__.py
    │   ├── chrome_driver.py
    │   ├── downloader.py
    │   ├── driver_installer.py
    │   ├── exceptions.py
    │   ├── firefox_driver.py
    │   ├── progress.py
    │   └── web_driver_manager.py
    │
    ├── prediction/
    │   ├── __init__.py
    │   ├── calculator/
    │   ├── example_usage.py
    │   └── prediction_data_loader.py
    │
    ├── scripts/
    │   ├── activate_and_run.py
    │   ├── demo_performance_display.py
    │   ├── run_cli.py
    │   ├── setup_drivers.py
    │   └── setup_platform.py
    │
    ├── storage/
    │   └── json_storage.py
    │
    └── utils/
        ├── __init__.py
        ├── cleanup.py
        ├── config_loader.py
        ├── progress_monitor.py
        └── selenium_utils.py
```

---

## ℹ️ Troubleshooting

- **Driver issues:**
  - `fss --install-drivers chrome [VERSION]`
  - `fss --list-versions`
- **Permission errors:** Run as administrator or check file permissions
- **Network timeouts:** Increase timeout settings in `src/config.json`
- **Logs location:** Check `output/logs/` for `scraper_*.log` and `chrome_*.log`
- **Memory issues:** Reduce batch size in settings

---

## 📚 Documentation

See the `docs/` directory for more detailed guides and technical documentation. 