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
    _executor.submit(_run_scheduled_scrape, req.day, scrape_id, req.force)

    return ScrapeResponse(
        status="accepted",
        message=f"Scrape for {req.day} started (ID: {scrape_id})"
        + (" — FORCE mode: re-scraping already-processed matches" if req.force else ""),
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

    Enqueues a job in the single-scrape queue. If the queue isn't full
    (under max_workers), the job starts immediately. Otherwise it waits
    in the queue until a worker is free.

    If the same match is already queued or running, returns that job's
    status instead of creating a duplicate.

    Body: { "match_id": "GzcUBljD" }
    Returns: { job_id, match_id, status, position, paused }
    """
    match_id = req.get("match_id")
    if not match_id or not isinstance(match_id, str):
        raise HTTPException(422, "match_id is required (string)")

    from api.scrape_queue import _scrape_queue
    result = _scrape_queue.enqueue(match_id, _do_single_result_scrape)
    return result


@router.get("/scrape/results/single/status")
async def get_single_scrape_status():
    """Return the current state of the single-match scrape queue.

    Shows running jobs, queued jobs, recent completions, errors, and
    whether the queue is paused.
    """
    from api.scrape_queue import _scrape_queue
    return _scrape_queue.get_status()


@router.get("/scrape/results/single/{job_id}")
async def get_single_scrape_job(job_id: str):
    """Get the status of a specific scrape job."""
    from api.scrape_queue import _scrape_queue
    job = _scrape_queue.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    return job


@router.post("/scrape/results/single/pause")
async def pause_single_scrape():
    """Pause the scrape queue — running jobs finish, queued jobs wait."""
    from api.scrape_queue import _scrape_queue
    _scrape_queue.pause()
    return {"status": "paused", "message": "Queue paused — running jobs will finish, new jobs will wait"}


@router.post("/scrape/results/single/resume")
async def resume_single_scrape():
    """Resume the scrape queue — queued jobs start running."""
    from api.scrape_queue import _scrape_queue
    _scrape_queue.resume()
    return {"status": "resumed", "message": "Queue resumed — queued jobs are starting"}


@router.post("/scrape/results/single/cancel/{job_id}")
async def cancel_single_scrape(job_id: str):
    """Cancel a queued scrape job (can't cancel running jobs)."""
    from api.scrape_queue import _scrape_queue
    cancelled = _scrape_queue.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(409, f"Job {job_id} is not queued (may be running or already done)")
    return {"status": "cancelled", "job_id": job_id}


def _wait_for_batch_idle(match_id: str, max_wait_s: int = 1800) -> bool:
    """Block until no batch scrape (scheduled or results) is running.

    A batch run owns a Chrome instance. Launching a second browser beside it
    is what OOM-kills Chrome on small containers ("session not created:
    Chrome instance exited"). Single jobs run on a worker pool, so blocking
    here simply keeps them queued until the container has memory to spare.
    """
    import time
    waited = 0
    while waited < max_wait_s:
        with _state_lock:
            scheduled_busy = _state.busy
        with _results_state_lock:
            results_busy = _results_state.busy
        if not scheduled_busy and not results_busy:
            return True
        if waited == 0:
            logger.info(
                f"[single-result] {match_id}: batch scrape in progress — "
                "waiting for Chrome to free up before starting"
            )
        time.sleep(5)
        waited += 5
    return False


def _other_single_jobs_running() -> bool:
    """True if any single-scrape job besides the calling thread's is running."""
    try:
        from api.scrape_queue import _scrape_queue
        status = _scrape_queue.get_status()
        return len(status.get("running", [])) > 1
    except Exception:
        return True  # unknown → assume yes, don't kill anything


def _kill_zombie_chrome(match_id: str) -> None:
    """Best-effort cleanup of leftover Chrome/chromedriver processes.

    Called ONLY when no batch scrape and no other single job is running —
    any chrome process alive at that point is a leftover from a crashed run
    holding the memory that just prevented a new session from starting.
    """
    import subprocess
    logger.warning(f"[single-result] {match_id}: killing zombie Chrome processes before retry")
    for pattern in ("chrome", "chromedriver"):
        try:
            subprocess.run(["pkill", "-9", "-f", pattern], timeout=5, capture_output=True)
        except Exception:
            pass


def _do_single_result_scrape(match_id: str) -> dict:
    """Synchronous worker — runs on a thread pool. Does the actual Selenium work.

    Each call gets its own FlashscoreScraper + Chrome browser instance, so
    multiple calls can run in parallel without sharing state.
    """
    # CRITICAL: thread-state reset — same as _run_scheduled_scrape / _run_results_scrape.
    # Without this, the retry_manager thinks the thread is shutting down and
    # immediately aborts with "Operation cancelled by shutdown".
    import threading
    import time
    threading.current_thread()._is_shutting_down = False

    # Never launch a Chrome next to a running batch scrape — that memory
    # contention is the root cause of "session not created: Chrome instance
    # exited" on Railway. Jobs wait (queued) until the batch finishes.
    if not _wait_for_batch_idle(match_id):
        return {
            "status": "error",
            "match_id": match_id,
            "message": "A batch scrape has been running for over 30 minutes — try again when it finishes.",
        }

    try:
        from src.scraper import FlashscoreScraper
        from src.data.loader.results_data_loader import ResultsDataLoader
        from src.data.extractor.results_data_extractor import ResultsDataExtractor

        scraper = FlashscoreScraper(status_callback=None, progress_callback=None)
        try:
            try:
                scraper.initialize(status_callback=lambda msg: logger.debug(f"[single-result] {msg}"))
            except Exception as init_exc:
                # Chrome failed to start (usually memory exhaustion or a
                # zombie browser from a crashed run). Clean up and retry ONCE.
                if "session not created" not in str(init_exc).lower():
                    raise
                logger.warning(f"[single-result] {match_id}: Chrome session failed to start — {init_exc}")
                try:
                    scraper.close()
                except Exception:
                    pass
                if not _other_single_jobs_running():
                    _kill_zombie_chrome(match_id)
                time.sleep(5)
                scraper = FlashscoreScraper(status_callback=None, progress_callback=None)
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
    Also pauses the single-scrape queue so queued jobs wait.
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

    # Also pause the single-scrape queue
    from api.scrape_queue import _scrape_queue
    queue_was_active = _scrape_queue.get_status()
    if queue_was_active["running_count"] > 0 or queue_was_active["queued_count"] > 0:
        _scrape_queue.pause()
        stopped_any = True

    if not stopped_any:
        raise HTTPException(409, "No scrape is currently running")

    logger.info("Stop requested — scrape(s) will halt after current match, queue paused")
    return {
        "status": "stop_requested",
        "message": "Scrape(s) will stop after current match. Single-scrape queue paused.",
    }


@router.post("/scrape/kill")
async def kill_all_scrapes():
    """Kill ALL active scrapes immediately — the nuclear option.

    Unlike /scrape/stop (which waits for the current match to finish),
    this endpoint:
      1. Sets stop_requested on scheduled + results scrapes
      2. Kills ALL single-scrape queue jobs (queued AND running)
      3. Pauses the queue so no new jobs start
      4. Kills any zombie Chrome/chromedriver processes

    Use this when the scraper is stuck and /scrape/stop isn't enough.
    After killing, the queue is paused — call /scrape/results/single/resume
    to restart it.
    """
    import subprocess
    killed = {
        "scheduled_stopped": False,
        "results_stopped": False,
        "queue_killed": {"killed_queued": 0, "killed_running": 0},
        "chrome_processes_killed": 0,
    }

    # 1. Stop scheduled + results scrapes
    with _state_lock:
        if _state.busy:
            _state.stop_requested = True
            killed["scheduled_stopped"] = True

    with _results_state_lock:
        if _results_state.busy:
            _results_state.stop_requested = True
            killed["results_stopped"] = True

    # 2. Kill all single-scrape queue jobs
    from api.scrape_queue import _scrape_queue
    killed["queue_killed"] = _scrape_queue.kill_all()

    # 3. Kill zombie Chrome processes
    try:
        result = subprocess.run(
            ["pkill", "-9", "-f", "chrome"],
            timeout=5,
            capture_output=True,
        )
        killed["chrome_processes_killed"] = result.returncode == 0
    except Exception:
        pass
    try:
        subprocess.run(["pkill", "-9", "-f", "chromedriver"], timeout=5, capture_output=True)
    except Exception:
        pass

    logger.warning(
        f"[kill] Killed all — scheduled={killed['scheduled_stopped']}, "
        f"results={killed['results_stopped']}, "
        f"queue={killed['queue_killed']}, "
        f"chrome_killed={killed['chrome_processes_killed']}"
    )

    return {
        "status": "killed",
        "message": "All scrapes killed. Queue is paused. Chrome processes terminated.",
        "details": killed,
        "next_step": "Call POST /scrape/results/single/resume to restart the queue.",
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
