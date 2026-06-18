"""schedule.py router

Recurring scrape scheduler — auto-trigger scrapes on a fixed interval.

Endpoints:
  GET /api/schedule  — return the current recurring scrape schedule
  PUT /api/schedule  — configure recurring scraping (enable + interval + day + start_time)

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import ScheduleConfigRequest
from api.state import _executor, _prepare_state_for_run, _run_scheduled_scrape

# PROJECT_ROOT is the scraper repo root (parent of the api/ package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger("api_server")
router = APIRouter()

# Module-level handle to the running schedule task (so we can cancel + restart it)
_schedule_task: asyncio.Task | None = None


@router.get("/schedule")
async def get_schedule():
    """Return the current recurring scrape schedule."""
    sched_path = PROJECT_ROOT / "src" / "cli" / "cli_settings.json"
    defaults = {
        "enabled": False,
        "interval_minutes": 60,
        "day": "Today",
        "start_time": None,
    }
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

    logger.info(
        "Schedule updated: enabled=%s, interval=%d min",
        req.enabled,
        req.interval_minutes,
    )
    return {"status": "ok", "schedule": payload}


async def _run_schedule_loop(cfg: ScheduleConfigRequest) -> None:
    """Background coroutine that triggers scrapes on a schedule."""
    first_delay: float = 0.0
    if cfg.start_time:
        try:
            now = datetime.now()
            parts = cfg.start_time.split(":")
            target = now.replace(
                hour=int(parts[0]),
                minute=int(parts[1]),
                second=0,
                microsecond=0,
            )
            if target <= now:
                target += timedelta(days=1)
            first_delay = (target - now).total_seconds()
        except Exception:
            first_delay = 0.0

    if first_delay > 0:
        logger.info(
            "Scheduler: first scrape in %.0f seconds (at %s)",
            first_delay,
            cfg.start_time,
        )
        await asyncio.sleep(first_delay)

    interval = cfg.interval_minutes * 60

    while True:
        logger.info("Scheduler: triggering scrape for %s", cfg.day)
        try:
            scrape_id = _prepare_state_for_run("scheduled", day=cfg.day)
            _executor.submit(_run_scheduled_scrape, cfg.day, scrape_id)
        except HTTPException:
            logger.warning(
                "Scheduler: scrape already in progress, skipping this interval"
            )
        except Exception as exc:
            logger.error("Scheduler: error triggering scrape: %s", exc)

        await asyncio.sleep(interval)
