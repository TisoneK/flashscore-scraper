import json
from typing import Any, Dict, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException

from . import results  # for PROJECT_ROOT resolution
from . import jobs as jobs_routes
from ..models import StartScrapeResponse, JobInfo
from src.scraper import FlashscoreScraper
from src.driver_manager import WebDriverManager
from src.storage.json_storage import JSONStorage
from src.utils.config_loader import load_config
from src.reporting import CallbackReporter


router = APIRouter()

PROJECT_ROOT = results.PROJECT_ROOT
CONFIG_PATH = PROJECT_ROOT / "src" / "config.json"


@router.get("/config")
def get_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="config.json not found")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.patch("/config")
def patch_config(update: Dict[str, Any]) -> Dict[str, Any]:
    # Load existing
    data: Dict[str, Any] = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

    # Update only existing top-level keys to avoid accidental schema changes
    for k, v in update.items():
        if k in data:
            data[k] = v

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return data


@router.get("/status")
def get_scraper_status():
    # Summarize job manager state
    jm = jobs_routes.job_manager
    summary = {}
    for jid, rec in list(jm._jobs.items()):  # type: ignore[attr-defined]
        summary[jid] = {
            "status": rec.status,
            "detail": rec.detail,
            "started_at": rec.started_at,
            "finished_at": rec.finished_at,
        }
    return {"jobs": summary}


@router.post("/jobs/{job_id}/stop")
def stop_job(job_id: str):
    jm = jobs_routes.job_manager
    ok = jm.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    rec = jm.get(job_id)
    return {"job_id": job_id, "status": rec.status if rec else "cancelled"}


def _to_yyyymmdd(date_str: str) -> str:
    s = date_str.strip()
    if len(s) == 10 and s[4] == '-' and s[7] == '-':
        return s.replace('-', '')
    if len(s) == 10 and s[2] == '.' and s[5] == '.':
        dd, mm, yyyy = s.split('.')
        return f"{yyyy}{mm}{dd}"
    if len(s) == 8 and s.isdigit():
        return s
    if len(s) == 6 and s.isdigit():
        dd, mm, yy = s[:2], s[2:4], s[4:6]
        return f"20{yy}{mm}{dd}"
    return s


@router.get("/start", response_model=StartScrapeResponse)
def start_scrape_via_query(
    mode: str = "scheduled",
    day: str = "Today",
    headless: Optional[bool] = None,
    max_tabs: Optional[int] = None,
    max_matches: Optional[int] = None,
    base_batch_size: Optional[int] = None,
    disable_images: Optional[bool] = None,
    proxy: Optional[str] = None,
    log_level: Optional[str] = None,
):
    if mode not in ("scheduled", "results"):
        raise HTTPException(status_code=400, detail="mode must be 'scheduled' or 'results'")

    jm = jobs_routes.job_manager

    if mode == "results":
        raise HTTPException(status_code=400, detail="Use /scraper/results?date=... for results mode")

    def task_with_ctx(rec, log, is_cancelled, set_progress):
        config_snapshot = load_config()
        driver_factory = lambda: WebDriverManager()
        storage = JSONStorage()
        reporter = CallbackReporter(status_callback=lambda m: log(str(m)), progress_callback=lambda c, t, msg=None: set_progress(c, t, msg))
        scraper = FlashscoreScraper(
            reporter=reporter,
            driver_factory=driver_factory,
            storage=storage,
            config_snapshot=config_snapshot,
        )
        scraper.scrape(
            day=day,
            status_callback=lambda m: log(str(m)),
            progress_callback=lambda c, t, msg=None: set_progress(c, t, msg),
            stop_callback=lambda: is_cancelled(),
        )

    job_id = jm.submit_with_context(task_with_ctx)
    record = jm.get(job_id)
    assert record is not None
    return StartScrapeResponse(job=JobInfo(job_id=record.job_id, status=record.status, detail=record.detail))


@router.get("/results", response_model=StartScrapeResponse)
def start_results_via_query(date: str):
    normalized = _to_yyyymmdd(date)
    jm = jobs_routes.job_manager

    def task_with_ctx(rec, log, is_cancelled, set_progress):
        config_snapshot = load_config()
        driver_factory = lambda: WebDriverManager()
        storage = JSONStorage()
        reporter = CallbackReporter(status_callback=lambda m: log(str(m)), progress_callback=lambda c, t, msg=None: set_progress(c, t, msg))
        scraper = FlashscoreScraper(
            reporter=reporter,
            driver_factory=driver_factory,
            storage=storage,
            config_snapshot=config_snapshot,
        )
        scraper.scrape_results(
            date=normalized,
            status_callback=lambda m: log(str(m)),
            progress_callback=lambda c, t, msg=None: set_progress(c, t, msg),
        )

    job_id = jm.submit_with_context(task_with_ctx)
    record = jm.get(job_id)
    assert record is not None
    return StartScrapeResponse(job=JobInfo(job_id=record.job_id, status=record.status, detail=record.detail))


