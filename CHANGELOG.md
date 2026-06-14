# Changelog

All notable changes to the Flashscore Scraper are documented here.

---

## [Unreleased] — API Server + Railway Web Service

This release transforms the scraper from a stand-alone cron worker into a
persistent web service with a control API, while keeping full backward
compatibility for local/CLI usage.

### Added

- **`api_server.py`** — New FastAPI control server (522 lines) with the
  following REST endpoints:
  - `GET /health` — Liveness probe
  - `POST /scrape` — Trigger an async scrape (`{"day": "Today"|"Tomorrow"}`)
  - `GET /status` — Scraper state + last-scrape summary
  - `GET /history` — Recent scrape runs
  - `GET /outputs` — List available JSON output files
  - `GET /outputs/{filename}` — Download a specific JSON output
  - `GET /config` — Current `src/config.json`
  - `PUT /config` — Update `src/config.json` in real time
  - The server reads `$PORT` (Railway) or defaults to `8080`.

### Changed

- **`Dockerfile`** — Default `CMD` now runs `api_server.py` instead of
  `run_scraper_railway.py`. The scraper is triggered on demand via the API
  (or by an external cron job that `POST /scrape`).

- **`railway.toml`** — Changed from a **cron worker** to a **web service**
  so that Railway assigns a `$PORT` and exposes the API publicly. The
  `startCommand` is `python api_server.py`.

- **`requirements.txt`** — Added `fastapi>=0.110.0`, `uvicorn>=0.27.0`,
  and `pydantic>=2.5.0` for the API server.

- **`run_scraper_railway.py`** — Payload transformation to match the
  ScoreWise engine's `IngestRequest` schema:
  - New `_transform_payload()` function rebuilds the envelope as
    `{source, scraped_at, matches}` (the raw file used `{metadata, matches}`,
    which caused a 422 error).
  - New `_convert_h2h_date()` converts H2H dates from `DD/MM/YYYY` to
    ISO 8601 (`YYYY-MM-DD`) for correct lexicographic sorting.
  - Auth header changed from `Authorization: Bearer` to `X-API-Key` to
    match the engine's FastAPI dependency.
  - Incomplete matches (lacking odds/H2H) are filtered out.
  - Extra undeclared fields (`match_id` in odds, `competition` in H2H)
    are stripped.

- **`src/utils/utils.py`** — `format_date()` now returns ISO 8601
  (`YYYY-MM-DD`) instead of `DD/MM/YYYY`, fixing silently incorrect
  predictions when H2H matches span multiple years.

### Removed

- **`railway.toml`** — Removed `[[cron]]` blocks. Scheduling is now
  handled externally (e.g., Railway Cron Jobs → `POST /scrape`).

---

## [1.0.0] — Initial Release

- CLI-based scraper for Flashscore basketball matches
- Selenium/Chrome headless automation
- Odds extraction (home/away, over/under)
- Head-to-head match history extraction
- JSON output with daily file rotation
- Railway cron worker deployment
- ScoreWise webhook integration (original `Bearer` auth)
