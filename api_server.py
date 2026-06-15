#!/usr/bin/env python3
"""
FastAPI control server for the Flashscore Scraper.

Provides a REST API that mirrors every capability of the interactive CLI:
  - Scrape scheduled matches (Today / Tomorrow) with live progress
  - Scrape final results for a given date
  - Stop a running scrape gracefully
  - View / update scraper configuration (all settings)
  - List / download JSON output files (match + results)
  - List available ChromeDriver versions
  - Install browser drivers (Chrome / Firefox)
  - Configure recurring scrape scheduling
  - Project health and scrape-run history

The scraper runs **in-process on a background thread** so that live progress
callbacks (current match, total, status messages) are forwarded to the API
in real time.  This matches the CLI's interactive progress experience.
"""

import sys
import os
import json
import logging
import asyncio
import csv
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from threading import Lock

import uvicorn
from fastapi import FastAPI, HTTPException, Query, APIRouter
from pydantic import BaseModel, Field

# ── Ensure project root is on sys.path ──────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Import scraper components directly (for live callbacks) ─────
from src.scraper import FlashscoreScraper
from src.driver_manager.driver_installer import DriverInstaller
from src.reporting import CallbackReporter

# ── FastAPI app ─────────────────────────────────────────────────
app = FastAPI(
    title="Flashscore Scraper API",
    version="1.0.0",
    description="Control server for the Flashscore basketball scraper. "
                "Mirrors all CLI capabilities via REST.",
)

# Add /api prefix so the admin dashboard can reach /api/scrape, /api/status etc.
router = APIRouter(prefix="/api")

# ── Logging ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api_server")

# ── Thread-safe shared state ────────────────────────────────────
_state_lock: Lock = Lock()
_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)
_scrape_history: List[Dict[str, Any]] = []
_schedule_task: Optional[asyncio.Task] = None


