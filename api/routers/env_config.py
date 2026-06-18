"""env_config.py router

Env-config management endpoints — runtime-modifiable env vars.

Endpoints:
  GET    /api/env-config          — list all known env-config keys (secrets masked)
  POST   /api/env-config          — update one or more env-config keys
  DELETE /api/env-config/{key}    — remove an override for a single key

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from api.schemas import (
    EnvConfigEntry,
    EnvConfigListResponse,
    EnvConfigUpdateRequest,
    EnvConfigUpdateResponse,
)
from api.env_config_store import (
    get_env_config,
    is_env_secret,
    mask_env_value,
    get_overrides,
    get_known_keys,
    set_override,
    remove_override,
    save_env_overrides,
)

logger = logging.getLogger("api_server")
router = APIRouter()


@router.get("/env-config", response_model=EnvConfigListResponse)
async def list_env_config():
    """List all known env-config keys with their current values (secrets masked)."""
    overrides = get_overrides()
    known = get_known_keys()
    keys = sorted(set(list(known.keys()) + list(overrides.keys())))
    entries: List[EnvConfigEntry] = []
    for k in keys:
        spec = known.get(k, {})
        raw_value = get_env_config(k)
        entries.append(
            EnvConfigEntry(
                key=k,
                value=mask_env_value(raw_value) if is_env_secret(k) else raw_value,
                has_override=k in overrides,
                is_secret=is_env_secret(k),
                description=spec.get("description"),
                env_var=spec.get("env"),
            )
        )
    return EnvConfigListResponse(configs=entries, total=len(entries))


@router.post("/env-config", response_model=EnvConfigUpdateResponse)
async def update_env_config(req: EnvConfigUpdateRequest):
    """Update one or more env-config keys. Empty value removes override."""
    updated: List[str] = []
    removed: List[str] = []
    failed = {}
    for key, value in req.updates.items():
        if not key or not key.strip():
            failed[key or "(empty)"] = "Key must be non-empty"
            continue
        try:
            if value == "":
                if remove_override(key):
                    removed.append(key)
                else:
                    # No-op: empty value + no existing override = nothing to remove
                    removed.append(key)
            else:
                set_override(key, value)
                updated.append(key)
        except Exception as exc:
            failed[key] = str(exc)
    if updated or removed:
        save_env_overrides()
    if updated:
        logger.info("Env-config updated via API: %s", ", ".join(updated))
    if removed:
        logger.info("Env-config overrides removed via API: %s", ", ".join(removed))
    return EnvConfigUpdateResponse(updated=updated, removed=removed, failed=failed)


@router.delete("/env-config/{key}")
async def delete_env_override(key: str):
    """Remove an override for a single env-config key (falls back to env var/default)."""
    if not key:
        raise HTTPException(400, "Key is required")
    if remove_override(key):
        save_env_overrides()
        return {
            "removed": key,
            "message": f"Override for {key} removed. Scraper now uses env var or default.",
        }
    return {
        "removed": None,
        "message": f"No override found for {key}. Nothing to remove.",
    }
