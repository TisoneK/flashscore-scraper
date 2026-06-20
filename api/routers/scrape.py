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


@router.post("/scrape/results/single")
async def trigger_single_result_scrape(req: dict):
    """Scrape the result for a SINGLE match by match_id.

    Opens one Flashscore match page, extracts the score + status, and
    pushes the result to the website immediately. Much faster than a
    full results scrape (which processes all matches).

    Body: { "match_id": "GzcUBljD" }

    Runs synchronously (not background) — the caller gets the result
    back in the response. Takes ~5-10 seconds (one page load + extract).
    """
    match_id = req.get("match_id")
    if not match_id or not isinstance(match_id, str):
        raise HTTPException(422, "match_id is required (string)")

    logger.info(f"[single-result] Scraping result for match {match_id}")

    # CRITICAL: thread-state reset — same as _run_scheduled_scrape / _run_results_scrape.
    # Without this, the retry_manager thinks the thread is shutting down and
    # immediately aborts with "Operation cancelled by shutdown".
    import threading
    threading.current_thread()._is_shutting_down = False

    try:
        from src.scraper import FlashscoreScraper
        from src.data.loader.results_data_loader import ResultsDataLoader
        from src.data.extractor.results_data_extractor import ResultsDataExtractor

        scraper = FlashscoreScraper(status_callback=None, progress_callback=None)
        try:
            scraper.initialize(status_callback=lambda msg: logger.debug(f"[single-result] {msg}"))
            results_loader = ResultsDataLoader(
                scraper.driver,
                selenium_utils=scraper.selenium_utils,
            )
            extractor = ResultsDataExtractor(results_loader)

            # Load the match summary page by match_id
            loaded = results_loader.load_match_summary_by_id(match_id, status_callback=None)
            if not loaded:
                return {"status": "error", "match_id": match_id, "message": "Failed to load match page"}

            elements = results_loader.get_elements()
            match_status = extractor.extract_match_status(elements, status_callback=None)
            home_score, away_score = extractor.extract_final_scores(elements, status_callback=None)

            result = {
                "match_id": match_id,
                "home_score": home_score,
                "away_score": away_score,
                "status": match_status or "UNKNOWN",
            }

            logger.info(
                f"[single-result] {match_id}: status='{match_status}', "
                f"scores={home_score}-{away_score}"
            )

            # Push to website immediately
            try:
                from webhook_utils import forward_results_to_website
                from api.env_config_store import get_env_config
                website_url = get_env_config("SCOREWISE_WEBSITE_URL")
                webhook_secret = get_env_config("SCOREWISE_WEBHOOK_SECRET")
                if website_url and webhook_secret:
                    forward_results_to_website(
                        results=[result],
                        website_url=website_url,
                        webhook_secret=webhook_secret,
                        date_str=None,
                        source="flashscore-scraper",
                    )
                    logger.info(f"[single-result] Pushed result for {match_id} to website")
                else:
                    logger.warning("[single-result] Website URL/secret not set — result not pushed")
            except Exception as push_err:
                logger.error(f"[single-result] Failed to push to website: {push_err}")

            return {
                "status": "ok",
                "match_id": match_id,
                "result": result,
                "message": f"Scraped: {match_status or 'unknown'}, {home_score}-{away_score}",
            }
        finally:
            scraper.close()
    except Exception as exc:
        logger.error(f"[single-result] Failed for {match_id}: {exc}")
        return {"status": "error", "match_id": match_id, "message": str(exc)}


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
