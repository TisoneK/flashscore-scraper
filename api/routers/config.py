"""config.py router

Legacy file-based configuration endpoints (reads/writes src/config.json).

This is the OLD config system — distinct from the env-config system in
env_config.py router, which manages runtime env-var overrides pushed from
the admin dashboard.

Endpoints:
  GET /api/config         — return the full scraper config from src/config.json
  PUT /api/config         — update scraper config (deep-merge)
  GET /api/config/schema  — return config schema (sections + descriptions)

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException

from api.schemas import ConfigUpdateRequest

# PROJECT_ROOT is the scraper repo root (parent of the api/ package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH: Path = PROJECT_ROOT / "src" / "config.json"

logger = logging.getLogger("api_server")
router = APIRouter()


@router.get("/config")
async def get_config():
    """Return the full scraper configuration from ``src/config.json``."""
    if not _CONFIG_PATH.exists():
        raise HTTPException(404, "Config file not found")
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(500, "Config file contains invalid JSON")


@router.put("/config")
async def update_config(req: ConfigUpdateRequest):
    """Update scraper configuration (deep-merge).

    Mirrors the CLI's **Configure Settings** screen.  Send the keys you
    want to change; nested dicts are merged recursively.
    """
    if not _CONFIG_PATH.exists():
        raise HTTPException(404, "Config file not found")

    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            current = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(500, "Config file contains invalid JSON")

    def _deep_merge(base: Dict, overlay: Dict) -> None:
        for key, value in overlay.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                _deep_merge(base[key], value)
            else:
                base[key] = value

    _deep_merge(current, req.config)

    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)

    logger.info("Configuration updated via API")
    return {"status": "ok", "config": current}


@router.get("/config/schema")
async def get_config_schema():
    """Return the config schema — a list of all top-level sections with descriptions."""
    return {
        "sections": {
            "browser": "Browser settings: headless, window_size, browser_name, chrome_binary_path, etc.",
            "timeout": "Timeouts: page_load, element, retry_delay, max_retries, etc.",
            "output": "Output settings: directory, date_format, time_format",
            "logging": "Logging: log_level, log_directory, quiet_modules, etc.",
            "batch": "Batch processing: base_batch_size, adaptive_delay, etc.",
            "scraping": "Scraping limits: max_matches, min_h2h_matches",
            "selectors": "CSS/XPath selectors for match, odds, H2H elements",
        }
    }
