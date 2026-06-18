"""Scraper API package.

Modular structure (extracted from the original api_server.py during the
api modularization):

  api_server.py         — entry point (uvicorn.run only)
  api/
    app.py              — FastAPI app + middleware + startup hooks
    state.py            — _ScraperState, _executor, _stream_executor, scrape runners
    log_capture.py      — _LogCaptureHandler, _log_buffer, _attach_log_capture_handler
    schemas.py          — Pydantic models (request/response)
    env_config_store.py — _KNOWN_ENV_KEYS, _env_overrides, _load/_save/_get_env_config
    routers/
      scrape.py         — POST /scrape, /scrape/results, /scrape/stop, GET /scrape/progress
      status.py         — GET /status, /history, /outputs, /outputs/{filename}, /outputs/{filename}/csv
      config.py         — GET/PUT /config, GET /config/schema (legacy file-based)
      env_config.py     — GET/POST /env-config, DELETE /env-config/{key}
      schedule.py       — GET/PUT /schedule, _run_schedule_loop
      logs.py           — GET/DELETE /logs, GET /logs/debug
      drivers.py        — GET /drivers/versions, POST /drivers/install
      init.py           — POST /initialize, POST /results/update
"""
