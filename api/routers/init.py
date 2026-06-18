"""init.py router

Project initialization + results update endpoints.

Endpoints:
  POST /api/initialize       — initialize the project (mkdir output dirs + install driver)
  POST /api/results/update   — update match results from a JSON file (writes CSV)

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import InitProjectRequest, ResultsUpdateRequest
from src.driver_manager.driver_installer import DriverInstaller

# PROJECT_ROOT is the scraper repo root (parent of the api/ package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger("api_server")
router = APIRouter()


@router.post("/initialize")
async def initialize_project(req: InitProjectRequest):
    """Initialize the project and install drivers.

    Mirrors the CLI's ``--init [browser [version]]`` flag. Ensures the
    output directories exist and the chosen driver is downloaded.
    """
    # Ensure output directories exist
    (PROJECT_ROOT / "output" / "json").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "output" / "logs").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "output" / "database").mkdir(parents=True, exist_ok=True)

    if req.browser not in ("chrome", "firefox"):
        raise HTTPException(422, "browser must be 'chrome' or 'firefox'")

    try:
        installer = DriverInstaller()
        version = req.version or ("138" if req.browser == "chrome" else None)
        if req.browser == "firefox":
            result = installer.install_firefox_driver(version=version)
        else:
            result = installer.install_chrome_driver(version=version)
        return {
            "status": "ok",
            "message": f"Project initialized with {req.browser}",
            "version": version or "latest",
            "details": str(result),
        }
    except Exception as exc:
        raise HTTPException(500, f"Initialization failed: {exc}")


@router.post("/results/update")
async def update_results(req: ResultsUpdateRequest):
    """Update match results from a JSON file.

    Mirrors the CLI's ``--results-update JSON_FILE`` flag. Reads a JSON
    results file and writes an updated CSV with final scores.
    """
    json_path = Path(req.json_file)
    if not json_path.is_absolute():
        json_path = PROJECT_ROOT / json_path
    if not json_path.exists():
        raise HTTPException(404, f"File not found: {json_path}")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        raise HTTPException(400, f"Cannot read JSON file: {exc}")

    results = data.get("results", data.get("matches", []))
    if not results:
        raise HTTPException(400, "No results or matches found in JSON file")

    # Produce CSV output
    output_path = req.output or str(json_path.with_suffix(".csv"))
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            if results and isinstance(results[0], dict):
                writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
                writer.writeheader()
                writer.writerows(results)
            else:
                raise HTTPException(400, "Results entries must be dicts")
    except IOError as exc:
        raise HTTPException(500, f"Failed to write CSV: {exc}")

    logger.info(
        "Results updated: %s → %s (%d entries)",
        json_path.name,
        output_path,
        len(results),
    )
    return {
        "status": "ok",
        "input": str(json_path),
        "output": str(output_path),
        "entries": len(results),
    }
