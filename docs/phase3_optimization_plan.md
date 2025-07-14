# Phase 3 Optimization Plan (Updated)

## Objective
Enhance the Flashscore Scraper with real-time observability, actionable feedback, and robust performance monitoring during scraping, focusing on both user experience and system diagnostics.

---

## Key Improvements

### 1. Centralized Performance Dashboard
- Integrate a Rich-based `PerformanceDisplay` as the default CLI dashboard.
- Show real-time progress, current task, and key metrics (memory, CPU, tasks, success rate, average match time).
- Use a single, live-updating terminal UI for all scraping operations.

### 2. Data Module Instrumentation
- Instrument all major data module components (extractors, loaders, verifiers) to:
  - Report the current stage/module to the dashboard (e.g., "Extracting Odds", "Loading H2H").
  - Track and report per-match processing time.
  - Optionally, report batch-level progress if batching is used.

### 3. Enhanced Metrics & Insights
- Track and display:
  - **Average match processing time** (auto-updating as matches are processed)
  - **Memory usage** and **CPU usage** (using `psutil`)
  - **Batch progress** (if applicable)
  - **Success rate** (configurable definition: e.g., matches with all required data)
  - **Number of matches with missing odds/H2H**
  - **Number of skipped matches**
  - **Number of completed matches**

### 4. Error & Warning Reporting
- Add a panel for recent errors/warnings (e.g., failed matches, missing data, network issues).
- Show alerts for timeouts, scraping failures, or critical issues.

### 5. User Experience & Terminal Compatibility
- Recommend using **Windows Terminal** or a modern terminal emulator for best results.
- Lower the Rich dashboard refresh rate (e.g., 1/sec) to reduce flicker/trembling on Windows CMD/Git Bash.
- Optionally, allow users to configure refresh rate and dashboard panels.

### 6. Future/Optional Enhancements
- Support for more granular metrics (e.g., per-stage timing, network latency, retries).
- User-configurable dashboard panels and metrics.
- Export of performance metrics for offline analysis.

---

## Implementation Steps
1. Integrate `PerformanceDisplay` into CLI manager and scraping workflow.
2. Refactor data modules to report stage and timing to the dashboard.
3. Add metrics collection for memory, CPU, and match timing.
4. Implement error/warning reporting and data insights.
5. Test on multiple terminals and document best practices for users.
6. Gather feedback and iterate on dashboard features.

---

## Outcome
- Users and developers will have real-time, actionable visibility into scraping progress, performance, and issues.
- Debugging and optimization will be easier with live metrics and error reporting.
- The CLI will provide a modern, professional, and user-friendly experience. 