"""status.py router

Status, history, and outputs endpoints.

Endpoints:
  GET /api/status                        — scraper state + last run summary
  GET /api/history                       — recent scrape run history (in-memory)
  GET /api/outputs                       — list JSON output files
  GET /api/outputs/{filename}            — download a JSON output file
  GET /api/outputs/{filename}/csv        — download a JSON output file as CSV

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from api.state import _state, _state_lock, _results_state, _results_state_lock, _scrape_history

# PROJECT_ROOT is the scraper repo root (parent of the api/ package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger("api_server")
router = APIRouter()


def _flatten_dict(
    d: Dict[str, Any], parent_key: str = "", sep: str = "."
) -> Dict[str, Any]:
    """Recursively flatten a nested dict (e.g. odds.home_odds)."""
    items: List[tuple] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, json.dumps(v, ensure_ascii=False)))
        else:
            items.append((new_key, v))
    return dict(items)


@router.get("/status")
async def get_status():
    """Return scraper state and a summary of the last completed scrape.

    Mirrors the CLI **View Status** screen which shows the overall
    scraper health and last-run statistics.
    """
    with _state_lock:
        busy = _state.busy
        last = _state.result
        err = _state.error

    # Also check results scrape state (runs concurrently with scheduled scrapes)
    with _results_state_lock:
        results_busy = _results_state.busy
        results_last = _results_state.result
        results_err = _results_state.error

    if busy or results_busy:
        status_text = "scraping"
    elif last is not None or results_last is not None:
        status_text = "idle (last scrape succeeded)"
    elif err or results_err:
        status_text = "idle (last scrape failed)"
    else:
        status_text = "idle (no runs yet)"

    return {
        "status": status_text,
        "scraper_busy": busy or results_busy,
        "scheduled_busy": busy,
        "results_busy": results_busy,
        "last_scrape": (
            {
                "success": err is None and last is not None,
                "error": err,
                "scrape_type": _state.scrape_type,
                "day": _state.day,
                "date": _state.date,
                "complete_matches": _state.complete_matches,
                "incomplete_matches": _state.incomplete_matches,
                "started_at": _state.started_at,
                "finished_at": _state.finished_at,
                "engine_forwarded": _state.engine_forwarded,
                "streamed_count": _state.streamed_count,
                "stream_failed_count": _state.stream_failed_count,
            }
            if not busy
            else None
        ),
        "currentDay": _state.day,
        "progress": (
            {
                "busy": _state.busy,
                "scrape_id": _state.scrape_id,
                "scrape_type": _state.scrape_type,
                "day": _state.day,
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
            if _state.busy
            else None
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=200)):
    """Return recent scrape runs (in-memory, last *limit* entries)."""
    return {"runs": _scrape_history[-limit:], "total": len(_scrape_history)}


@router.get("/outputs")
async def list_outputs():
    """List JSON output files, split into ``match_files`` and ``results_files``.

    Mirrors the CLI's status screen which shows file counts in
    the ``output/json/`` directory.
    """
    json_dir = PROJECT_ROOT / "output" / "json"
    if not json_dir.exists():
        return {"match_files": [], "results_files": []}

    files = sorted(json_dir.iterdir(), key=os.path.getmtime, reverse=True)
    match_files: List[Dict[str, Any]] = []
    results_files: List[Dict[str, Any]] = []

    for f in files:
        if f.suffix != ".json":
            continue
        entry = {
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "modified": datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        }
        if f.name.startswith("results_"):
            results_files.append(entry)
        elif f.name.startswith("matches_"):
            match_files.append(entry)

    return {"match_files": match_files, "results_files": results_files}


@router.get("/outputs/{filename:path}")
async def get_output(filename: str):
    """Download a specific JSON output file (e.g. ``matches_250614.json``)."""
    # Prevent directory traversal
    sanitised = Path(filename).name
    json_path = PROJECT_ROOT / "output" / "json" / sanitised
    if not json_path.exists() or not json_path.is_file():
        raise HTTPException(404, f"File '{sanitised}' not found")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(500, "File contains invalid JSON")


@router.get("/outputs/{filename:path}/csv")
async def get_output_csv(filename: str):
    """Download a specific JSON output file as CSV (flattened)."""
    sanitised = Path(filename).name
    json_path = PROJECT_ROOT / "output" / "json" / sanitised
    if not json_path.exists() or not json_path.is_file():
        raise HTTPException(404, f"File '{sanitised}' not found")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(500, "File contains invalid JSON")

    matches = data.get("matches", [])
    if not matches:
        raise HTTPException(404, "No match data in file")

    # Flatten first match for headers
    flat = _flatten_dict(matches[0])
    headers = list(flat.keys())

    async def stream_csv():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        for m in matches:
            writer.writerow(_flatten_dict(m))
        yield buf.getvalue()

    return StreamingResponse(
        stream_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={sanitised.replace('.json', '.csv')}"
        },
    )