class _ScraperState:
    """Mutable state shared between the API event loop and the scraper thread."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.busy: bool = False
        self.scrape_id: Optional[str] = None
        self.scrape_type: Optional[str] = None       # "scheduled" | "results"
        self.day: Optional[str] = None               # "Today" / "Tomorrow"
        self.date: Optional[str] = None              # "DD.MM.YYYY" for results
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None

        # Progress (updated via callbacks from the scraper thread)
        self.current_match_index: int = 0
        self.total_matches: int = 0
        self.progress_message: Optional[str] = None
        self.status_message: Optional[str] = None
        self.complete_matches: int = 0
        self.incomplete_matches: int = 0

        # Outcome
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.stop_requested: bool = False


_state: _ScraperState = _ScraperState()


# ── Pydantic request / response schemas ─────────────────────────

class ScrapeRequest(BaseModel):
    day: str = Field("Today", description="Which day: 'Today' or 'Tomorrow'")

class ScrapeResponse(BaseModel):
    status: str
    message: str
    scrape_id: Optional[str] = None

class ResultsScrapeRequest(BaseModel):
    date: str = Field(..., description="Date in DD.MM.YYYY format, e.g. '13.06.2025'",
                      pattern=r"^\d{2}\.\d{2}\.\d{4}$")

class ConfigUpdateRequest(BaseModel):
    config: dict = Field(..., description="Partial or full config to merge into src/config.json")

class ScheduleConfigRequest(BaseModel):
    enabled: bool = Field(False, description="Enable recurring scraping")
    interval_minutes: int = Field(60, ge=15, le=1440, description="Interval between scrapes (min)")
    day: str = Field("Today", description="Day to scrape: 'Today' or 'Tomorrow'")
    start_time: Optional[str] = Field(None, description='Start time HH:MM or null for immediate',
                                       pattern=r"^\d{2}:\d{2}$|^$")

class DriverInstallRequest(BaseModel):
    browser: str = Field("chrome", description="'chrome' or 'firefox'")
    version: Optional[str] = Field(None, description="Major version, e.g. '138'. Default = latest")

class InitProjectRequest(BaseModel):
    browser: str = Field("chrome", description="'chrome' or 'firefox'")
    version: Optional[str] = Field(None, description="Driver major version, e.g. '138'")


# ════════════════════════════════════════════════════════════════
#  Background scraper runners (threaded, with live callbacks)
# ════════════════════════════════════════════════════════════════

def _run_scheduled_scrape(day: str, scrape_id: str) -> None:
    """Run FlashscoreScraper.scrape() on a background thread.

    All progress / status callbacks update ``_state`` under the lock so that
    ``GET /scrape/progress`` and ``GET /status`` reflect live state.
    """
    global _state
    import threading

    # Ensure stop flag is clear at the start of every run
    # (defensive: in case a previous run's stop_requested leaked)
    with _state_lock:
        _state.stop_requested = False

    # Clear the thread's _is_shutting_down flag — the previous scrape's
    # close() method sets this, and since ThreadPoolExecutor reuses the
    # same worker thread, it would poison the next run.
    threading.current_thread()._is_shutting_down = False

    def status_cb(msg: str) -> None:
        with _state_lock:
            _state.status_message = msg
        logger.info("[%s] %s", scrape_id, msg)

    def progress_cb(current: int, total: int, task: str = None) -> None:
        with _state_lock:
            _state.current_match_index = current
            _state.total_matches = total
            _state.progress_message = task or f"Processing match {current}/{total}"
        logger.debug("[%s] Progress: %d/%d — %s", scrape_id, current, total, task)

    def stop_cb() -> bool:
        with _state_lock:
            return _state.stop_requested

    scraper = FlashscoreScraper(
        status_callback=status_cb,
        progress_callback=progress_cb,
        reporter=CallbackReporter(status_callback=status_cb, progress_callback=progress_cb),
    )
    try:
        result = scraper.scrape(day=day, progress_callback=progress_cb,
                                status_callback=status_cb, stop_callback=stop_cb)
        with _state_lock:
            _state.result = result
            _state.complete_matches = result.get("complete_matches", 0)
            _state.incomplete_matches = result.get("incomplete_matches", 0)
            _state.busy = False
            _state.finished_at = datetime.now(timezone.utc).isoformat()
            _state.error = None
            _state.stop_requested = False  # Clear after successful run
        logger.info("[%s] Finished — %d complete, %d incomplete",
                    scrape_id, _state.complete_matches, _state.incomplete_matches)
    except Exception as exc:
        logger.error("[%s] Failed: %s", scrape_id, exc)
        with _state_lock:
            _state.result = None
            _state.busy = False
            _state.finished_at = datetime.now(timezone.utc).isoformat()
            _state.error = str(exc)
            _state.stop_requested = False  # Clear after failed run too

    _scrape_history.append({
        "scrape_id": scrape_id,
        "type": "scheduled",
        "day": day,
        "finished_at": _state.finished_at,
        "success": _state.error is None,
        "complete_matches": _state.complete_matches,
        "incomplete_matches": _state.incomplete_matches,
    })


def _run_results_scrape(date_str: str, scrape_id: str) -> None:
    """Run FlashscoreScraper.scrape_results() on a background thread."""
    global _state
    import threading

    # Ensure stop flag is clear at the start of every run
    with _state_lock:
        _state.stop_requested = False

    # Clear the thread's _is_shutting_down flag — the previous scrape's
    # close() method sets this, and since ThreadPoolExecutor reuses the
    # same worker thread, it would poison the next run.
    threading.current_thread()._is_shutting_down = False

    def status_cb(msg: str) -> None:
        with _state_lock:
            _state.status_message = msg
        logger.info("[%s] %s", scrape_id, msg)

    def progress_cb(current: int, total: int, task: str = None) -> None:
        with _state_lock:
            _state.current_match_index = current
            _state.total_matches = total
            _state.progress_message = task or f"Processing match {current}/{total}"

    scraper = FlashscoreScraper(status_callback=status_cb, progress_callback=progress_cb)
    try:
        scraper.scrape_results(date=date_str, status_callback=status_cb,
                               progress_callback=progress_cb)
        with _state_lock:
            _state.busy = False
            _state.finished_at = datetime.now(timezone.utc).isoformat()
            _state.error = None
            _state.result = {"date": date_str, "success": True}
            _state.stop_requested = False  # Clear after successful run
        logger.info("[%s] Results scrape for %s finished", scrape_id, date_str)
    except Exception as exc:
        logger.error("[%s] Results scrape failed: %s", scrape_id, exc)
        with _state_lock:
            _state.busy = False
            _state.finished_at = datetime.now(timezone.utc).isoformat()
            _state.error = str(exc)
            _state.stop_requested = False  # Clear after failed run too

    _scrape_history.append({
        "scrape_id": scrape_id,
        "type": "results",
        "date": date_str,
        "finished_at": _state.finished_at,
        "success": _state.error is None,
    })


def _prepare_state_for_run(scrape_type: str, **kwargs: Any) -> str:
    """Atomically reset + prepare state for a new background run.

    Returns the generated scrape_id.  Raises ``HTTPException(409)`` if
    a scrape is already in progress.
    """
    global _state
    with _state_lock:
        if _state.busy:
            raise HTTPException(409, "A scrape is already in progress")
        _state.reset()
        _state.busy = True
        _state.scrape_type = scrape_type
        _state.started_at = datetime.now(timezone.utc).isoformat()
        for k, v in kwargs.items():
            setattr(_state, k, v)

    scrape_id = datetime.now().strftime(
        f"{'results' if scrape_type == 'results' else 'scrape'}_%Y%m%d_%H%M%S"
    )
    with _state_lock:
        _state.scrape_id = scrape_id
    return scrape_id


# ════════════════════════════════════════════════════════════════
#  Health
# ════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Liveness probe.  Returns 200 when the server is ready."""
    with _state_lock:
        busy = _state.busy
    return {
        "status": "ok",
        "scraper_busy": busy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
#  Scrape — scheduled matches  (CLI: "Scheduled Matches")
# ════════════════════════════════════════════════════════════════

@router.post("/scrape", response_model=ScrapeResponse)
async def trigger_scrape(req: ScrapeRequest):
    """Scrape scheduled matches (Today / Tomorrow).

    Mirrors the CLI's **Scheduled Matches** mode.  The scraper runs on a
    background thread; poll ``GET /scrape/progress`` for live updates and
    ``GET /status`` for the final result.
    """
    if req.day not in ("Today", "Tomorrow"):
        raise HTTPException(422, "day must be 'Today' or 'Tomorrow'")

    scrape_id = _prepare_state_for_run("scheduled", day=req.day)
    _executor.submit(_run_scheduled_scrape, req.day, scrape_id)

    return ScrapeResponse(
        status="accepted",
        message=f"Scrape for {req.day} started (ID: {scrape_id})",
        scrape_id=scrape_id,
    )


# ════════════════════════════════════════════════════════════════
#  Scrape — results           (CLI: "Results" → date picker)
# ════════════════════════════════════════════════════════════════

@router.post("/scrape/results", response_model=ScrapeResponse)
async def trigger_results_scrape(req: ResultsScrapeRequest):
    """Scrape final match results for a given date.

    Mirrors the CLI's **Results** mode.  Date must be in ``DD.MM.YYYY``
    format (e.g. ``13.06.2025``).  Internally calls
    ``FlashscoreScraper.scrape_results()``.
    """
    # Validate the date is real (not just pattern-matched)
    try:
        datetime.strptime(req.date, "%d.%m.%Y")
    except ValueError:
        raise HTTPException(422, "Invalid date — must be a real date in DD.MM.YYYY format")

    scrape_id = _prepare_state_for_run("results", date=req.date)
    _executor.submit(_run_results_scrape, req.date, scrape_id)

    return ScrapeResponse(
        status="accepted",
        message=f"Results scrape for {req.date} started (ID: {scrape_id})",
        scrape_id=scrape_id,
    )


# ════════════════════════════════════════════════════════════════
#  Stop scrape                (CLI: Ctrl+C / Stop button)
# ════════════════════════════════════════════════════════════════

@router.post("/scrape/stop")
async def stop_scrape():
    """Request the running scrape to stop after the current match.

    The scraper checks this flag between matches; the current match
    finishes before the scrape halts cooperatively.
    """
    with _state_lock:
        if not _state.busy:
            raise HTTPException(409, "No scrape is currently running")
        _state.stop_requested = True

    logger.info("Stop requested — scrape will halt after current match")
    return {"status": "stop_requested", "message": "Scrape will stop after the current match"}


# ════════════════════════════════════════════════════════════════
#  Live progress             (CLI: Rich progress bars)
# ════════════════════════════════════════════════════════════════

@router.get("/scrape/progress")
async def get_scrape_progress():
    """Return real-time progress of the currently running scrape.

    Fields returned match what the CLI shows in its progress bars:
    ``current_match_index``, ``total_matches``, ``status_message``,
    ``progress_message``, ``stop_requested``, etc.
    """
    with _state_lock:
        return {
            "busy": _state.busy,
            "scrape_id": _state.scrape_id,
            "scrape_type": _state.scrape_type,
            "day": _state.day,
            "date": _state.date,
            "started_at": _state.started_at,
            "current_match_index": _state.current_match_index,
            "total_matches": _state.total_matches,
            "complete_matches": _state.complete_matches,
            "incomplete_matches": _state.incomplete_matches,
            "progress_message": _state.progress_message,
            "status_message": _state.status_message,
            "stop_requested": _state.stop_requested,
            "error": _state.error,
        }


# ════════════════════════════════════════════════════════════════
#  Status                    (CLI: "View Status")
# ════════════════════════════════════════════════════════════════

@router.get("/status")
async def get_status():
    """Return scraper state and a summary of the last completed scrape.

    Mirrors the CLI **View Status** screen which shows the overall
    scraper health and last-run statistics.
    """
    with _state_lock:
        busy = _state.busy
        last = _state.result
        err = _state.error

    if busy:
        status_text = "scraping"
    elif last is not None:
        status_text = "idle (last scrape succeeded)"
    elif err:
        status_text = "idle (last scrape failed)"
    else:
        status_text = "idle (no runs yet)"

    return {
        "status": status_text,
        "scraper_busy": busy,
        "last_scrape": {
            "success": err is None and last is not None,
            "error": err,
            "scrape_type": _state.scrape_type,
            "day": _state.day,
            "date": _state.date,
            "complete_matches": _state.complete_matches,
            "incomplete_matches": _state.incomplete_matches,
            "started_at": _state.started_at,
            "finished_at": _state.finished_at,
        } if not busy else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ════════════════════════════════════════════════════════════════
#  History
# ════════════════════════════════════════════════════════════════

@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=200)):
    """Return recent scrape runs (in-memory, last *limit* entries)."""
    return {"runs": _scrape_history[-limit:], "total": len(_scrape_history)}


