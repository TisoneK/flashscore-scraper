"""schedule.py router

Smart results scheduler — runs INSIDE the scraper process as a background
asyncio task. No external cron needed.

The scheduler continuously monitors match statuses and intelligently decides
when to scrape each match:

  SCHEDULED (hasn't started) → WAIT. Check again in 60s.
  LIVE (in progress)         → SCRAPE every 60s for live score updates.
                               Pause if queue is busy, resume when free.
  AWAITING (likely finished) → SCRAPE once for final score, then stop.
  FINAL/POSTPONED/CANCELLED  → DONE. Skip.

The loop runs forever (until the scraper restarts). It's smart about not
overloading the queue — if the queue has pending jobs, it waits for them
to drain before enqueuing more.

Endpoints:
  GET  /api/schedule           — return current scheduler state
  PUT  /api/schedule           — enable/disable + configure intervals
  POST /api/schedule/start     — start the scheduler
  POST /api/schedule/stop      — stop the scheduler
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("api_server")
router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Module-level handle to the running scheduler task
_results_scheduler_task: asyncio.Task | None = None
_results_scheduler_state: Dict[str, Any] = {
    "enabled": False,
    "running": False,
    "last_cycle": None,
    "matches_scraped": 0,
    "cycles_completed": 0,
    "current_action": "idle",
}

# ── Scheduled-matches scheduler ─────────────────────────────────────────
# Fetches matches + runs predictions on a fixed cadence (default every 6h),
# so the site no longer depends on a human clicking a manual scrape. Runs
# a "Today" scheduled scrape; single-match result scrapes automatically
# stand down while it runs (wait-for-batch), so there is no Chrome
# collision to schedule around.
_scheduled_scraper_task: asyncio.Task | None = None
_scheduled_scraper_state: Dict[str, Any] = {
    "enabled": False,
    "running": False,
    "interval_hours": 6.0,
    "day": "Today",
    "last_run": None,
    "next_run": None,
    "runs_triggered": 0,
    "current_action": "idle",
}


class ScheduleConfigRequest(BaseModel):
    enabled: bool = False
    interval_minutes: int = 60
    day: str = "Today"
    start_time: str | None = None
    # New: results scheduler config
    results_enabled: bool = True
    live_interval_seconds: int = 60  # how often to scrape live matches
    awaiting_interval_seconds: int = 30  # how often to check for newly finished matches
    idle_interval_seconds: int = 120  # how often to check when no matches are live
    # New: scheduled-matches scheduler config
    scheduled_enabled: bool = True  # fetch matches + predict on a cadence
    scheduled_interval_hours: float = 6.0  # how often to run the scheduled scrape
    scheduled_day: str = "Today"  # "Today" or "Tomorrow"


@router.get("/schedule")
async def get_schedule():
    """Return the current scheduler state."""
    return {
        "results_scheduler": _results_scheduler_state,
        "scheduled_scraper": _scheduled_scraper_state,
        "config": {
            "results_enabled": _results_scheduler_state.get("enabled", False),
            "live_interval_seconds": _results_scheduler_state.get("live_interval_seconds", 60),
            "awaiting_interval_seconds": _results_scheduler_state.get("awaiting_interval_seconds", 30),
            "idle_interval_seconds": _results_scheduler_state.get("idle_interval_seconds", 120),
            "scheduled_enabled": _scheduled_scraper_state.get("enabled", False),
            "scheduled_interval_hours": _scheduled_scraper_state.get("interval_hours", 6.0),
            "scheduled_day": _scheduled_scraper_state.get("day", "Today"),
        },
    }


def _persist_scheduler_config() -> None:
    """Write both schedulers' config to disk so they auto-resume on restart."""
    sched_path = PROJECT_ROOT / "output" / "scheduler_config.json"
    sched_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sched_path, "w") as f:
        json.dump({
            "results_enabled": _results_scheduler_state.get("enabled", False),
            "live_interval_seconds": _results_scheduler_state.get("live_interval_seconds", 60),
            "awaiting_interval_seconds": _results_scheduler_state.get("awaiting_interval_seconds", 30),
            "idle_interval_seconds": _results_scheduler_state.get("idle_interval_seconds", 120),
            "scheduled_enabled": _scheduled_scraper_state.get("enabled", False),
            "scheduled_interval_hours": _scheduled_scraper_state.get("interval_hours", 6.0),
            "scheduled_day": _scheduled_scraper_state.get("day", "Today"),
        }, f, indent=2)


