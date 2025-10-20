import threading
import uuid
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, List, Tuple


JobStatus = str  # "queued" | "running" | "completed" | "failed" | "cancelled"


@dataclass
class JobRecord:
    job_id: str
    status: JobStatus
    detail: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    _logs: List[str] = field(default_factory=list)
    _cancel_event: threading.Event = field(default_factory=threading.Event)
    _progress: Optional[Tuple[int, int, Optional[str]]] = None  # current, total, message


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def _log(self, job_id: str, message: str) -> None:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return
            # Keep last 500 messages to cap memory
            rec._logs.append(message)
            if len(rec._logs) > 500:
                rec._logs = rec._logs[-500:]

    def get_logs(self, job_id: str) -> List[str]:
        with self._lock:
            rec = self._jobs.get(job_id)
            return list(rec._logs) if rec else []

    def set_progress(self, job_id: str, current: int, total: int, message: Optional[str]) -> None:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return
            rec._progress = (current, total, message)

    def get_progress(self, job_id: str) -> Optional[Tuple[int, int, Optional[str]]]:
        with self._lock:
            rec = self._jobs.get(job_id)
            return rec._progress if rec else None

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return False
            rec._cancel_event.set()
            # If job not yet started, mark cancelled
            if rec.status == "queued":
                rec.status = "cancelled"
                rec.finished_at = time.time()
            return True

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            rec = self._jobs.get(job_id)
            return bool(rec and rec._cancel_event.is_set())

    def submit(self, target: Callable[[], None]) -> str:
        job_id = str(uuid.uuid4())
        record = JobRecord(job_id=job_id, status="queued")
        with self._lock:
            self._jobs[job_id] = record

        def runner():
            with self._lock:
                rec = self._jobs[job_id]
                rec.status = "running"
                rec.started_at = time.time()
            try:
                target()
                with self._lock:
                    rec = self._jobs[job_id]
                    rec.status = "completed"
                    rec.finished_at = time.time()
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    rec = self._jobs[job_id]
                    rec.status = "failed"
                    rec.detail = str(exc)
                    rec.finished_at = time.time()

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        return job_id

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    # Submit with context: provides log and cancel hooks to runner
    def submit_with_context(
        self,
        runner: Callable[[JobRecord, Callable[[str], None], Callable[[], bool], Callable[[int, int, Optional[str]], None]], None],
    ) -> str:
        job_id = str(uuid.uuid4())
        record = JobRecord(job_id=job_id, status="queued")
        with self._lock:
            self._jobs[job_id] = record

        def log_fn(msg: str) -> None:
            self._log(job_id, msg)

        def is_cancelled() -> bool:
            return self.is_cancelled(job_id)

        def runner_wrapper():
            with self._lock:
                rec = self._jobs[job_id]
                if rec.status == "cancelled":
                    # Cancelled before start
                    rec.finished_at = time.time()
                    return
                rec.status = "running"
                rec.started_at = time.time()
            try:
                runner(record, log_fn, is_cancelled, lambda c, t, m: self.set_progress(job_id, c, t, m))
                with self._lock:
                    rec = self._jobs[job_id]
                    if rec.status != "cancelled":
                        rec.status = "completed"
                    rec.finished_at = time.time()
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    rec = self._jobs[job_id]
                    rec.status = "failed"
                    rec.detail = str(exc)
                    rec.finished_at = time.time()

        thread = threading.Thread(target=runner_wrapper, daemon=True)
        thread.start()
        return job_id


