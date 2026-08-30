"""
Background Worker for Asynchronous Automation Execution
"""
import time
import traceback
from typing import List, Optional

from PySide6.QtCore import QThread, Signal

from app.browser_controller import BrowserController
from app.checkpoint import (
    CheckpointStore,
    RUN_CANCELLED,
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_READY_TO_RESUME,
    RUN_WAITING_USER,
)
from app.config import BATCH_TIMEOUT_SEC, MAX_JOB_RETRIES
from app.errors import (
    ErrorCategory,
    LoginRequiredError,
    SessionNotFoundError,
    WebsiteUnavailableError,
    classify_exception,
)
from app.logger import log_failure
from app.models import ExecutionSummary, InvoiceJob
from app.resilience import human_pause


class LoginCheckWorker(QThread):
    """Runs Playwright login inspection off the Qt GUI thread."""

    sig_result = Signal(bool, str)  # (is_logged_in, reason)

    def __init__(self, browser_controller: BrowserController, parent=None):
        super().__init__(parent)
        self.browser = browser_controller

    def run(self):
        try:
            ok, reason = self.browser.verify_login_status()
            self.sig_result.emit(ok, reason)
        except Exception as e:
            self.sig_result.emit(False, f"Login check failed: {e}")


class InvoicingWorker(QThread):
    """
    Background worker thread executing eLOGiPark SSR automation.
    Skips completed checkpointed bookings and pauses for login/outage instead of restarting.
    """
    sig_log = Signal(str, str)
    sig_progress = Signal(int, int, str)
    sig_job_completed = Signal(int, str, str)
    sig_error = Signal(str, str)
    sig_waiting_user = Signal(str)
    sig_finished = Signal(object)

    def __init__(
        self,
        browser_controller: BrowserController,
        jobs: List[InvoiceJob],
        file_path: str = "",
        file_name: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.browser = browser_controller
        self.jobs = jobs
        self.file_path = file_path
        self.file_name = file_name
        self._is_cancelled = False
        self.checkpoint = CheckpointStore.for_batch(file_path, file_name or "batch", jobs)

    def cancel(self):
        self._is_cancelled = True

    def _aborted(self) -> bool:
        return self._is_cancelled

    def run(self):
        total_jobs = len(self.jobs)
        already_done = self.checkpoint.completed_count()
        summary = ExecutionSummary(
            total_jobs=total_jobs,
            resumed=already_done > 0,
            run_status="in_progress",
        )
        started = time.time()
        self.checkpoint.set_run_status("in_progress")

        if already_done:
            self.sig_log.emit(
                "INFO",
                f"Resuming batch: {already_done} booking(s) already completed will be skipped.",
            )
        self.sig_log.emit("INFO", f"Starting automation for {total_jobs} grouped booking(s)...")

        for idx, job in enumerate(self.jobs, start=1):
            if self._is_cancelled:
                self.sig_log.emit("WARNING", "Execution cancelled by user.")
                self.checkpoint.set_run_status(RUN_CANCELLED)
                summary.run_status = RUN_CANCELLED
                break

            if time.time() - started > BATCH_TIMEOUT_SEC:
                msg = f"Batch timeout ({BATCH_TIMEOUT_SEC}s) reached. Remaining bookings were not started."
                self.sig_log.emit("ERROR", msg)
                self.checkpoint.set_run_status(RUN_READY_TO_RESUME, waiting_reason=msg)
                summary.run_status = RUN_READY_TO_RESUME
                summary.waiting_reason = msg
                summary.errors.append(msg)
                break

            rec = self.checkpoint.record(job)
            if rec.get("status") == "failed" and int(rec.get("retry_count") or 0) >= MAX_JOB_RETRIES + 1:
                self.sig_log.emit(
                    "WARNING",
                    f"Booking #{job.booking_no} retry limit reached "
                    f"({rec.get('retry_count')}). Not retrying.",
                )
                continue

            if self.checkpoint.is_completed(job):
                rec = self.checkpoint.record(job)
                self.sig_log.emit(
                    "INFO",
                    f"Skipping Booking #{job.booking_no} — already completed "
                    f"(checkpoint {rec.get('updated_at', '')}).",
                )
                summary.skipped_jobs += 1
                if rec.get("proof_path"):
                    summary.proof_screenshots.append(rec["proof_path"])
                self.sig_progress.emit(idx, total_jobs, f"Skipped completed Booking #{job.booking_no}")
                continue

            status_msg = (
                f"Processing Job {idx}/{total_jobs} — Booking #{job.booking_no} "
                f"({len(job.containers)} container(s))"
            )
            self.sig_progress.emit(idx - 1, total_jobs, status_msg)
            self.sig_log.emit("INFO", status_msg)
            human_pause("job")

            outcome = self._run_one_job(job)
            if outcome == "waiting":
                rec = self.checkpoint.record(job)
                summary.run_status = RUN_WAITING_USER
                summary.waiting_reason = rec.get("error_message") or "Waiting for user to restore the portal session."
                break
            if outcome == "success":
                rec = self.checkpoint.record(job)
                summary.successful_jobs += 1
                summary.total_containers_processed += len(job.containers)
                summary.total_value_invoiced += job.total_amount
                proof = rec.get("proof_path") or ""
                if proof:
                    summary.proof_screenshots.append(proof)
                self.sig_job_completed.emit(idx, job.booking_no, proof)
            elif outcome == "failed":
                rec = self.checkpoint.record(job)
                summary.failed_jobs += 1
                err = rec.get("error_message") or "Unknown error"
                cat = rec.get("error_category") or ErrorCategory.UNEXPECTED_ERROR.value
                summary.errors.append(f"Booking #{job.booking_no} [{cat}]: {err}")
                self.sig_error.emit(job.booking_no, err)

        if summary.run_status not in (RUN_WAITING_USER, RUN_READY_TO_RESUME, RUN_CANCELLED):
            if summary.failed_jobs and summary.successful_jobs + summary.failed_jobs + summary.skipped_jobs >= total_jobs:
                summary.run_status = RUN_FAILED if summary.successful_jobs == 0 else RUN_COMPLETED
            else:
                remaining = [
                    j for j in self.jobs
                    if not self.checkpoint.is_completed(j)
                    and self.checkpoint.record(j).get("status") != "failed"
                ]
                if remaining:
                    summary.run_status = RUN_READY_TO_RESUME
                else:
                    summary.run_status = RUN_COMPLETED
            self.checkpoint.set_run_status(summary.run_status)

        self.sig_progress.emit(total_jobs, total_jobs, "Processing completed.")
        self.sig_log.emit(
            "INFO",
            f"Batch finished ({summary.run_status}): {summary.successful_jobs} successful, "
            f"{summary.failed_jobs} failed, {summary.skipped_jobs} skipped as already completed.",
        )
        self.sig_finished.emit(summary)

    def _run_one_job(self, job: InvoiceJob) -> str:
        rec = self.checkpoint.record(job)
        attempts_used = int(rec.get("retry_count") or 0)
        max_tries = MAX_JOB_RETRIES + 1

        for attempt in range(1, max_tries + 1):
            if self._is_cancelled:
                return "cancelled"
            self.checkpoint.mark_in_progress(job, step="start")
            current_step = ["start"]

            def on_step(step: str):
                current_step[0] = step
                self.checkpoint.mark_step(job, step)

            try:
                proof_path = self.browser.process_job(
                    job,
                    log_callback=lambda msg: self.sig_log.emit("INFO", f"  ↳ {msg}"),
                    step_callback=on_step,
                    abort_check=self._aborted,
                )
                self.checkpoint.mark_completed(job, proof_path)
                self.sig_log.emit("SUCCESS", f"✓ Booking #{job.booking_no} completed successfully. Saved proof.")
                return "success"
            except (LoginRequiredError, SessionNotFoundError, WebsiteUnavailableError) as e:
                cat = e.category.value
                log_failure(
                    category=cat,
                    step=current_step[0],
                    record=job.booking_no,
                    error=str(e),
                    retry_count=attempt,
                    status="Waiting for User",
                )
                self.checkpoint.mark_failed(
                    job, category=cat, message=str(e), step=current_step[0]
                )
                # Keep in_progress semantically as waiting — remaining jobs resume later
                rec2 = self.checkpoint.record(job)
                rec2["status"] = "pending"
                self.checkpoint.save()
                reason = str(e)
                self.checkpoint.set_run_status(RUN_WAITING_USER, waiting_reason=reason)
                self.sig_log.emit("WARNING", f"Paused: {cat}. {reason}")
                self.sig_waiting_user.emit(reason)
                return "waiting"
            except Exception as e:
                cat = classify_exception(e).value
                err_msg = str(e)
                self.sig_log.emit(
                    "ERROR",
                    f"✗ Booking #{job.booking_no} attempt {attempt}/{max_tries} "
                    f"[{cat}] at step {current_step[0]}: {err_msg}",
                )
                self.sig_log.emit("ERROR", traceback.format_exc().strip().splitlines()[-1])
                log_failure(
                    category=cat,
                    step=current_step[0],
                    record=job.booking_no,
                    error=err_msg,
                    retry_count=attempt,
                    status="Failed" if attempt >= max_tries else "Retrying",
                )
                err_proof = self.browser.capture_screenshot(f"fail_{job.booking_no}")
                self.checkpoint.mark_failed(
                    job, category=cat, message=err_msg, step=current_step[0]
                )
                if attempt < max_tries:
                    self.sig_log.emit("WARNING", f"Retrying Booking #{job.booking_no} ({attempt + 1}/{max_tries})...")
                    human_pause("job")
                    continue
                return "failed"
        return "failed"
