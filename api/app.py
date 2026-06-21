"""app.py

FastAPI application instance + startup hooks + router registration.

Extracted from api_server.py during the api modularization.

This module exposes the `app` object that uvicorn loads via
`uvicorn api_server:app` (api_server.py imports `app` from here).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI

from api.log_capture import attach_log_capture_handler
from api.routers import (
    scrape,
    status,
    config,
    env_config,
    schedule,
    logs,
    drivers,
    init,
)

logger = logging.getLogger("api_server")

app = FastAPI(
    title="Flashscore Scraper API",
    version="1.0.0",
    description=(
        "Control server for the Flashscore basketball scraper. "
        "Mirrors all CLI capabilities via REST."
    ),
)

# All routes are mounted under /api/ prefix — matches the original
# api_server.py's `APIRouter(prefix="/api")` behavior. Each router defines
# its routes as /scrape, /status, etc.; the prefix is added here so we
# don't repeat /api/ in every router file.
app.include_router(scrape.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(env_config.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(drivers.router, prefix="/api")
app.include_router(init.router, prefix="/api")


@app.on_event("startup")
async def _on_startup() -> None:
    """Startup: re-attach log handler + auto-start results scheduler."""
    # 1. Re-attach log capture handler (uvicorn strips it)
    attach_log_capture_handler()
    logger.info("Log capture handler attached — /api/logs is live")

    # 2. Auto-start the results scheduler if it was enabled before restart
    try:
        from api.routers.schedule import _try_autostart
        _try_autostart()
    except Exception as e:
        logger.warning(f"Failed to auto-start results scheduler: {e}")


@app.get("/health")
async def health():
    """Liveness probe. Returns 200 when the server is ready."""
    from api.state import _state, _state_lock

    with _state_lock:
        busy = _state.busy
    return {
        "status": "ok",
        "scraper_busy": busy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
