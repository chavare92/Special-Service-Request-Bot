"""Persistent per-booking checkpoints so a crash never restarts a finished invoice."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.config import CHECKPOINT_DIR
from app.models import InvoiceJob

PENDING = "pending"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"
FAILED = "failed"
SKIPPED = "skipped"

RUN_IN_PROGRESS = "in_progress"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"
RUN_WAITING_USER = "waiting_user"
RUN_READY_TO_RESUME = "ready_to_resume"
RUN_CANCELLED = "cancelled"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def job_key(job: InvoiceJob) -> str:
    boxes = ",".join(sorted(c.upper() for c in job.containers))
    return (
        f"{job.booking_no}|{job.doc_type}|{job.invoice_to}|"
        f"{job.billing_party}|{job.service}|{job.rate}|{boxes}"
    )


def batch_id(file_name: str, jobs: List[InvoiceJob]) -> str:
    payload = file_name + "||" + "||".join(job_key(j) for j in jobs)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class CheckpointStore:
    """JSON checkpoint file with atomic replace."""

    def __init__(self, path: Path, data: dict):
        self.path = path
        self.data = data

    @classmethod
    def for_batch(cls, file_path: str, file_name: str, jobs: List[InvoiceJob]) -> "CheckpointStore":
        bid = batch_id(file_name, jobs)
        path = CHECKPOINT_DIR / f"batch_{bid}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = None
            if isinstance(data, dict) and data.get("batch_id") == bid:
                store = cls(path, data)
                store._ensure_jobs(jobs)
                return store
        data = {
            "schema": 1,
            "batch_id": bid,
            "file_path": str(file_path),
            "file_name": file_name,
            "run_status": RUN_READY_TO_RESUME,
            "current_job_key": "",
            "waiting_reason": "",
            "updated_at": _now(),
            "jobs": {},
        }
        store = cls(path, data)
        store._ensure_jobs(jobs)
        store.save()
        return store

    def _ensure_jobs(self, jobs: List[InvoiceJob]) -> None:
        records: Dict[str, dict] = self.data.setdefault("jobs", {})
        for job in jobs:
            key = job_key(job)
            if key not in records:
                records[key] = {
                    "job_key": key,
                    "booking_no": job.booking_no,
                    "status": PENDING,
                    "last_step": "",
                    "retry_count": 0,
                    "error_category": "",
                    "error_message": "",
                    "proof_path": "",
                    "updated_at": _now(),
                }

    def save(self) -> None:
        self.data["updated_at"] = _now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def record(self, job: InvoiceJob) -> dict:
        return self.data["jobs"][job_key(job)]

    def is_completed(self, job: InvoiceJob) -> bool:
        return self.record(job).get("status") == COMPLETED

    def completed_count(self) -> int:
        return sum(1 for r in self.data["jobs"].values() if r.get("status") == COMPLETED)

    def pending_jobs(self, jobs: List[InvoiceJob]) -> List[InvoiceJob]:
        return [j for j in jobs if not self.is_completed(j)]

    def set_run_status(self, status: str, waiting_reason: str = "") -> None:
        self.data["run_status"] = status
        self.data["waiting_reason"] = waiting_reason
        self.save()

    def mark_in_progress(self, job: InvoiceJob, step: str) -> None:
        rec = self.record(job)
        rec["status"] = IN_PROGRESS
        rec["last_step"] = step
        rec["updated_at"] = _now()
        self.data["current_job_key"] = job_key(job)
        self.data["run_status"] = RUN_IN_PROGRESS
        self.save()

    def mark_step(self, job: InvoiceJob, step: str) -> None:
        rec = self.record(job)
        rec["last_step"] = step
        rec["updated_at"] = _now()
        self.data["current_job_key"] = job_key(job)
        self.save()

    def mark_completed(self, job: InvoiceJob, proof_path: str = "") -> None:
        rec = self.record(job)
        rec["status"] = COMPLETED
        rec["last_step"] = "completed"
        rec["proof_path"] = proof_path or rec.get("proof_path", "")
        rec["error_message"] = ""
        rec["error_category"] = ""
        rec["updated_at"] = _now()
        self.save()

    def mark_failed(
        self,
        job: InvoiceJob,
        *,
        category: str,
        message: str,
        step: str = "",
    ) -> None:
        rec = self.record(job)
        rec["status"] = FAILED
        rec["error_category"] = category
        rec["error_message"] = message
        rec["retry_count"] = int(rec.get("retry_count") or 0) + 1
        if step:
            rec["last_step"] = step
        rec["updated_at"] = _now()
        self.save()

    def bump_retry(self, job: InvoiceJob) -> int:
        rec = self.record(job)
        rec["retry_count"] = int(rec.get("retry_count") or 0) + 1
        rec["updated_at"] = _now()
        self.save()
        return rec["retry_count"]
