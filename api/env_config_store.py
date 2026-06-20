"""env_config_store.py

Env-config overrides store — runtime-modifiable env vars for the scraper.

Allows the website's admin dashboard to push env-config overrides
(SCOREWISE_WEBHOOK_URL, SCOREWISE_API_KEY, SCRAPER_LOG_LEVEL, etc.)
directly to the scraper — no Railway dashboard visit needed for ongoing
changes.

Overrides are persisted to output/env_config.json and merged on top of
os.environ at read time. Existing env vars still work unchanged.

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Path to the persisted overrides file. Mount this as a Railway persistent
# volume if you want overrides to survive redeploys.
_ENV_CONFIG_PATH = Path(__file__).resolve().parent.parent / "output" / "env_config.json"
_env_config_lock = Lock()
_env_overrides: Dict[str, str] = {}

# Known keys + their env-var mappings + secret flag.
_KNOWN_ENV_KEYS: Dict[str, Dict[str, Any]] = {
    "SCOREWISE_WEBHOOK_URL": {
        "env": "SCOREWISE_WEBHOOK_URL",
        "default": "",
        "secret": False,
        "description": (
            "Engine ingestion endpoint URL "
            "(e.g. https://scorewise-engine.up.railway.app/api/ingest). "
            "When set, scraper forwards completed matches to the engine."
        ),
    },
    "SCOREWISE_API_KEY": {
        "env": "SCOREWISE_API_KEY",
        "default": "",
        "secret": True,
        "description": (
            "API key sent to the engine as X-API-Key when forwarding matches. "
            "MUST match the engine's API_KEY."
        ),
    },
    "SCRAPER_LOG_LEVEL": {
        "env": "SCRAPER_LOG_LEVEL",
        "default": "INFO",
        "secret": False,
        "description": "Python logging level (DEBUG / INFO / WARNING / ERROR).",
    },
    "SCRAPER_CRON_SCHEDULE": {
        "env": "SCRAPER_CRON_SCHEDULE",
        "default": "",
        "secret": False,
        "description": (
            "Optional cron expression (e.g. '0 6 * * *') enabling built-in "
            "daily scrape. Empty = no built-in cron."
        ),
    },
    "SCOREWISE_WEBSITE_URL": {
        "env": "SCOREWISE_WEBSITE_URL",
        "default": "",
        "secret": False,
        "description": (
            "Base URL of the website (e.g. https://scorewise-ke.vercel.app). "
            "When set + SCOREWISE_WEBHOOK_SECRET, scraper pushes final scores "
            "to /api/webhook/result after running scrape_results()."
        ),
    },
    "SCOREWISE_WEBHOOK_SECRET": {
        "env": "SCOREWISE_WEBHOOK_SECRET",
        "default": "",
        "secret": True,
        "description": (
            "HMAC-SHA256 secret used to sign result-push payloads to the website. "
            "MUST match WEBHOOK_SECRET on the website (stored in ServiceConfig "
            "table or env var)."
        ),
    },
    "RESULTS_MAX_WORKERS": {
        "env": "RESULTS_MAX_WORKERS",
        "default": "3",
        "secret": False,
        "description": (
            "Max concurrent browser instances for results scraping (1-3). "
            "1 = single-browser (slower, less memory). "
            "3 = three browsers, one per priority bucket (faster, ~900MB RAM). "
            "Set to 1 if Railway OOMs with 3 concurrent Chrome instances."
        ),
    },
    "RESULTS_INCREMENTAL_PUSH": {
        "env": "RESULTS_INCREMENTAL_PUSH",
        "default": "true",
        "secret": False,
        "description": (
            "If true, push each result to the website immediately after extraction "
            "(users see updates in real-time). If false, batch-push all results at "
            "the end (less webhook calls but slower user updates)."
        ),
    },
    "RESULTS_MATCH_DURATION_MINUTES": {
        "env": "RESULTS_MATCH_DURATION_MINUTES",
        "default": "170",
        "secret": False,
        "description": (
            "Minutes after match start time to consider the match 'likely finished'. "
            "Default 170 (2h50m) — basketball matches take 2h-2h50m. "
            "Increase if matches seem to finish later, decrease for faster detection."
        ),
    },
    "RESULTS_PRIORITY_MODE": {
        "env": "RESULTS_PRIORITY_MODE",
        "default": "status",
        "secret": False,
        "description": (
            "How to sort matches for results scraping: "
            "'status' = sort by effective status (FINISHED→LIVE→SCHEDULED, default) "
            "'time' = sort by start time (earliest first) "
            "'off' = process in original order (no sorting)"
        ),
    },
}


def load_env_overrides() -> None:
    """Load persisted env overrides from disk into the in-memory cache."""
    global _env_overrides
    try:
        if _ENV_CONFIG_PATH.exists():
            with _ENV_CONFIG_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _env_overrides = {str(k): str(v) for k, v in data.items()}
                    logger.info(
                        "Loaded %d env-config overrides from %s",
                        len(_env_overrides),
                        _ENV_CONFIG_PATH,
                    )
    except Exception as exc:
        logger.warning(
            "Failed to load env-config overrides from %s: %s",
            _ENV_CONFIG_PATH,
            exc,
        )
        _env_overrides = {}


def save_env_overrides() -> None:
    """Atomically persist the current env overrides to disk."""
    try:
        _ENV_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = _ENV_CONFIG_PATH.with_suffix(".tmp")
        with tmp_file.open("w", encoding="utf-8") as f:
            json.dump(_env_overrides, f, indent=2, sort_keys=True)
        tmp_file.replace(_ENV_CONFIG_PATH)
    except Exception as exc:
        logger.warning(
            "Failed to save env-config overrides to %s: %s",
            _ENV_CONFIG_PATH,
            exc,
        )


def get_env_config(key: str) -> str:
    """Read an env-config value: override → env var → default."""
    if key in _env_overrides:
        return _env_overrides[key]
    spec = _KNOWN_ENV_KEYS.get(key)
    if spec:
        return os.environ.get(spec["env"], spec["default"])
    return os.environ.get(key, "")


def is_env_secret(key: str) -> bool:
    """Return True if the given key is a secret (should be masked in UI)."""
    spec = _KNOWN_ENV_KEYS.get(key)
    if spec:
        return bool(spec["secret"])
    return bool(re.search(r"(SECRET|KEY|TOKEN|PASSWORD|API_KEY)", key, re.IGNORECASE))


def mask_env_value(value: str) -> str:
    """Mask a secret value for display — first 4 + last 4 chars only."""
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return value[:4] + "••••" + value[-4:]


def set_override(key: str, value: str) -> None:
    """Set or update an override. Empty value removes the override.

    Caller is responsible for calling save_env_overrides() afterwards.
    """
    with _env_config_lock:
        if value == "":
            _env_overrides.pop(key, None)
        else:
            _env_overrides[key] = value


def remove_override(key: str) -> bool:
    """Remove an override. Returns True if it existed."""
    with _env_config_lock:
        if key in _env_overrides:
            _env_overrides.pop(key)
            return True
        return False


def get_overrides() -> Dict[str, str]:
    """Return a copy of the current overrides dict."""
    with _env_config_lock:
        return dict(_env_overrides)


def get_known_keys() -> Dict[str, Dict[str, Any]]:
    """Return the known env-config keys spec (for the /api/env-config endpoint)."""
    return _KNOWN_ENV_KEYS


# Load on import
load_env_overrides()
