# Flashscore Scraper — Development Plan

## Purpose

This document tracks the development roadmap for the Flashscore scraper as a standalone, focused tool. The scraper's sole job is to extract structured match data from Flashscore and output it as JSON/CSV files.

---

## Current Status

The scraper is fully functional for basketball match data extraction with:
- CLI interface with interactive menus
- Scheduled and on-demand scraping
- Match, odds, H2H, and results data extraction
- JSON and CSV output
- Performance monitoring and resource management
- Chrome and Firefox driver management

---

## Roadmap

### 1. Selector Maintenance (Ongoing)
- Monitor and update CSS selectors as Flashscore UI changes
- Maintain the [Fragile Selectors Watchlist](../fragile_selectors_watchlist.md)
- Add automated selector health checks

### 2. New Sport/League Support
- Generalize the scraper to support football (soccer), tennis, and other Flashscore sports
- Make sport selection configurable from the CLI and config.json
- Adapt selectors per sport where needed

### 3. Output Enhancements
- Add CSV output alongside JSON (partially supported)
- Add date-range scraping and multi-day output aggregation
- Include scraper run metadata (timestamp, config snapshot, duration)
- Add deduplication logic for repeated runs on the same date

### 4. Performance and Reliability
- Improve headless mode stability on Linux servers
- Reduce memory footprint for long-running scheduled sessions
- Better handling of Cloudflare/bot detection challenges
- Add retry with exponential backoff for transient failures

### 5. Developer Experience
- Improve test coverage for extractors and loaders
- Add a `--dry-run` mode that shows what would be scraped without launching a browser
- Add structured logging with JSON output option
- Improve error messages and diagnostics

### 6. Results Update Feature
- Complete the results update workflow for final scores
- Add incremental updates (only fetch results for matches not yet completed)
- Support merging results into existing match data files

---

## Completed

- [x] CLI-only operation (GUI/UI removed)
- [x] Prediction/ScoreWise code moved to separate repository
- [x] FastAPI layer removed (scraper is library + CLI only)
- [x] Cleanup of legacy config.py and migration scripts
- [x] Driver management (Chrome + Firefox) with auto-installation
- [x] Performance monitoring and display
- [x] Scheduling and repetitive scraping
- [x] Results scraping workflow
