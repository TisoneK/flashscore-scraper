#!/usr/bin/env python3
"""
FastAPI control server for the Flashscore Scraper.

This is the entry point only. All routes, state, and helpers live in the
`api/` package:

  api/
    app.py              — FastAPI app + startup hooks + router registration
    state.py            — _ScraperState, _executor, scrape runners
    log_capture.py      — _LogCaptureHandler, _log_buffer, attach_log_capture_handler
    schemas.py          — Pydantic models (request/response)
    env_config_store.py — _KNOWN_ENV_KEYS, _env_overrides, _load/_save/_get_env_config
    routers/
      scrape.py         — POST /api/scrape, /api/scrape/results, /api/scrape/stop, GET /api/scrape/progress
      status.py         — GET /api/status, /api/history, /api/outputs, /api/outputs/{filename}, /api/outputs/{filename}/csv
      config.py         — GET/PUT /api/config, GET /api/config/schema (legacy file-based)
      env_config.py     — GET/POST /api/env-config, DELETE /api/env-config/{key}
      schedule.py       — GET/PUT /api/schedule, _run_schedule_loop
      logs.py           — GET/DELETE /api/logs, GET /api/logs/debug
      drivers.py        — GET /api/drivers/versions, POST /api/drivers/install
      init.py           — POST /api/initialize, POST /api/results/update

Run:
    python api_server.py            # development
    uvicorn api_server:app ...      # production (Railway)
"""

import logging
import os
import sys
from pathlib import Path

# ── Ensure project root is on sys.path ──────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Logging ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api_server")

# ── Import the FastAPI app from the api package ─────────────────
# This import has side effects: registers all routers, loads env-config
# overrides from disk, and attaches the log capture handler at import
# time (the startup hook re-attaches it after uvicorn's dictConfig).
from api.app import app  # noqa: E402

import uvicorn  # noqa: E402


def main() -> None:
    """Entry point — run the uvicorn server.

    Port from ``$PORT`` env (Railway) or 8080.
    Host from ``$HOST`` env or ``0.0.0.0``.
    """
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info("Starting API server on %s:%s ...", host, port)
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
