"""log_capture.py

In-memory log ring buffer + handler for the /api/logs dashboard endpoint.

Captures every log record from every module (api_server, src.scraper,
src.driver_manager, uvicorn access logs, etc.) so the admin dashboard
can stream recent activity without SSH or Railway dashboard access.

Extracted from api_server.py during the api modularization.

CRITICAL implementation notes (do not change without reading):
  1. Attach to the ROOT logger only, never to api_server or any child.
     Same handler instance attached to both root and a child logger
     fires twice per record (child + propagation to root) → duplicates.
  2. Do NOT call _attach_log_capture_handler() at module-import time.
     When `python api_server.py` runs, the file is imported as module
     `__main__`; then uvicorn.run("api_server:app") RE-IMPORTS the same
     file as module `api_server`, creating a SECOND handler instance.
     Both attach to root → duplicates. Only attach via the FastAPI
     startup hook (which fires once, after uvicorn's dictConfig).
  3. Uvicorn's dictConfig strips root handlers on startup. The startup
     hook re-attaches AFTER uvicorn's config has been applied.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

# In-memory ring buffer (capacity 1000 entries, ~1 scrape's worth of logs)
_LOG_BUFFER_CAPACITY = 1000
_log_buffer: deque = deque(maxlen=_LOG_BUFFER_CAPACITY)
_log_buffer_lock = Lock()


class _LogCaptureHandler(logging.Handler):
    """Captures log records into an in-memory ring buffer for /api/logs."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat(),
                "level": record.levelname or "INFO",
                "logger": record.name or "root",
                "message": record.getMessage(),
            }
            with _log_buffer_lock:
                _log_buffer.append(entry)
        except Exception:
            # Logging must never crash the application
            pass


# Singleton handler instance — single source of truth
_log_capture_handler = _LogCaptureHandler()


def attach_log_capture_handler() -> None:
    """Attach the log capture handler to the root logger.

    Safe to call multiple times — dedupes by handler identity.

    Must be called from the FastAPI startup event (NOT at module import
    time). See module docstring for the full rationale.
    """
    root = logging.getLogger()
    if _log_capture_handler not in root.handlers:
        root.addHandler(_log_capture_handler)
    if root.level > logging.INFO or root.level == logging.NOTSET:
        root.setLevel(logging.INFO)


# ── Snapshot helpers (used by /api/logs endpoint) ──────────────────

_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def snapshot_logs(
    since: Optional[str] = None,
    limit: int = 100,
    level: Optional[str] = None,
    q: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return a filtered, limited slice of the in-memory log buffer.

    Args:
        since: ISO 8601 timestamp; only return logs at or after this time.
        limit: Max entries to return (kept most-recent).
        level: Minimum log level (DEBUG / INFO / WARNING / ERROR).
        q: Case-insensitive substring filter on logger name or message.

    Returns:
        List of log entries, oldest-first.
    """
    with _log_buffer_lock:
        items = list(_log_buffer)
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            items = [
                e
                for e in items
                if datetime.fromisoformat(e["timestamp"]) >= since_dt
            ]
        except Exception:
            # Ignore invalid `since` rather than failing the whole request
            pass
    if level:
        level_upper = level.upper()
        if level_upper in _LOG_LEVELS:
            allowed = set(_LOG_LEVELS[_LOG_LEVELS.index(level_upper) :])
            items = [e for e in items if e["level"] in allowed]
    if q:
        ql = q.lower()
        items = [
            e
            for e in items
            if ql in e["message"].lower() or ql in e["logger"].lower()
        ]
    # Keep the most recent `limit` entries; return oldest-first for natural
    # top-down reading in the dashboard.
    items = items[-limit:]
    return items


def clear_logs() -> int:
    """Clear the in-memory log buffer. Returns the number of entries removed."""
    with _log_buffer_lock:
        n = len(_log_buffer)
        _log_buffer.clear()
    return n


def buffer_size() -> int:
    """Return the current buffer size (for the /api/logs/debug endpoint)."""
    with _log_buffer_lock:
        return len(_log_buffer)


def buffer_capacity() -> int:
    """Return the buffer capacity (for the /api/logs/debug endpoint)."""
    return _LOG_BUFFER_CAPACITY