@router.put("/schedule")
async def set_schedule(req: ScheduleConfigRequest):
    """Configure both schedulers (results + scheduled-matches)."""
    global _results_scheduler_state, _scheduled_scraper_state

    _results_scheduler_state["enabled"] = req.results_enabled
    _results_scheduler_state["live_interval_seconds"] = req.live_interval_seconds
    _results_scheduler_state["awaiting_interval_seconds"] = req.awaiting_interval_seconds
    _results_scheduler_state["idle_interval_seconds"] = req.idle_interval_seconds

    # Clamp the scheduled interval to a sane range (30 min .. 24 h).
    _scheduled_scraper_state["enabled"] = req.scheduled_enabled
    _scheduled_scraper_state["interval_hours"] = max(0.5, min(24.0, req.scheduled_interval_hours))
    _scheduled_scraper_state["day"] = req.scheduled_day if req.scheduled_day in ("Today", "Tomorrow") else "Today"

    _persist_scheduler_config()

    # Start or stop each scheduler independently
    if req.results_enabled:
        await start_results_scheduler()
    else:
        await stop_results_scheduler()

    if req.scheduled_enabled:
        await start_scheduled_scraper()
    else:
        await stop_scheduled_scraper()

    logger.info("Results scheduler config updated: enabled=%s", req.results_enabled)
    return {"status": "ok", "config": _results_scheduler_state}


@router.post("/schedule/start")
async def start_results_scheduler():
    """Start the background results scheduler loop."""
    global _results_scheduler_task, _results_scheduler_state

    if _results_scheduler_task is not None and not _results_scheduler_task.done():
        return {"status": "already_running"}

    _results_scheduler_state["enabled"] = True
    _results_scheduler_state["running"] = True
    _results_scheduler_task = asyncio.create_task(_results_scheduler_loop())

    logger.info("[results-scheduler] Started")
    return {"status": "started"}


