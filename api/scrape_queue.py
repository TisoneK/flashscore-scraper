"""
scrape_queue.py — lightweight job queue for single-match result scrapes.

Features:
  - Configurable max concurrent workers (reads RESULTS_MAX_WORKERS from env-config)
  - Excess requests queue automatically (FIFO)
  - Per-job status tracking: QUEUED → RUNNING → DONE / ERROR
  - Pause/resume the queue (paused queue holds new jobs until resumed)
  - Thread-safe (uses a Lock for all state mutations)
  - In-memory only (resets on redeploy — jobs are short-lived, ~10s each)

Used by:
  POST /api/scrape/results/single — enqueues a job, returns job_id + position
  GET  /api/scrape/results/single/status — returns queue state
  POST /api/scrape/results/single/pause — pauses the queue
  POST /api/scrape/results/single/resume — resumes the queue
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("api_server")


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"


@dataclass
class ScrapeJob:
    job_id: str
    match_id: str
    status: JobStatus = JobStatus.QUEUED
    queued_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "match_id": self.match_id,
            "status": self.status.value,
            "queued_at": self.queued_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": round(self.finished_at - self.started_at, 1) if self.started_at and self.finished_at else None,
            "result": self.result,
            "error": self.error,
        }


class SingleScrapeQueue:
    """Manages concurrent single-match scrapes with queueing + pause support."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, ScrapeJob] = {}  # job_id → job
        self._match_to_job: Dict[str, str] = {}  # match_id → job_id (active only)
        self._paused = False
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_workers = 3  # default, updated on first enqueue

    def _ensure_executor(self) -> None:
        """Lazily create the thread pool with the configured max workers."""
        if self._executor is None:
            try:
                from api.env_config_store import get_env_config
                mw = get_env_config("RESULTS_MAX_WORKERS")
                if mw:
                    self._max_workers = max(1, min(5, int(mw)))
            except Exception:
                pass
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="single-scrape",
            )
            logger.info(f"[scrape-queue] Thread pool created with {self._max_workers} workers")

    def enqueue(self, match_id: str, work_fn: Callable[[str], Dict[str, Any]]) -> Dict[str, Any]:
        """Enqueue a single-match scrape job.

        If the match is already queued/running, returns the existing job's status
        instead of creating a duplicate.

        Returns: { job_id, match_id, status, position, paused }
        """
        with self._lock:
            # Check if this match is already in the queue
            existing_job_id = self._match_to_job.get(match_id)
            if existing_job_id and existing_job_id in self._jobs:
                existing = self._jobs[existing_job_id]
                if existing.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                    return {
                        "job_id": existing.job_id,
                        "match_id": match_id,
                        "status": existing.status.value,
                        "position": self._position_of(existing.job_id),
                        "paused": self._paused,
                        "message": f"Match {match_id} is already {existing.status.value}",
                    }

            # Create a new job
            job_id = str(uuid.uuid4())[:8]
            job = ScrapeJob(job_id=job_id, match_id=match_id)
            self._jobs[job_id] = job
            self._match_to_job[match_id] = job_id

            # Clean up old finished jobs (keep last 50)
            self._cleanup_old_jobs()

        # Submit to thread pool (even if paused — the worker will wait)
        self._ensure_executor()
        self._executor.submit(self._run_job, job_id, work_fn)

        with self._lock:
            return {
                "job_id": job_id,
                "match_id": match_id,
                "status": job.status.value,
                "position": self._position_of(job_id),
                "paused": self._paused,
            }

    def _run_job(self, job_id: str, work_fn: Callable[[str], Dict[str, Any]]) -> None:
        """Worker thread — waits if paused, then runs the scrape.

        Checks job status before starting. If the job was killed while
        queued (e.g. by kill_all), exits immediately without running.
        """
        # Wait if paused
        while True:
            with self._lock:
                if not self._paused:
                    break
                job = self._jobs.get(job_id)
                if job and job.status != JobStatus.QUEUED:
                    return  # Job was cancelled or killed while waiting
            time.sleep(0.5)  # Poll every 500ms

        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != JobStatus.QUEUED:
                return  # Job was killed before it could start
            job.status = JobStatus.RUNNING
            job.started_at = time.time()

        logger.info(f"[scrape-queue] Starting job {job_id} for match {job.match_id}")

        try:
            result = work_fn(job.match_id)

            # Check if the job was killed while running
            with self._lock:
                job = self._jobs.get(job_id)
                if job and job.status == JobStatus.ERROR:
                    logger.info(f"[scrape-queue] Job {job_id} was killed during execution — discarding result")
                    self._match_to_job.pop(job.match_id, None)
                    return
                if job:
                    job.status = JobStatus.DONE
                    job.finished_at = time.time()
                    job.result = result
            logger.info(f"[scrape-queue] Job {job_id} done for {job.match_id}")
        except Exception as exc:
            with self._lock:
                job = self._jobs.get(job_id)
                if job and job.status != JobStatus.ERROR:  # don't overwrite kill status
                    job.status = JobStatus.ERROR
                    job.finished_at = time.time()
                    job.error = str(exc)
            logger.error(f"[scrape-queue] Job {job_id} failed for {job.match_id}: {exc}")
        finally:
            with self._lock:
                if job:
                    self._match_to_job.pop(job.match_id, None)

    def _position_of(self, job_id: str) -> int:
        """Position in queue (0 = running now, 1+ = waiting)."""
        position = 0
        for jid, job in self._jobs.items():
            if job.status == JobStatus.QUEUED:
                position += 1
            if jid == job_id:
                return position if job.status == JobStatus.QUEUED else 0
        return 0

    def _cleanup_old_jobs(self) -> None:
        """Remove finished jobs beyond the last 50."""
        finished = [(jid, j) for jid, j in self._jobs.items() if j.status in (JobStatus.DONE, JobStatus.ERROR)]
        if len(finished) > 50:
            # Sort by finished_at, remove oldest
            finished.sort(key=lambda x: x[1].finished_at or 0)
            for jid, _ in finished[:-50]:
                self._jobs.pop(jid, None)

    def get_status(self) -> Dict[str, Any]:
        """Return the full queue state for the status endpoint."""
        with self._lock:
            running = [j.to_dict() for j in self._jobs.values() if j.status == JobStatus.RUNNING]
            queued = [j.to_dict() for j in self._jobs.values() if j.status == JobStatus.QUEUED]
            done = [j.to_dict() for j in self._jobs.values() if j.status == JobStatus.DONE]
            errors = [j.to_dict() for j in self._jobs.values() if j.status == JobStatus.ERROR]

            return {
                "paused": self._paused,
                "max_workers": self._max_workers,
                "running_count": len(running),
                "queued_count": len(queued),
                "done_count": len(done),
                "error_count": len(errors),
                "running": running,
                "queued": queued,
                "recent_done": done[-10:],  # last 10 finished
                "recent_errors": errors[-10:],
            }

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a single job's status."""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None

    def pause(self) -> None:
        """Pause the queue — running jobs finish, queued jobs wait."""
        with self._lock:
            self._paused = True
        logger.info("[scrape-queue] Paused — running jobs will finish, queued jobs will wait")

    def resume(self) -> None:
        """Resume the queue — queued jobs start running."""
        with self._lock:
            self._paused = False
        logger.info("[scrape-queue] Resumed — queued jobs will start running")

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job (can't cancel running jobs)."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.QUEUED:
                job.status = JobStatus.ERROR
                job.error = "Cancelled by admin"
                job.finished_at = time.time()
                self._match_to_job.pop(job.match_id, None)
                return True
            return False

    def kill_all(self) -> Dict[str, Any]:
        """Kill ALL jobs — queued AND running.

        Queued jobs are marked as ERROR ("Killed by admin").
        Running jobs are marked as ERROR too — the worker thread will
        check the job status after its current operation and exit.

        Also clears the match-to-job map so matches can be re-scraped.

        This is the nuclear option — use when the scraper is stuck and
        you need to clear everything. Chrome processes are NOT killed
        here (that's the caller's responsibility) but the threads will
        exit as soon as they check the job status.

        Returns: { killed_queued, killed_running }
        """
        killed_queued = 0
        killed_running = 0
        with self._lock:
            for job in self._jobs.values():
                if job.status == JobStatus.QUEUED:
                    job.status = JobStatus.ERROR
                    job.error = "Killed by admin"
                    job.finished_at = time.time()
                    killed_queued += 1
                elif job.status == JobStatus.RUNNING:
                    job.status = JobStatus.ERROR
                    job.error = "Killed by admin"
                    job.finished_at = time.time()
                    killed_running += 1
            self._match_to_job.clear()
            self._paused = True  # pause so no new jobs start

        logger.info(
            f"[scrape-queue] Kill all — {killed_queued} queued + {killed_running} running jobs killed"
        )
        return {"killed_queued": killed_queued, "killed_running": killed_running}


# Singleton
_scrape_queue = SingleScrapeQueue()
