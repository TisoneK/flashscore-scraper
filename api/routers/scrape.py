"""scrape.py router

Scrape control endpoints — trigger, stop, and monitor scrapes.

Endpoints:
  POST /api/scrape           — trigger a scheduled scrape (Today / Tomorrow)
  POST /api/scrape/results   — trigger a results scrape for a specific date
  POST /api/scrape/stop      — request the running scrape to stop after current match
  GET  /api/scrape/progress  — real-time progress of the running scrape

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from api.schemas import ScrapeRequest, ScrapeResponse, ResultsScrapeRequest
from api.state import (
    _state,
    _state_lock,
    _executor,
    _prepare_state_for_run,
    _run_scheduled_scrape,
    _run_results_scrape,
)

logger = logging.getLogger("api_server")
router = APIRouter()


@router.post("/scrape", response_model=ScrapeResponse)
async def trigger_scrape(req: ScrapeRequest):
    """Scrape scheduled matches (Today / Tomorrow).

    Mirrors the CLI's **Scheduled Matches** mode.  The scraper runs on a
    background thread; poll ``GET /api/scrape/progress`` for live updates and
    ``GET /api/status`` for the final result.
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
        raise HTTPException(
            422, "Invalid date — must be a real date in DD.MM.YYYY format"
        )

    scrape_id = _prepare_state_for_run("results", date=req.date)
    _executor.submit(_run_results_scrape, req.date, scrape_id)

    return ScrapeResponse(
        status="accepted",
        message=f"Results scrape for {req.date} started (ID: {scrape_id})",
        scrape_id=scrape_id,
    )


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
    return {
        "status": "stop_requested",
        "message": "Scrape will stop after the current match",
    }


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
            "engine_forwarded": _state.engine_forwarded,
            "streamed_count": _state.streamed_count,
            "stream_failed_count": _state.stream_failed_count,
        }