# ════════════════════════════════════════════════════════════════
#  Outputs — list / download  (CLI: shows JSON file count)
# ════════════════════════════════════════════════════════════════

@router.get("/outputs")
async def list_outputs():
    """List JSON output files, split into ``match_files`` and ``results_files``.

    Mirrors the CLI's status screen which shows file counts in
    the ``output/json/`` directory.
    """
    json_dir = PROJECT_ROOT / "output" / "json"
    if not json_dir.exists():
        return {"match_files": [], "results_files": []}

    files = sorted(json_dir.iterdir(), key=os.path.getmtime, reverse=True)
    match_files: List[Dict[str, Any]] = []
    results_files: List[Dict[str, Any]] = []

    for f in files:
        if f.suffix != ".json":
            continue
        entry = {
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
        }
        if f.name.startswith("results_"):
            results_files.append(entry)
        elif f.name.startswith("matches_"):
            match_files.append(entry)

    return {"match_files": match_files, "results_files": results_files}


@router.get("/outputs/{filename:path}")
async def get_output(filename: str):
    """Download a specific JSON output file (e.g. ``matches_250614.json``)."""
    # Prevent directory traversal
    sanitised = Path(filename).name
    json_path = PROJECT_ROOT / "output" / "json" / sanitised
    if not json_path.exists() or not json_path.is_file():
        raise HTTPException(404, f"File '{sanitised}' not found")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(500, "File contains invalid JSON")


