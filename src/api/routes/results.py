import json
from typing import List
from fastapi import APIRouter, HTTPException
from pathlib import Path

from ..models import ResultsListResponse, ResultsFileResponse, ResultFileMetadata


router = APIRouter()


# Resolve project root regardless of current working directory
# src/api/routes/results.py → parents[4] == project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = PROJECT_ROOT / "output" / "json"


def _resolve_results_path_for_date(date_str: str) -> Path:
    """Resolve a results file path from a user-supplied date string.

    Accepts formats:
    - YYYY-MM-DD (e.g., 2025-10-12)
    - YYYYMMDD (e.g., 20251012)
    - DD.MM.YYYY (e.g., 12.10.2025)
    - DDMMYY (e.g., 121025)
    Returns the first existing path among common filename patterns.
    """
    s = date_str.strip()
    candidates = []
    # Normalize into several patterns
    ymd = s.replace("-", "").replace(".", "")
    if len(ymd) == 8 and s.count("-") == 2:
        # YYYY-MM-DD
        candidates.append(RESULTS_DIR / f"matches_{ymd}.json")
    elif len(ymd) == 8 and s.count(".") == 2 and s.find(".") == 2:
        # DD.MM.YYYY → to YYYYMMDD
        dd, mm, yyyy = s.split(".")
        candidates.append(RESULTS_DIR / f"matches_{yyyy}{mm}{dd}.json")
    elif len(ymd) == 8:
        # Already compact YYYYMMDD
        candidates.append(RESULTS_DIR / f"matches_{ymd}.json")

    # Legacy short pattern DDMMYY (observed in repo: matches_250925.json)
    if len(s) == 6 and s.isdigit():
        candidates.append(RESULTS_DIR / f"matches_{s}.json")

    # Fallback: try any file containing digits of the date in order
    for p in RESULTS_DIR.glob("matches_*.json"):
        if all(ch in p.name for ch in [c for c in s if c.isdigit()]):
            candidates.append(p)

    # Return first that exists
    for path in candidates:
        if path.exists():
            return path
    # If none found, raise
    raise FileNotFoundError("No results file for the given date")


@router.get("/", response_model=ResultsListResponse)
def list_results() -> ResultsListResponse:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    files: List[ResultFileMetadata] = []
    for p in sorted(RESULTS_DIR.glob("matches_*.json")):
        stat = p.stat()
        files.append(
            ResultFileMetadata(
                filename=p.name, size_bytes=stat.st_size, last_update=None
            )
        )
    return ResultsListResponse(files=files)


@router.get("/latest", response_model=ResultsFileResponse)
def get_latest_results() -> ResultsFileResponse:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    files = list(RESULTS_DIR.glob("matches_*.json"))
    if not files:
        raise HTTPException(status_code=404, detail="No results files found")
    latest = max(files, key=lambda p: p.stat().st_mtime)
    with open(latest, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ResultsFileResponse(filename=latest.name, data=data)


@router.get("/by-date/{date}", response_model=ResultsFileResponse)
def get_results_by_date(date: str) -> ResultsFileResponse:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        path = _resolve_results_path_for_date(date)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No results file for the given date")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ResultsFileResponse(filename=path.name, data=data)


