# Flashscore Basketball Scraper

A powerful basketball match data scraper with a modern GUI interface, designed to extract comprehensive match data from Flashscore.co.ke.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Chrome or Firefox browser

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd flashscore_scraper_1o
```

2. **Initialize everything (recommended):**
```bash
flashscore-scraper --init
```
This will:
- Create virtual environment automatically
- Install all dependencies
- Set up browser drivers
- Create necessary directories

3. **Activate virtual environment:**
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

4. **Start using the scraper:**
```bash
fss -u    # Launch GUI
fss -c    # Launch CLI
```

## 🖥️ Usage

### Quick Start
After installation, you can use these simple commands:

```bash
# Initialize project and install drivers
flashscore-scraper --init

# Launch GUI (recommended)
flashscore-scraper --ui
# or short form
fss -u

# Launch CLI
flashscore-scraper --cli
# or short form
fss -c

# Show help
flashscore-scraper --help
```

### Alternative Methods

#### GUI Mode
```bash
python main.py
# or
python run_ui.py
```

#### CLI Mode
```bash
python main.py --cli
# or
python run_cli.py
```

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
flashscore_scraper_1o/
├── main.py                 # Main entry point (UI by default)
├── run_ui.py              # UI launcher
├── run_cli.py             # CLI launcher
├── requirements.txt       # Dependencies
├── src/                   # Core scraper logic
│   ├── scraper.py         # Main scraper class
│   ├── config.py          # Configuration management
│   ├── models.py          # Data models
│   └── storage/           # Data storage
├── ui/                    # GUI interface
│   ├── main.py            # UI application
│   ├── components/        # Reusable UI components
│   ├── pages/             # Application pages
│   └── utils/             # UI utilities
├── output/                # Scraped data
│   ├── json/              # JSON output files
│   └── logs/              # Scraping logs
└── drivers/               # WebDriver executables
    ├── windows/           # Windows drivers
    ├── linux/            # Linux drivers
    └── mac/              # macOS drivers
```

## ⚙️ Configuration

The scraper can be configured through the UI settings or by editing `config.json`:

### Browser Settings
- **Headless Mode**: Run browser in background
- **Window Size**: Browser window dimensions
- **Image Loading**: Enable/disable image loading for performance

### Timeout Settings
- **Page Load Timeout**: Maximum time to load pages
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

4. **UI Not Launching**
   - Install flet: `pip install flet==0.27.1`
   - Check for display/rendering issues
   - Verify system requirements

### Logs
- **UI Logs**: Displayed in the Scraper page
- **CLI Logs**: Written to `output/logs/` directory
- **Export Logs**: Use export functionality in UI

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