@router.get("/outputs/{filename:path}/csv")
async def get_output_csv(filename: str):
    """Download a specific JSON output file as CSV (flattened)."""
    sanitised = Path(filename).name
    json_path = PROJECT_ROOT / "output" / "json" / sanitised
    if not json_path.exists() or not json_path.is_file():
        raise HTTPException(404, f"File '{sanitised}' not found")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(500, "File contains invalid JSON")

    matches = data.get("matches", [])
    if not matches:
        raise HTTPException(404, "No match data in file")

    # Flatten first match for headers
    flat = _flatten_dict(matches[0])
    headers = list(flat.keys())

    from fastapi.responses import StreamingResponse

    async def stream_csv():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        for m in matches:
            writer.writerow(_flatten_dict(m))
        yield buf.getvalue()

    return StreamingResponse(
        stream_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={sanitised.replace('.json', '.csv')}"},
    )


def _flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """Recursively flatten a nested dict (e.g. odds.home_odds)."""
    items: List[tuple] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, json.dumps(v, ensure_ascii=False)))
        else:
            items.append((new_key, v))
    return dict(items)


# ════════════════════════════════════════════════════════════════
#  Configuration             (CLI: "Configure Settings")
# ════════════════════════════════════════════════════════════════

_CONFIG_PATH: Path = PROJECT_ROOT / "src" / "config.json"


@router.get("/config")
async def get_config():
    """Return the full scraper configuration from ``src/config.json``."""
    if not _CONFIG_PATH.exists():
        raise HTTPException(404, "Config file not found")
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(500, "Config file contains invalid JSON")