@router.post("/schedule/stop")
async def stop_results_scheduler():
    """Stop the background results scheduler loop."""
    global _results_scheduler_task, _results_scheduler_state

    if _results_scheduler_task is not None and not _results_scheduler_task.done():
        _results_scheduler_task.cancel()
        try:
            await asyncio.wait_for(_results_scheduler_task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

    _results_scheduler_task = None
    _results_scheduler_state["enabled"] = False
    _results_scheduler_state["running"] = False
    _results_scheduler_state["current_action"] = "stopped"

    logger.info("[results-scheduler] Stopped")
    return {"status": "stopped"}


@router.post("/schedule/scheduled/start")
async def start_scheduled_scraper():
    """Start the background scheduled-matches loop (fetch matches + predict)."""
    global _scheduled_scraper_task, _scheduled_scraper_state

    if _scheduled_scraper_task is not None and not _scheduled_scraper_task.done():
        return {"status": "already_running"}

    _scheduled_scraper_state["enabled"] = True
    _scheduled_scraper_state["running"] = True
    _scheduled_scraper_task = asyncio.create_task(_scheduled_scraper_loop())

    logger.info(
        "[scheduled-scraper] Started (every %.2fh, day=%s)",
        _scheduled_scraper_state.get("interval_hours", 6.0),
        _scheduled_scraper_state.get("day", "Today"),
    )
    return {"status": "started"}


@router.post("/schedule/scheduled/stop")
async def stop_scheduled_scraper():
    """Stop the background scheduled-matches loop."""
    global _scheduled_scraper_task, _scheduled_scraper_state

    if _scheduled_scraper_task is not None and not _scheduled_scraper_task.done():
        _scheduled_scraper_task.cancel()
        try:
            await asyncio.wait_for(_scheduled_scraper_task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

    _scheduled_scraper_task = None
    _scheduled_scraper_state["enabled"] = False
    _scheduled_scraper_state["running"] = False
    _scheduled_scraper_state["current_action"] = "stopped"

    logger.info("[scheduled-scraper] Stopped")
    return {"status": "stopped"}


def _trigger_scheduled_scrape(day: str) -> Optional[str]:
    """Kick off a scheduled (Today/Tomorrow) scrape on the batch executor.

    Returns the scrape_id, or None if a scrape is already in progress (the
    scraper runs one batch at a time — we skip this cycle rather than error).
    """
    from api.state import _prepare_state_for_run, _executor, _run_scheduled_scrape

    try:
        scrape_id = _prepare_state_for_run("scheduled", day=day)
    except HTTPException:
        return None  # already busy — skip this cycle
    _executor.submit(_run_scheduled_scrape, day, scrape_id, False)
    return scrape_id


async def _scheduled_scraper_loop():
    """Fetch matches + run predictions on a fixed cadence (default 6h).

    Removes the dependence on a human clicking a manual scrape. Each cycle
    triggers one "Today" (or "Tomorrow") scheduled scrape; if a scrape is
    already running it skips this cycle. Single-match result scrapes stand
    down while the batch runs (wait-for-batch), so there is no collision to
    schedule around.
    """
    global _scheduled_scraper_state

    logger.info("[scheduled-scraper] Loop started")
    # Run once shortly after start so a fresh deploy has data without waiting
    # a full interval, then settle into the cadence.
    first_delay = 30
    while True:
        try:
            _scheduled_scraper_state["current_action"] = "waiting"
            interval_h = _scheduled_scraper_state.get("interval_hours", 6.0)
            wait_s = first_delay if first_delay is not None else interval_h * 3600
            next_run = datetime.now(timezone.utc) + timedelta(seconds=wait_s)
            _scheduled_scraper_state["next_run"] = next_run.isoformat()
            await asyncio.sleep(wait_s)
            first_delay = None  # subsequent cycles use the full interval

            day = _scheduled_scraper_state.get("day", "Today")
            _scheduled_scraper_state["current_action"] = "triggering_scrape"
            scrape_id = _trigger_scheduled_scrape(day)
            if scrape_id:
                _scheduled_scraper_state["last_run"] = datetime.now(timezone.utc).isoformat()
                _scheduled_scraper_state["runs_triggered"] += 1
                logger.info(
                    "[scheduled-scraper] Triggered %s scrape %s (run #%d)",
                    day, scrape_id, _scheduled_scraper_state["runs_triggered"],
                )
            else:
                logger.info("[scheduled-scraper] A scrape is already running — skipping this cycle")

        except asyncio.CancelledError:
            logger.info("[scheduled-scraper] Loop cancelled — shutting down")
            _scheduled_scraper_state["running"] = False
            _scheduled_scraper_state["current_action"] = "stopped"
            break
        except Exception as e:
            logger.error("[scheduled-scraper] Unexpected error: %s", e)
            _scheduled_scraper_state["current_action"] = "error"
            await asyncio.sleep(300)  # back off 5 min on errors


async def _results_scheduler_loop():
    """Background loop that intelligently scrapes results based on match status.

    Logic:
    1. Fetch match statuses from the website (/api/predictions/exists?with_priority=true)
    2. For each match that's LIVE or AWAITING_RESULT:
       a. If queue is not busy → enqueue a single-match scrape
       b. If queue is busy → wait for it to drain
    3. Wait based on what we found:
       - Live matches → short wait (60s) for frequent updates
       - Only awaiting → medium wait (30s)
       - Nothing to do → long wait (120s)
    4. Repeat forever

    The loop is self-throttling: it won't enqueue more than the queue can handle,
    and it backs off when there's nothing to scrape.
    """
    global _results_scheduler_state

    logger.info("[results-scheduler] Loop started")
    _results_scheduler_state["cycles_completed"] = 0
    _results_scheduler_state["matches_scraped"] = 0

    while True:
        try:
            _results_scheduler_state["current_action"] = "checking_matches"
            _results_scheduler_state["last_cycle"] = datetime.now(timezone.utc).isoformat()

            # ── Fetch match statuses from website ────────────────────────
            website_url = _get_website_url()
            if not website_url:
                logger.warning("[results-scheduler] No website URL configured — waiting 60s")
                _results_scheduler_state["current_action"] = "no_website_url"
                await asyncio.sleep(60)
                continue

            match_duration = _get_match_duration_minutes()
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        f"{website_url.rstrip('/')}/api/predictions/exists"
                        f"?with_priority=true&match_duration={match_duration}"
                    )
                if not resp.is_success:
                    logger.warning(f"[results-scheduler] Website returned {resp.status_code} — waiting 60s")
                    _results_scheduler_state["current_action"] = "website_error"
                    await asyncio.sleep(60)
                    continue
                data = resp.json()
            except Exception as e:
                logger.warning(f"[results-scheduler] Failed to fetch match statuses: {e} — waiting 60s")
                _results_scheduler_state["current_action"] = "fetch_error"
                await asyncio.sleep(60)
                continue

            by_priority = data.get("by_priority", {})
            high_ids = [m["match_id"] for m in by_priority.get("high", [])]
            medium_ids = [m["match_id"] for m in by_priority.get("medium", [])]
            counts = data.get("priority_counts", {})

            live_count = counts.get("medium", 0)
            awaiting_count = counts.get("high", 0)
            total_to_scrape = live_count + awaiting_count

            logger.info(
                f"[results-scheduler] Status: {live_count} live, {awaiting_count} awaiting, "
                f"{counts.get('done', 0)} done"
            )

            if total_to_scrape == 0:
                _results_scheduler_state["current_action"] = "idle"
                wait = _results_scheduler_state.get("idle_interval_seconds", 120)
                await asyncio.sleep(wait)
                continue

            # ── Check queue status ────────────────────────────────────────
            scraper_base = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
            if not scraper_base:
                # Running locally — use the PORT env var or default to 8000
                port = os.environ.get("PORT", "8000")
                scraper_base = f"http://localhost:{port}"
            else:
                scraper_base = f"https://{scraper_base}"

            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    qresp = await client.get(f"{scraper_base}/api/scrape/results/single/status")
                queue_data = qresp.json() if qresp.is_success else {}
            except Exception:
                queue_data = {}

            queue_running = queue_data.get("running_count", 0)
            queue_queued = queue_data.get("queued_count", 0)
            queue_paused = queue_data.get("paused", False)

            if queue_paused:
                logger.info("[results-scheduler] Queue is paused — waiting 30s")
                _results_scheduler_state["current_action"] = "queue_paused"
                await asyncio.sleep(30)
                continue

            # ── Enqueue matches that need scraping ───────────────────────
            # Priority: HIGH (awaiting) first, then MEDIUM (live)
            # But don't flood the queue — only enqueue if queue isn't too full
            max_queue_depth = 5  # don't enqueue if more than 5 already waiting
            matches_to_enqueue = (high_ids + medium_ids)

            if queue_queued >= max_queue_depth:
                logger.info(
                    f"[results-scheduler] Queue full ({queue_queued} queued) — waiting for drain"
                )
                _results_scheduler_state["current_action"] = "waiting_for_queue"
                await asyncio.sleep(15)
                continue

            enqueued_this_cycle = 0
            for match_id in matches_to_enqueue:
                # Don't re-enqueue if already running or queued
                running_ids = {j.get("match_id") for j in queue_data.get("running", [])}
                queued_ids = {j.get("match_id") for j in queue_data.get("queued", [])}
                if match_id in running_ids or match_id in queued_ids:
                    continue

                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        resp = await client.post(
                            f"{scraper_base}/api/scrape/results/single",
                            json={"match_id": match_id},
                        )
                    if resp.is_success:
                        enqueued_this_cycle += 1
                        _results_scheduler_state["matches_scraped"] += 1
                except Exception as e:
                    logger.debug(f"[results-scheduler] Failed to enqueue {match_id}: {e}")

            logger.info(
                f"[results-scheduler] Enqueued {enqueued_this_cycle} matches this cycle "
                f"(queue: {queue_running} running, {queue_queued} queued)"
            )

            _results_scheduler_state["cycles_completed"] += 1

            # ── Wait based on what we found ──────────────────────────────
            if live_count > 0:
                # Live matches → short wait for frequent updates
                wait = _results_scheduler_state.get("live_interval_seconds", 60)
                _results_scheduler_state["current_action"] = f"monitoring_{live_count}_live"
            else:
                # Only awaiting → medium wait
                wait = _results_scheduler_state.get("awaiting_interval_seconds", 30)
                _results_scheduler_state["current_action"] = f"checking_{awaiting_count}_awaiting"

            await asyncio.sleep(wait)

        except asyncio.CancelledError:
            logger.info("[results-scheduler] Loop cancelled — shutting down")
            _results_scheduler_state["running"] = False
            _results_scheduler_state["current_action"] = "stopped"
            break
        except Exception as e:
            logger.error(f"[results-scheduler] Unexpected error: {e}")
            _results_scheduler_state["current_action"] = "error"
            await asyncio.sleep(30)  # back off on errors


def _get_website_url() -> str:
    """Get the website URL from env-config store or env var."""
    try:
        from api.env_config_store import get_env_config
        return get_env_config("SCOREWISE_WEBSITE_URL")
    except ImportError:
        return os.environ.get("SCOREWISE_WEBSITE_URL", "")


def _get_match_duration_minutes() -> int:
    """Get the match duration threshold from env-config store."""
    try:
        from api.env_config_store import get_env_config
        val = get_env_config("RESULTS_MATCH_DURATION_MINUTES")
        return int(val) if val else 170
    except Exception:
        return 170


# ── Auto-start on import (if enabled in config) ─────────────────────────
def _try_autostart():
    """Auto-start both schedulers on boot.

    Defaults BOTH to enabled when there is no saved config, so a fresh deploy
    runs autonomously with no manual trigger (the whole point of this
    feature). A saved scheduler_config.json overrides the defaults, so an
    admin who turned a scheduler off keeps it off across restarts.
    """
    try:
        config: Dict[str, Any] = {}
        sched_path = PROJECT_ROOT / "output" / "scheduler_config.json"
        if sched_path.exists():
            with open(sched_path, "r") as f:
                config = json.load(f)

        # Results scheduler (live/awaiting) — default ON.
        _results_scheduler_state["enabled"] = config.get("results_enabled", True)
        _results_scheduler_state["live_interval_seconds"] = config.get("live_interval_seconds", 60)
        _results_scheduler_state["awaiting_interval_seconds"] = config.get("awaiting_interval_seconds", 30)
        _results_scheduler_state["idle_interval_seconds"] = config.get("idle_interval_seconds", 120)

        # Scheduled-matches scheduler (6h fetch) — default ON.
        _scheduled_scraper_state["enabled"] = config.get("scheduled_enabled", True)
        _scheduled_scraper_state["interval_hours"] = config.get("scheduled_interval_hours", 6.0)
        _scheduled_scraper_state["day"] = config.get("scheduled_day", "Today")

        if _results_scheduler_state["enabled"] or _scheduled_scraper_state["enabled"]:
            logger.info(
                "[scheduler] Auto-starting (results=%s, scheduled=%s @ %.2fh)",
                _results_scheduler_state["enabled"],
                _scheduled_scraper_state["enabled"],
                _scheduled_scraper_state["interval_hours"],
            )
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_start_after_delay())
            else:
                loop.run_until_complete(_start_after_delay())
    except Exception as e:
        logger.warning(f"[scheduler] Auto-start check failed: {e}")


async def _start_after_delay():
    """Wait a bit for the server to fully start, then begin the enabled loops."""
    await asyncio.sleep(10)  # let the server warm up
    global _results_scheduler_task, _results_scheduler_state
    global _scheduled_scraper_task, _scheduled_scraper_state

    if _results_scheduler_state.get("enabled") and (
        _results_scheduler_task is None or _results_scheduler_task.done()
    ):
        _results_scheduler_state["running"] = True
        _results_scheduler_task = asyncio.create_task(_results_scheduler_loop())
        logger.info("[results-scheduler] Auto-started after 10s delay")

    if _scheduled_scraper_state.get("enabled") and (
        _scheduled_scraper_task is None or _scheduled_scraper_task.done()
    ):
        _scheduled_scraper_state["running"] = True
        _scheduled_scraper_task = asyncio.create_task(_scheduled_scraper_loop())
        logger.info("[scheduled-scraper] Auto-started after 10s delay")
