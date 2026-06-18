"""state.py

Shared mutable state for the scraper API.

Contains:
  - _ScraperState — progress / outcome / stop flag for the current scrape
  - _state — singleton instance
  - _state_lock — guards all _state mutations
  - _executor — single-worker ThreadPoolExecutor for scrape runs
  - _stream_executor — 3-worker pool for per-match streaming to engine
  - _scrape_history — list of finished-run summaries (for /api/history)
  - _stream_match_to_engine — per-match streaming helper
  - _run_scheduled_scrape — background runner for FlashscoreScraper.scrape()
  - _run_results_scrape — background runner for FlashscoreScraper.scrape_results()
  - _prepare_state_for_run — atomic reset + scrape_id generation

Extracted from api_server.py during the api modularization.

CRITICAL: the thread-state reset at the top of _run_scheduled_scrape and
_run_results_scrape is load-bearing. See the inline comment for the full
rationale. Do not remove.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from src.scraper import FlashscoreScraper, get_ddmmyy_date
from src.reporting import CallbackReporter
from webhook_utils import post_to_webhook, forward_matches_to_engine
from api.env_config_store import get_env_config

logger = logging.getLogger("api_server")

# ── Thread-safe shared state ─────────────────────────────────────────
_state_lock = threading.Lock()
_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)
# Dedicated pool for streaming individual matches to the engine as they
# complete — keeps the scraper thread moving without waiting on HTTP.
_stream_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=3)

# Scrape run history (in-memory, most-recent-first when served)
_scrape_history: List[Dict[str, Any]] = []


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
        self.engine_forwarded: bool = False

        # Per-match streaming stats
        self.streamed_count: int = 0
        self.stream_failed_count: int = 0


_state: _ScraperState = _ScraperState()


# ════════════════════════════════════════════════════════════════
#  Background scraper runners (threaded, with live callbacks)
# ════════════════════════════════════════════════════════════════

def _stream_match_to_engine(match_id: str, match: Optional[dict], scrape_id: str) -> None:
    """Stream a single finalized match to the engine in real time.

    Runs on the streaming executor so the scraper thread can continue
    processing the next match without waiting for the engine HTTP round-trip.
    Failures are logged but never crash the scrape; the batch POST at the
    end of the scrape acts as a safety net for any matches that failed
    to stream individually.
    """
    if match is None:
        return

    webhook_url = get_env_config("SCOREWISE_WEBHOOK_URL")
    api_key = get_env_config("SCOREWISE_API_KEY")
    if not webhook_url:
        return

    try:
        logger.info("[%s] Streaming match %s to engine ...", scrape_id, match_id)
        ok = forward_matches_to_engine([match], webhook_url, api_key, timeout=15)
        with _state_lock:
            if ok:
                _state.streamed_count += 1
                logger.info(
                    "[%s] Streamed match %s to engine (total streamed: %d)",
                    scrape_id,
                    match_id,
                    _state.streamed_count,
                )
            else:
                _state.stream_failed_count += 1
                logger.warning(
                    "[%s] Failed to stream match %s to engine "
                    "(will be covered by batch POST at end of scrape)",
                    scrape_id,
                    match_id,
                )
    except Exception as e:
        with _state_lock:
            _state.stream_failed_count += 1
        logger.error("[%s] Error streaming match %s: %s", scrape_id, match_id, e)


def _run_scheduled_scrape(day: str, scrape_id: str) -> None:
    """Run FlashscoreScraper.scrape() on a background thread.

    All progress / status callbacks update ``_state`` under the lock so that
    ``GET /scrape/progress`` and ``GET /status`` reflect live state.
    """
    global _state

    # ────────────────────────────────────────────────────────────────
    # CRITICAL: thread-state reset. DO NOT REMOVE THESE LINES.
    #
    # FlashscoreScraper.close() (in src/scraper.py) sets
    #   threading.current_thread()._is_shutting_down = True
    # as part of its cleanup, so retry_manager can abort in-flight
    # network operations during a real shutdown.
    #
    # But api_server uses a ThreadPoolExecutor(max_workers=1), so the
    # SAME worker thread is reused for every scrape. Without clearing
    # the flag at the start of the next run, the worker is still
    # marked as "shutting down" from the previous run's cleanup, and
    # retry_manager.retry_network_operation() immediately raises
    #   RuntimeError("Operation cancelled by shutdown")
    # the moment the new scrape tries its first network call.
    #
    # Symptom of the bug: every scrape dies ~3s in with
    # "Operation cancelled by shutdown", 0 matches scraped.
    #
    # History: this fix was added in commit 5a7a594 (Jun 15),
    # accidentally removed in commit bf1bf6f (Jun 15) during a
    # refactor, then restored in commit 16d39a7 after the regression
    # was discovered. If you're refactoring this function, keep the
    # clear below — it is load-bearing.
    # ────────────────────────────────────────────────────────────────
    with _state_lock:
        _state.stop_requested = False
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

    def match_finalized_cb(match_id: str, match: Optional[dict] = None) -> None:
        """Per-match callback: stream the finalized match to the engine immediately.

        Submitted to the streaming executor so the scraper thread is not blocked
        by the HTTP round-trip. The batch POST at the end of the scrape serves as
        a fallback for any matches that failed to stream individually.
        """
        try:
            _stream_executor.submit(_stream_match_to_engine, match_id, match, scrape_id)
        except Exception as e:
            logger.error(
                "[%s] Could not submit streaming task for match %s: %s",
                scrape_id,
                match_id,
                e,
            )

    scraper = FlashscoreScraper(
        status_callback=status_cb,
        progress_callback=progress_cb,
        reporter=CallbackReporter(
            status_callback=status_cb,
            progress_callback=progress_cb,
            match_finalized_callback=match_finalized_cb,
        ),
    )
    try:
        result = scraper.scrape(
            day=day,
            progress_callback=progress_cb,
            status_callback=status_cb,
            stop_callback=stop_cb,
        )
        with _state_lock:
            _state.result = result
            _state.complete_matches = result.get("complete_matches", 0)
            _state.incomplete_matches = result.get("incomplete_matches", 0)
            _state.busy = False
            _state.finished_at = datetime.now(timezone.utc).isoformat()
            _state.error = None
        logger.info(
            "[%s] Finished — %d complete, %d incomplete",
            scrape_id,
            _state.complete_matches,
            _state.incomplete_matches,
        )

        # ── Forward results to ScoreWise engine ──────────────────
        engine_forwarded = False
        webhook_url = get_env_config("SCOREWISE_WEBHOOK_URL")
        api_key = get_env_config("SCOREWISE_API_KEY")
        if webhook_url:
            try:
                file_date = get_ddmmyy_date(day)
                json_path = Path("output/json") / f"matches_{file_date}.json"
                if json_path.exists():
                    logger.info(
                        "[%s] Forwarding results to engine: %s",
                        scrape_id,
                        webhook_url,
                    )
                    ok = post_to_webhook(json_path, webhook_url, api_key)
                    engine_forwarded = ok
                    with _state_lock:
                        _state.engine_forwarded = ok
                    if ok:
                        logger.info(
                            "[%s] Successfully forwarded scrape results to engine",
                            scrape_id,
                        )
                    else:
                        logger.warning(
                            "[%s] Engine forwarding failed; results saved locally",
                            scrape_id,
                        )
                else:
                    logger.warning(
                        "[%s] Output file not found for engine forwarding: %s",
                        scrape_id,
                        json_path,
                    )
            except Exception as e:
                logger.error("[%s] Error forwarding to engine: %s", scrape_id, e)
        else:
            logger.info(
                "[%s] No SCOREWISE_WEBHOOK_URL configured; results saved locally only",
                scrape_id,
            )
    except Exception as exc:
        logger.error("[%s] Failed: %s", scrape_id, exc)
        with _state_lock:
            _state.result = None
            _state.busy = False
            _state.finished_at = datetime.now(timezone.utc).isoformat()
            _state.error = str(exc)

    _scrape_history.append(
        {
            "scrape_id": scrape_id,
            "type": "scheduled",
            "day": day,
            "finished_at": _state.finished_at,
            "success": _state.error is None,
            "complete_matches": _state.complete_matches,
            "incomplete_matches": _state.incomplete_matches,
            "engine_forwarded": engine_forwarded if _state.error is None else False,
            "streamed_count": _state.streamed_count,
            "stream_failed_count": _state.stream_failed_count,
        }
    )


def _run_results_scrape(date_str: str, scrape_id: str) -> None:
    """Run FlashscoreScraper.scrape_results() on a background thread."""
    global _state

    # CRITICAL: thread-state reset. DO NOT REMOVE.
    # Same rationale as _run_scheduled_scrape above — without this clear,
    # the worker thread is poisoned by the previous run's close() and the
    # next scrape dies immediately with "Operation cancelled by shutdown"
    # in retry_manager. See the full comment in _run_scheduled_scrape.
    # (Restored in commit 16d39a7 after being accidentally removed in bf1bf6f.)
    with _state_lock:
        _state.stop_requested = False
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

    scraper = FlashscoreScraper(
        status_callback=status_cb, progress_callback=progress_cb
    )
    try:
        scraper.scrape_results(
            date=date_str,
            status_callback=status_cb,
            progress_callback=progress_cb,
        )
        with _state_lock:
            _state.busy = False
            _state.finished_at = datetime.now(timezone.utc).isoformat()
            _state.error = None
            _state.result = {"date": date_str, "success": True}
        logger.info("[%s] Results scrape for %s finished", scrape_id, date_str)
    except Exception as exc:
        logger.error("[%s] Results scrape failed: %s", scrape_id, exc)
        with _state_lock:
            _state.busy = False
            _state.finished_at = datetime.now(timezone.utc).isoformat()
            _state.error = str(exc)

    _scrape_history.append(
        {
            "scrape_id": scrape_id,
            "type": "results",
            "date": date_str,
            "finished_at": _state.finished_at,
            "success": _state.error is None,
        }
    )


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