@router.put("/config")
async def update_config(req: ConfigUpdateRequest):
    """Update scraper configuration (deep-merge).

    Mirrors the CLI's **Configure Settings** screen.  Send the keys you
    want to change; nested dicts are merged recursively.
    """
    if not _CONFIG_PATH.exists():
        raise HTTPException(404, "Config file not found")

    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            current = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(500, "Config file contains invalid JSON")

    def _deep_merge(base: Dict, overlay: Dict) -> None:
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                _deep_merge(base[key], value)
            else:
                base[key] = value

    _deep_merge(current, req.config)

    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)

    logger.info("Configuration updated via API")
    return {"status": "ok", "config": current}


@router.get("/config/schema")
async def get_config_schema():
    """Return the config schema — a list of all top-level sections with descriptions."""
    return {
        "sections": {
            "browser": "Browser settings: headless, window_size, browser_name, chrome_binary_path, etc.",
            "timeout": "Timeouts: page_load, element, retry_delay, max_retries, etc.",
            "output": "Output settings: directory, date_format, time_format",
            "logging": "Logging: log_level, log_directory, quiet_modules, etc.",
            "batch": "Batch processing: base_batch_size, adaptive_delay, etc.",
            "scraping": "Scraping limits: max_matches, min_h2h_matches",
            "selectors": "CSS/XPath selectors for match, odds, H2H elements",
        }
    }


# ════════════════════════════════════════════════════════════════
#  Schedule — recurring scrape  (CLI: frequency picker)
# ════════════════════════════════════════════════════════════════

@router.get("/schedule")
async def get_schedule():
    """Return the current recurring scrape schedule."""
    sched_path = PROJECT_ROOT / "src" / "cli" / "cli_settings.json"
    defaults = {"enabled": False, "interval_minutes": 60, "day": "Today", "start_time": None}
    if sched_path.exists():
        try:
            with open(sched_path, "r") as f:
                stored = json.load(f)
                defaults.update(stored.get("schedule", {}))
        except Exception:
            pass
    return defaults


@router.put("/schedule")
async def set_schedule(req: ScheduleConfigRequest):
    """Configure recurring scraping (mirrors CLI frequency picker).

    When *enabled* is ``True``, the server will automatically trigger
    ``POST /scrape`` every *interval_minutes* for the given *day*,
    optionally starting at *start_time* (HH:MM).
    """
    sched_path = PROJECT_ROOT / "src" / "cli" / "cli_settings.json"
    settings = {"default_day": "Today"}
    if sched_path.exists():
        try:
            with open(sched_path, "r") as f:
                settings = json.load(f)
        except Exception:
            pass

    payload = req.model_dump()
    settings["schedule"] = payload

    sched_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sched_path, "w") as f:
        json.dump(settings, f, indent=2)

    # Restart the background scheduler
    global _schedule_task
    if _schedule_task is not None and not _schedule_task.done():
        _schedule_task.cancel()
    if req.enabled:
        _schedule_task = asyncio.create_task(_run_schedule_loop(req))

    logger.info("Schedule updated: enabled=%s, interval=%d min", req.enabled, req.interval_minutes)
    return {"status": "ok", "schedule": payload}


