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
    _results_state,
    _results_state_lock,
    _results_executor,
    _prepare_state_for_run,
    _prepare_results_state_for_run,
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

    # Use separate results state + executor so this doesn't block or get
    # blocked by scheduled scrapes. Multiple results scrapes queue on the
    # _results_executor (max_workers=1) without affecting the main scraper.
    scrape_id = _prepare_results_state_for_run(req.date)
    _results_executor.submit(_run_results_scrape, req.date, scrape_id)

    return ScrapeResponse(
        status="accepted",
        message=f"Results scrape for {req.date} started (ID: {scrape_id})",
        scrape_id=scrape_id,
    )


@router.post("/scrape/stop")
async def stop_scrape():
    """Request the running scrape(s) to stop after the current match.

    Stops BOTH scheduled and results scrapes if either is running.
    The scraper checks this flag between matches; the current match
    finishes before the scrape halts cooperatively.
    """
    stopped_any = False

    with _state_lock:
        if _state.busy:
            _state.stop_requested = True
            stopped_any = True

    with _results_state_lock:
        if _results_state.busy:
            _results_state.stop_requested = True
            stopped_any = True

    if not stopped_any:
        raise HTTPException(409, "No scrape is currently running")

    logger.info("Stop requested — scrape(s) will halt after current match")
    return {
        "status": "stop_requested",
        "message": "Scrape(s) will stop after the current match",
    }


@router.get("/scrape/progress")
async def get_scrape_progress():
    """Return real-time progress of the currently running scrape(s).

    Returns both scheduled and results scrape progress so the dashboard
    can show both if they're running concurrently.
    """
    with _state_lock:
        scheduled = {
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

    with _results_state_lock:
        results = {
            "busy": _results_state.busy,
            "scrape_id": _results_state.scrape_id,
            "scrape_type": _results_state.scrape_type,
            "date": _results_state.date,
            "started_at": _results_state.started_at,
            "current_match_index": _results_state.current_match_index,
            "total_matches": _results_state.total_matches,
            "progress_message": _results_state.progress_message,
            "status_message": _results_state.status_message,
            "stop_requested": _results_state.stop_requested,
            "error": _results_state.error,
        }

    return {
        "scheduled": scheduled,
        "results": results,
        # Backwards-compat: also return top-level fields from whichever is busy
        "busy": scheduled["busy"] or results["busy"],
        "scrape_id": scheduled["scrape_id"] if scheduled["busy"] else results["scrape_id"],
        "scrape_type": scheduled["scrape_type"] if scheduled["busy"] else results["scrape_type"],
        "day": scheduled["day"],
        "date": results["date"] if results["busy"] else scheduled["date"],
        "started_at": scheduled["started_at"] if scheduled["busy"] else results["started_at"],
        "current_match_index": scheduled["current_match_index"] if scheduled["busy"] else results["current_match_index"],
        "total_matches": scheduled["total_matches"] if scheduled["busy"] else results["total_matches"],
        "complete_matches": scheduled["complete_matches"],
        "incomplete_matches": scheduled["incomplete_matches"],
        "progress_message": scheduled["progress_message"] if scheduled["busy"] else results["progress_message"],
        "status_message": scheduled["status_message"] if scheduled["busy"] else results["status_message"],
        "stop_requested": scheduled["stop_requested"] or results["stop_requested"],
        "error": scheduled["error"] or results["error"],
        "engine_forwarded": scheduled.get("engine_forwarded", False),
        "streamed_count": scheduled.get("streamed_count", 0),
        "stream_failed_count": scheduled.get("stream_failed_count", 0),
    }
