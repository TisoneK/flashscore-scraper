import logging
from fastapi import APIRouter, HTTPException
from typing import Optional

from ..models import (
    StartScrapeRequest,
    StartScrapeResponse,
    JobInfo,
    JobStatusResponse,
    StartResultsRequest,
)
from ..services.job_manager import JobManager
from pathlib import Path
from src.scraper import FlashscoreScraper
from src.driver_manager import WebDriverManager
from src.storage.json_storage import JSONStorage
from src.utils.config_loader import load_config
from src.reporting import CallbackReporter


router = APIRouter()
logger = logging.getLogger(__name__)

# Shared singleton JobManager for the process
job_manager = JobManager()


def _to_yyyymmdd(date_str: str) -> str:
    s = date_str.strip()
    # Accept YYYY-MM-DD
    if len(s) == 10 and s[4] == '-' and s[7] == '-':
        return s.replace('-', '')
    # Accept DD.MM.YYYY
    if len(s) == 10 and s[2] == '.' and s[5] == '.':
        dd, mm, yyyy = s.split('.')
        return f"{yyyy}{mm}{dd}"
    # Accept YYYYMMDD
    if len(s) == 8 and s.isdigit():
        return s
    # Accept DDMMYY → expand to 20YY assuming 20xx
    if len(s) == 6 and s.isdigit():
        dd, mm, yy = s[:2], s[2:4], s[4:6]
        return f"20{yy}{mm}{dd}"
    # Fallback: leave as is
    return s


def _jobinfo_from_record(record) -> JobInfo:
    return JobInfo(job_id=record.job_id, status=record.status, detail=record.detail)


@router.post("/start", response_model=StartScrapeResponse)
def start_scrape(request: StartScrapeRequest) -> StartScrapeResponse:
    day = request.day

    def task_with_ctx(rec, log, is_cancelled, set_progress):
        # Construct explicit dependencies (no global CONFIG access)
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
        # Periodically check cancellation via stop_callback
        scraper.scrape(
            day=day,
            status_callback=lambda m: log(str(m)),
            progress_callback=lambda current, total, message=None: set_progress(current, total, message),
            stop_callback=lambda: is_cancelled(),
        )

    job_id = job_manager.submit_with_context(task_with_ctx)
    record = job_manager.get(job_id)
    assert record is not None
    return StartScrapeResponse(job=_jobinfo_from_record(record))


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    record = job_manager.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(job=_jobinfo_from_record(record))


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str) -> JobStatusResponse:
    ok = job_manager.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    record = job_manager.get(job_id)
    assert record is not None
    return JobStatusResponse(job=_jobinfo_from_record(record))


@router.get("/{job_id}/logs")
def get_job_logs(job_id: str):
    record = job_manager.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": record.status, "logs": job_manager.get_logs(job_id)}


@router.get("/{job_id}/progress")
def get_job_progress(job_id: str):
    record = job_manager.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    prog = job_manager.get_progress(job_id)
    if not prog:
        return {"job_id": job_id, "status": record.status, "current": None, "total": None, "message": None}
    current, total, message = prog
    return {"job_id": job_id, "status": record.status, "current": current, "total": total, "message": message}


@router.get("/")
def list_jobs():
    # Simple snapshot (no paging)
    # Return as dict mapping id -> status
    items = {}
    # Access via internal get to avoid exposing records directly
    for jid, rec in list(job_manager._jobs.items()):  # type: ignore[attr-defined]
        items[jid] = {
            "status": rec.status,
            "detail": rec.detail,
            "started_at": rec.started_at,
            "finished_at": rec.finished_at,
        }
    return {"jobs": items}


@router.post("/results", response_model=StartScrapeResponse)
def start_results_scrape(request: StartResultsRequest) -> StartScrapeResponse:
    normalized = _to_yyyymmdd(request.date)

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
            progress_callback=lambda current, total, message=None: set_progress(current, total, message),
        )

    job_id = job_manager.submit_with_context(task_with_ctx)
    record = job_manager.get(job_id)
    assert record is not None
    return StartScrapeResponse(job=_jobinfo_from_record(record))
