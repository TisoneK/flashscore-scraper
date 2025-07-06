# Flashscore Scraper UI

A modern, feature-rich GUI for the Flashscore basketball scraper built with Flet.

## Features

### 🏠 Home Dashboard
- **Quick Stats**: Overview of total matches, complete/incomplete counts, and latest file
- **Quick Actions**: Direct access to scraper, results, and settings
- **Recent Activity**: Live updates of scraping activity and file information
- **Status Indicator**: Real-time system status

### 🔧 Scraper Control
- **Start/Stop Controls**: Simple one-click scraper control
- **Real-time Progress**: Live progress bar with match-by-match updates
- **Detailed Logging**: Comprehensive log display with export functionality
- **Statistics**: Time tracking, ETA calculation, and performance metrics

### 📊 Results Viewer
- **Data Table**: Sortable and filterable match data display
- **Advanced Filtering**: Filter by status, country, and league
- **Match Details**: Detailed view of selected matches including odds and H2H data
- **Export Functionality**: Export filtered results to JSON

### ⚙️ Settings Management
- **Browser Settings**: Headless mode, window size, image loading
- **Timeout Configuration**: Page load, element, and retry timeouts
- **Output Settings**: Directory and log level configuration
- **Batch Processing**: Batch size and adaptive delay settings

## Architecture

```
ui/
├── main.py                 # Main application entry point
├── components/             # Reusable UI components
│   ├── scraper_control.py  # Scraper start/stop controls
│   ├── progress_display.py # Progress tracking and logging
│   └── results_view.py     # Data display and filtering
├── pages/                  # Main application pages
│   ├── home_page.py        # Dashboard and overview
│   ├── scraper_page.py     # Scraping interface
│   ├── results_page.py     # Results display
│   └── settings_page.py    # Configuration management
└── utils/                  # UI utilities and helpers
    └── ui_helpers.py       # Common UI components and utilities
```

## Getting Started

### Prerequisites
- Python 3.8+
- Flet 0.27.1+
- All scraper dependencies

### Installation
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the UI:
   ```bash
   python -m src.scripts.run_ui
   ```

   Or directly:
   ```bash
   python ui/main.py
   ```

## Usage

### Starting the Application
The UI launches with a modern dark theme and navigation rail on the left side.

### Navigation
- **Home**: Dashboard with overview and quick actions
- **Scraper**: Start/stop scraping with real-time progress
- **Results**: View and filter scraped data
- **Settings**: Configure scraper behavior

### Scraping Process
1. Navigate to the **Scraper** page
2. Click **Start Scraper** to begin
3. Monitor progress in real-time
4. View results in the **Results** page
5. Use **Settings** to adjust configuration

### Data Management
- **Auto-refresh**: Home page stats update automatically
- **Manual refresh**: Use refresh buttons in Results page
- **Export**: Export filtered data to JSON files
- **Log export**: Save scraping logs to text files

## Configuration

### Browser Settings
- **Headless Mode**: Run browser in background (recommended)
- **Window Size**: Browser window dimensions
- **Disable Images**: Improve performance by disabling image loading

### Timeout Settings
- **Page Load Timeout**: Maximum time to load pages
- **Element Timeout**: Maximum time to find elements
- **Retry Delay**: Delay between retry attempts
- **Max Retries**: Maximum number of retry attempts

### Output Settings
- **Output Directory**: Where to save scraped data
- **Log Level**: Detail level for logging (DEBUG, INFO, WARNING, ERROR)

### Batch Processing
- **Batch Size**: Number of matches to process in batches
- **Base Delay**: Delay between batches
- **Adaptive Delay**: Automatically adjust delays based on performance

## Integration

The UI integrates seamlessly with the existing scraper:

- **Real-time Communication**: Progress updates via logging
- **Configuration Management**: Load/save settings to JSON
- **Data Display**: Read from existing JSON output files
- **Error Handling**: Graceful error display and recovery

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python path includes project root

2. **Scraper Not Starting**
   - Verify webdriver is available
   - Check browser settings in configuration

3. **No Data Displayed**
   - Ensure scraping has been run
   - Check output directory exists
   - Verify JSON files are readable

4. **UI Not Responding**
   - Check for long-running operations
   - Restart the application
   - Verify system resources

### Logs
- Application logs are displayed in the Scraper page
- Export logs using the export button
- Check console for additional error information

## Development

### Adding New Features
1. Create new components in `ui/components/`
2. Add new pages in `ui/pages/`
3. Update navigation in `ui/main.py`
4. Add utility functions in `ui/utils/`

### Styling
- Use the helper functions in `ui_helpers.py`
- Follow the dark theme color scheme
- Maintain consistent spacing and padding

### Testing
- Test all navigation flows
- Verify data loading and display
- Check error handling scenarios
- Test with different data sizes

## License

This UI is part of the Flashscore Scraper project and follows the same license terms. 