async def _run_schedule_loop(cfg: ScheduleConfigRequest) -> None:
    """Background coroutine that triggers scrapes on a schedule."""
    first_delay: float = 0.0
    if cfg.start_time:
        try:
            now = datetime.now()
            parts = cfg.start_time.split(":")
            target = now.replace(hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            first_delay = (target - now).total_seconds()
        except Exception:
            first_delay = 0.0

    if first_delay > 0:
        logger.info("Scheduler: first scrape in %.0f seconds (at %s)", first_delay, cfg.start_time)
        await asyncio.sleep(first_delay)

    interval = cfg.interval_minutes * 60

    while True:
        logger.info("Scheduler: triggering scrape for %s", cfg.day)
        try:
            scrape_id = _prepare_state_for_run("scheduled", day=cfg.day)
            _executor.submit(_run_scheduled_scrape, cfg.day, scrape_id)
        except HTTPException:
            logger.warning("Scheduler: scrape already in progress, skipping this interval")
        except Exception as exc:
            logger.error("Scheduler: error triggering scrape: %s", exc)

        await asyncio.sleep(interval)


# ════════════════════════════════════════════════════════════════
#  Driver management          (CLI: --install-drivers / --list-versions)
# ════════════════════════════════════════════════════════════════

@router.get("/drivers/versions")
async def list_driver_versions():
    """List available ChromeDriver versions.

    Mirrors the CLI's ``--list-versions`` flag.
    """
    installer = DriverInstaller()
    try:
        versions = installer.get_available_versions()
        # Extract just the version strings
        version_strings = [v["version"] for v in versions] if versions else []
        return {"versions": version_strings[:100], "total": len(version_strings)}
    except Exception as exc:
        raise HTTPException(500, f"Failed to fetch Chrome versions: {exc}")


@router.post("/drivers/install")
async def install_drivers(req: DriverInstallRequest):
    """Install browser drivers.

    Mirrors the CLI's ``--install-drivers [browser [version]]`` flag.
    Installs ChromeDriver (default) or GeckoDriver for Firefox.
    """
    if req.browser not in ("chrome", "firefox"):
        raise HTTPException(422, "browser must be 'chrome' or 'firefox'")

    try:
        installer = DriverInstaller()
        if req.browser == "firefox":
            result = installer.install_firefox_driver(version=req.version)
        else:
            result = installer.install_chrome_driver(version=req.version)
        return {"status": "ok", "browser": req.browser, "version": req.version or "latest",
                "message": f"{req.browser} driver installed", "details": str(result)}
    except Exception as exc:
        raise HTTPException(500, f"Driver installation failed: {exc}")


# ════════════════════════════════════════════════════════════════
#  Project initialization     (CLI: --init)
# ════════════════════════════════════════════════════════════════

@router.post("/initialize")
async def initialize_project(req: InitProjectRequest):
    """Initialize the project and install drivers.

    Mirrors the CLI's ``--init [browser [version]]`` flag. Ensures the
    output directories exist and the chosen driver is downloaded.
    """
    # Ensure output directories exist
    (PROJECT_ROOT / "output" / "json").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "output" / "logs").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "output" / "database").mkdir(parents=True, exist_ok=True)

    if req.browser not in ("chrome", "firefox"):
        raise HTTPException(422, "browser must be 'chrome' or 'firefox'")

    try:
        installer = DriverInstaller()
        version = req.version or ("138" if req.browser == "chrome" else None)
        if req.browser == "firefox":
            result = installer.install_firefox_driver(version=version)
        else:
            result = installer.install_chrome_driver(version=version)
        return {
            "status": "ok",
            "message": f"Project initialized with {req.browser}",
            "version": version or "latest",
            "details": str(result),
        }
    except Exception as exc:
        raise HTTPException(500, f"Initialization failed: {exc}")


# ════════════════════════════════════════════════════════════════
#  Results update            (CLI: --results-update)
# ════════════════════════════════════════════════════════════════

class ResultsUpdateRequest(BaseModel):
    json_file: str = Field(..., description="Path to JSON results file (absolute or relative to project root)")
    output: Optional[str] = Field(None, description="Optional output CSV path")


@router.post("/results/update")
async def update_results(req: ResultsUpdateRequest):
    """Update match results from a JSON file.

    Mirrors the CLI's ``--results-update JSON_FILE`` flag. Reads a JSON
    results file and writes an updated CSV with final scores.
    """
    json_path = Path(req.json_file)
    if not json_path.is_absolute():
        json_path = PROJECT_ROOT / json_path
    if not json_path.exists():
        raise HTTPException(404, f"File not found: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        raise HTTPException(400, f"Cannot read JSON file: {exc}")

    results = data.get("results", data.get("matches", []))
    if not results:
        raise HTTPException(400, "No results or matches found in JSON file")

    # Produce CSV output
    output_path = req.output or str(json_path.with_suffix(".csv"))
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            if results and isinstance(results[0], dict):
                writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
                writer.writeheader()
                writer.writerows(results)
            else:
                raise HTTPException(400, "Results entries must be dicts")
    except IOError as exc:
        raise HTTPException(500, f"Failed to write CSV: {exc}")

    logger.info("Results updated: %s → %s (%d entries)", json_path.name, output_path, len(results))
    return {
        "status": "ok",
        "input": str(json_path),
        "output": str(output_path),
        "entries": len(results),
    }


# ════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════

# ── Register API router (all routes under /api) ─────────────────
app.include_router(router)

def main() -> None:
    """Entry point — run the uvicorn server.

    Port from ``$PORT`` env (Railway) or 8080.
    Host from ``$HOST`` env or ``0.0.0.0``.
    """
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info("Starting API server on %s:%s ...", host, port)
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
