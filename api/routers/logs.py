"""logs.py router

Live log streaming endpoints for the admin dashboard.

Endpoints:
  GET    /api/logs          — list recent log entries (with filters)
  DELETE /api/logs          — clear the in-memory buffer
  GET    /api/logs/debug    — diagnostic endpoint showing logging state

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from api.schemas import LogEntry, LogsResponse
from api.log_capture import (
    snapshot_logs,
    clear_logs,
    buffer_size,
    buffer_capacity,
    attach_log_capture_handler,
    _log_capture_handler,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/logs", response_model=LogsResponse)
async def list_logs(
    since: Optional[str] = Query(
        None,
        description="ISO 8601 timestamp; only return logs at or after this time (for incremental polling)",
    ),
    limit: int = Query(100, ge=1, le=500, description="Max entries to return (1-500)"),
    level: Optional[str] = Query(
        None,
        description="Minimum log level: DEBUG / INFO / WARNING / ERROR (includes this level and above)",
    ),
    q: Optional[str] = Query(
        None,
        description="Case-insensitive substring filter on logger name or message",
    ),
):
    """Return recent log entries from the in-memory ring buffer.

    Entries are returned oldest-first (so the dashboard can append new entries
    to the bottom as they arrive). Use `since` with the previous response's
    `newest` timestamp to poll for incremental updates without re-fetching
    the whole buffer.
    """
    items = snapshot_logs(since=since, limit=limit, level=level, q=q)
    return LogsResponse(
        logs=[LogEntry(**e) for e in items],
        total=len(items),
        oldest=items[0]["timestamp"] if items else None,
        newest=items[-1]["timestamp"] if items else None,
    )


@router.delete("/logs")
async def clear_logs_endpoint():
    """Clear the in-memory log buffer.

    Useful for resetting the dashboard view when the buffer gets noisy.
    Does NOT affect on-disk log files (output/logs/*.log) — only the
    in-memory ring buffer used by /api/logs.
    """
    n = clear_logs()
    logger.info("Log buffer cleared via API (%d entries removed)", n)
    return {"cleared": True, "removed": n}


@router.get("/logs/debug")
async def debug_logs():
    """Diagnostic endpoint — returns the current state of the logging system.

    Used to verify that the _LogCaptureHandler is actually attached to the
    root logger at request time (not just at startup). If 'capture_handler_attached'
    is false, the /api/logs endpoint will return an empty buffer even when
    the service is actively logging.
    """
    root = logging.getLogger()
    api_server_logger = logging.getLogger("api_server")
    return {
        "capture_handler_attached": _log_capture_handler in root.handlers,
        "root_logger_level": logging.getLevelName(root.level),
        "root_logger_handlers": [
            {
                "class": type(h).__name__,
                "name": getattr(h, "name", None)
                or h.__class__.__module__
                + "."
                + type(h).__name__,
            }
            for h in root.handlers
        ],
        "api_server_logger_level": logging.getLevelName(api_server_logger.level),
        "api_server_logger_propagate": api_server_logger.propagate,
        "api_server_logger_handlers": [
            {"class": type(h).__name__} for h in api_server_logger.handlers
        ],
        "buffer_size": buffer_size(),
        "buffer_capacity": buffer_capacity(),
    }
