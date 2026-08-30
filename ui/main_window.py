"""Main application window."""
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt

from app.config import APP_TITLE, APP_VERSION
from app.models import ValidationResult, ExecutionSummary
from app.validator import validate_ssr_file
from app.browser_controller import BrowserController
from app.worker import InvoicingWorker, LoginCheckWorker
from app.logger import ui_logger
from app.checkpoint import CheckpointStore

from ui.styles import QSS_STYLESHEET
from ui.drop_zone import DropZoneWidget
from ui.validation_table import ValidationTableWidget
from ui.log_viewer import LogViewerWidget
from ui.status_panel import StatusPanelWidget

STACK_BREAKPOINT = 1180


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.browser_controller = BrowserController()
        self.current_validation: Optional[ValidationResult] = None
        self.worker_thread: Optional[InvoicingWorker] = None
        self.login_worker: Optional[LoginCheckWorker] = None
        self._stacked_top = False

        self._init_window()
        self._init_layout()
        self._connect_signals()
        self._set_tab_order()

        ui_logger.set_callback(self._on_ui_log)
        ui_logger.log("INFO", "Application initialized. Ready for SSR batch processing.")

    def _init_window(self):
        self.setWindowTitle(f"{APP_TITLE} — {APP_VERSION}")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        self.setStyleSheet(QSS_STYLESHEET)

    def _metric_block(self, value_name: str, label: str):
        box = QVBoxLayout()
        box.setSpacing(0)
        value = QLabel("—")
        value.setObjectName("MetricValue")
        value.setAlignment(Qt.AlignLeft)
        caption = QLabel(label)
        caption.setObjectName("MetricLabel")
        box.addWidget(value)
        box.addWidget(caption)
        setattr(self, value_name, value)
        return box

    def _init_layout(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("HeaderCard")
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 10, 16, 10)
        h.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        kicker = QLabel("DP WORLD  GSC")
        kicker.setObjectName("AppHeaderKicker")
        title = QLabel(APP_TITLE)
        title.setObjectName("AppHeaderTitle")
        subtitle = QLabel("Attended SSR invoicing  ·  eLOGiPark  ·  No credentials stored")
        subtitle.setObjectName("AppHeaderSubtitle")
        subtitle.setWordWrap(True)
        title_col.addWidget(kicker)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        self.version_badge = QLabel(f"v{APP_VERSION.split()[0]}")
        self.version_badge.setObjectName("StepBadge")
        self.version_badge.setAlignment(Qt.AlignCenter)

        self.run_chip = QLabel("Idle")
        self.run_chip.setObjectName("RunChip")
        self.run_chip.setAlignment(Qt.AlignCenter)

        h.addLayout(title_col, 1)
        h.addWidget(self.version_badge, 0, Qt.AlignTop)
        h.addWidget(self.run_chip, 0, Qt.AlignTop)
        root.addWidget(header)

        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(8)

        self.top_splitter = QSplitter(Qt.Horizontal)
        self.top_splitter.setChildrenCollapsible(False)
        self.top_splitter.setHandleWidth(8)

        file_card = QFrame()
        file_card.setObjectName("Card")
        file_card.setMinimumWidth(320)
        fl = QVBoxLayout(file_card)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(8)

        file_head = QHBoxLayout()
        step1 = QLabel("STEP 1")
        step1.setObjectName("StepBadge")
        file_title = QLabel("Batch file")
        file_title.setObjectName("CardTitle")
        file_head.addWidget(step1)
        file_head.addWidget(file_title)
        file_head.addStretch()
        fl.addLayout(file_head)

        self.drop_zone = DropZoneWidget()
        fl.addWidget(self.drop_zone)

        metrics = QHBoxLayout()
        metrics.setSpacing(16)
        metrics.addLayout(self._metric_block("metric_jobs", "BOOKINGS"))
        metrics.addLayout(self._metric_block("metric_containers", "CONTAINERS"))
        metrics.addLayout(self._metric_block("metric_amount", "AMOUNT (INR)"))
        metrics.addStretch()
        fl.addLayout(metrics)
        fl.addStretch(1)

        action_card = QFrame()
        action_card.setObjectName("Card")
        action_card.setMinimumWidth(360)
        al = QVBoxLayout(action_card)
        al.setContentsMargins(14, 12, 14, 12)
        al.setSpacing(8)
        act_head = QHBoxLayout()
        step2 = QLabel("STEP 2")
        step2.setObjectName("StepBadge")
        act_title = QLabel("Session and run")
        act_title.setObjectName("CardTitle")
        act_head.addWidget(step2)
        act_head.addWidget(act_title)
        act_head.addStretch()
        al.addLayout(act_head)
        self.status_panel = StatusPanelWidget()
        al.addWidget(self.status_panel)
        al.addStretch(1)

        self.top_splitter.addWidget(file_card)
        self.top_splitter.addWidget(action_card)
        self.top_splitter.setStretchFactor(0, 2)
        self.top_splitter.setStretchFactor(1, 3)

        bottom = QWidget()
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self.bottom_splitter = QSplitter(Qt.Horizontal)
        self.bottom_splitter.setChildrenCollapsible(False)
        self.bottom_splitter.setHandleWidth(8)

        table_card = QFrame()
        table_card.setObjectName("Card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(14, 12, 14, 12)
        tl.setSpacing(8)
        table_head = QHBoxLayout()
        table_title = QLabel("Batch preview")
        table_title.setObjectName("CardTitle")
        self.table_meta = QLabel("No file")
        self.table_meta.setObjectName("SectionMeta")
        table_head.addWidget(table_title)
        table_head.addStretch()
        table_head.addWidget(self.table_meta)
        self.validation_table = ValidationTableWidget()
        tl.addLayout(table_head)
        tl.addWidget(self.validation_table, 1)

        log_card = QFrame()
        log_card.setObjectName("Card")
        ll = QVBoxLayout(log_card)
        ll.setContentsMargins(14, 12, 14, 12)
        ll.setSpacing(8)
        self.log_viewer = LogViewerWidget()
        ll.addWidget(self.log_viewer, 1)

        self.bottom_splitter.addWidget(table_card)
        self.bottom_splitter.addWidget(log_card)
        self.bottom_splitter.setStretchFactor(0, 3)
        self.bottom_splitter.setStretchFactor(1, 2)
        bl.addWidget(self.bottom_splitter)

        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(bottom)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 4)
        root.addWidget(self.main_splitter, 1)

        self.footer = QLabel("Ready.")
        self.footer.setObjectName("SectionMeta")
        root.addWidget(self.footer)

    def _set_tab_order(self):
        self.setTabOrder(self.drop_zone.browse_btn, self.status_panel.open_portal_btn)
        self.setTabOrder(self.status_panel.open_portal_btn, self.status_panel.start_bot_btn)
        self.setTabOrder(self.status_panel.start_bot_btn, self.status_panel.cancel_btn)
        self.setTabOrder(self.status_panel.cancel_btn, self.status_panel.open_folder_btn)

    def _set_run_chip(self, text: str):
        self.run_chip.setText(text)

    def _reset_metrics(self):
        self.metric_jobs.setText("—")
        self.metric_containers.setText("—")
        self.metric_amount.setText("—")
        self.table_meta.setText("No file")

    def _connect_signals(self):
        self.drop_zone.file_selected.connect(self._on_file_selected)
        self.status_panel.open_browser_clicked.connect(self._on_open_browser_clicked)
        self.status_panel.start_bot_clicked.connect(self._on_start_bot_clicked)
        self.status_panel.cancel_clicked.connect(self._on_cancel_clicked)

    def _on_ui_log(self, level: str, formatted: str):
        self.log_viewer.append_log(level, formatted)
        self.footer.setText(formatted)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        wide = self.width() >= STACK_BREAKPOINT
        want_horizontal = wide
        is_horizontal = self.top_splitter.orientation() == Qt.Horizontal
        if want_horizontal and not is_horizontal:
            self.top_splitter.setOrientation(Qt.Horizontal)
            self.top_splitter.setSizes([420, 620])
        elif not want_horizontal and is_horizontal:
            self.top_splitter.setOrientation(Qt.Vertical)
            self.top_splitter.setSizes([220, 320])

    def showEvent(self, event):
        super().showEvent(event)
        self.main_splitter.setSizes([340, 420])
        if self.top_splitter.orientation() == Qt.Horizontal:
            self.top_splitter.setSizes([480, 700])
        self.bottom_splitter.setSizes([720, 480])

    def _on_file_selected(self, file_path: str):
        ui_logger.log("INFO", f"Parsing and validating file: {file_path}")
        self.current_validation = validate_ssr_file(file_path)
        self.validation_table.display_result(self.current_validation)

        if self.current_validation.is_valid:
            total_jobs = len(self.current_validation.jobs)
            total_containers = self.current_validation.total_containers
            total_amt = self.current_validation.total_amount
            self.metric_jobs.setText(str(total_jobs))
            self.metric_containers.setText(str(total_containers))
            self.metric_amount.setText(f"{total_amt:,.0f}")
            self.table_meta.setText(f"{total_jobs} grouped bookings")
            self._set_run_chip("Ready")

            store = CheckpointStore.for_batch(
                self.current_validation.file_path,
                self.current_validation.file_name,
                self.current_validation.jobs,
            )
            already = store.completed_count()
            remaining = total_jobs - already
            resume_note = ""
            if already:
                resume_note = (
                    f" Checkpoint: {already} already completed, {remaining} remaining — "
                    "Start will skip finished bookings."
                )
                self.status_panel.set_running_state(False, resume=True)
            msg = (
                f"File valid: {self.current_validation.file_name} "
                f"({total_jobs} bookings, {total_containers} containers, INR {total_amt:,.2f})."
                f"{resume_note} Log in to eLOGiPark, then start."
            )
            self.status_panel.set_status(msg, state="valid")
            self.status_panel.start_bot_btn.setEnabled(True)
            ui_logger.log(
                "SUCCESS",
                f"Validation passed: {total_jobs} booking groups from "
                f"{self.current_validation.valid_rows_count} rows.{resume_note}",
            )
        else:
            self._reset_metrics()
            err_count = len(self.current_validation.errors)
            self.table_meta.setText(f"{err_count} validation error(s)")
            self._set_run_chip("Invalid file")
            msg = (
                f"Validation failed: {err_count} error(s) in {self.current_validation.file_name}. "
                "Fix the Excel file and upload again."
            )
            self.status_panel.set_status(msg, state="invalid")
            self.status_panel.start_bot_btn.setEnabled(False)
            ui_logger.log("ERROR", f"Validation failed: {err_count} issues detected.")
            for err in self.current_validation.errors[:5]:
                ui_logger.log("WARNING", f"  Row {err.row_number} [{err.column_name}]: {err.error_message}")
            if err_count > 5:
                ui_logger.log("WARNING", f"  … and {err_count - 5} more error(s).")

    def _on_open_browser_clicked(self):
        ui_logger.log("INFO", "Opening interactive eLOGiPark browser session...")
        try:
            self.browser_controller.launch_interactive_browser()
            ui_logger.log("SUCCESS", "Browser launched. Log in, then click Start.")
            self.status_panel.set_login_state("browser_open")
            self.status_panel.set_status(
                "Browser opened. Complete login on eLOGiPark, then start the bot.",
                state="neutral",
            )
            self._set_run_chip("Browser open")
        except Exception as e:
            ui_logger.log("ERROR", f"Failed to launch browser: {str(e)}")
            self.status_panel.set_login_state("failed", detail=f"Could not open browser: {str(e)}")
            self.status_panel.set_status(f"Browser could not be opened. {str(e)}", state="invalid")

    def _on_start_bot_clicked(self):
        if not self.current_validation or not self.current_validation.is_valid:
            self.status_panel.set_status(
                "No valid file loaded. Drop or browse a valid SSR Excel file first.",
                state="invalid",
            )
            ui_logger.log("WARNING", "Start clicked without a valid file.")
            return

        if not self.browser_controller.is_browser_open():
            ui_logger.log("INFO", "Browser not detected — launching portal now...")
            self._on_open_browser_clicked()
            self.status_panel.set_status(
                "Portal opened. Log in with credentials and MFA/OTP, then click Start.",
                state="neutral",
            )
            return

        if self.login_worker and self.login_worker.isRunning():
            return

        self.status_panel.set_login_state("checking")
        self.status_panel.set_status("Verifying login on eLOGiPark…", state="neutral")
        self.status_panel.start_bot_btn.setEnabled(False)
        self._set_run_chip("Checking login")

        ui_logger.log("INFO", "Verifying login status on eLOGiPark portal...")
        self.login_worker = LoginCheckWorker(self.browser_controller, parent=self)
        self.login_worker.sig_result.connect(self._on_login_check_finished)
        self.login_worker.start()

    def _on_login_check_finished(self, is_logged_in: bool, status_reason: str):
        if not is_logged_in:
            ui_logger.log("ERROR", f"Login verification failed: {status_reason}")
            self.status_panel.set_login_state("failed", detail=status_reason)
            self.status_panel.set_status(
                "Login verification failed. Complete login, then start again.",
                state="invalid",
            )
            self._set_run_chip("Login required")
            return

        if not self.current_validation or not self.current_validation.is_valid:
            self.status_panel.set_login_state("success")
            self.status_panel.set_status(
                "Login verified, but no valid file is loaded.",
                state="invalid",
            )
            return

        ui_logger.log("SUCCESS", f"Login verified: {status_reason}")
        self.status_panel.set_login_state("success")
        self.status_panel.set_status("Login verified. Starting invoicing…", state="valid")
        self.status_panel.set_running_state(True)
        self.drop_zone.setEnabled(False)
        self._set_run_chip("Running")

        self.worker_thread = InvoicingWorker(
            browser_controller=self.browser_controller,
            jobs=self.current_validation.jobs,
            file_path=self.current_validation.file_path,
            file_name=self.current_validation.file_name,
            parent=self,
        )
        self.worker_thread.sig_log.connect(self._on_ui_log)
        self.worker_thread.sig_progress.connect(self.status_panel.update_progress)
        self.worker_thread.sig_error.connect(self._on_worker_error)
        self.worker_thread.sig_waiting_user.connect(self._on_waiting_user)
        self.worker_thread.sig_finished.connect(self._on_worker_finished)
        self.worker_thread.start()

    def _on_worker_error(self, booking_no: str, error_msg: str):
        self.status_panel.set_status(f"Error on booking {booking_no}: {error_msg}", state="invalid")

    def _on_waiting_user(self, reason: str):
        ui_logger.log("WARNING", f"Paused — waiting for you: {reason}")
        self.status_panel.set_login_state("failed", detail=reason)
        self.status_panel.set_status(
            "Waiting for you. Restore the eLOGiPark session, then click Resume. "
            "Completed bookings will not run again.",
            state="warning",
        )
        self._set_run_chip("Waiting")

    def _on_worker_finished(self, summary: ExecutionSummary):
        waiting = summary.run_status == "waiting_user"
        resume = waiting or summary.run_status == "ready_to_resume"
        self.status_panel.set_running_state(False, resume=resume)
        self.drop_zone.setEnabled(True)

        if waiting:
            self.status_panel.progress_label.setText("Waiting for user")
            self._set_run_chip("Waiting")
            ui_logger.log("WARNING", f"Run paused ({summary.waiting_reason or 'session/login'}).")
            return

        self.status_panel.progress_label.setText("Completed")
        skip_bit = f" | {summary.skipped_jobs} skipped (already done)" if summary.skipped_jobs else ""

        if summary.failed_jobs == 0 and (summary.successful_jobs > 0 or summary.skipped_jobs > 0):
            self._set_run_chip("Done")
            ui_logger.log(
                "SUCCESS",
                f"All done. {summary.successful_jobs} processed this run{skip_bit} "
                f"| {summary.total_containers_processed} containers "
                f"| INR {summary.total_value_invoiced:,.2f} "
                f"| {len(summary.proof_screenshots)} screenshot(s).",
            )
            self.status_panel.set_status(
                f"Batch completed. {summary.successful_jobs} processed this run{skip_bit}. "
                "Proofs are in the completed folder.",
                state="valid",
            )
        else:
            self._set_run_chip("Finished")
            fail_detail = " | ".join(summary.errors[:3]) if summary.errors else "See the activity log."
            ui_logger.log(
                "WARNING",
                f"Batch finished ({summary.run_status}): {summary.successful_jobs} succeeded, "
                f"{summary.failed_jobs} failed{skip_bit}. {fail_detail}",
            )
            self.status_panel.set_status(
                f"Batch finished: {summary.successful_jobs} succeeded, {summary.failed_jobs} failed"
                f"{skip_bit}. {fail_detail}",
                state="warning",
            )

    def _on_cancel_clicked(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.cancel()
            self.status_panel.set_status("Cancellation requested. Stopping after the current booking…", state="warning")
            ui_logger.log("WARNING", "Cancel requested. Worker will stop after the current job.")
            self._set_run_chip("Cancelling")

    def closeEvent(self, event):
        if self.login_worker and self.login_worker.isRunning():
            self.login_worker.wait(2000)
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.cancel()
            self.worker_thread.wait(2000)
        self.browser_controller.cleanup()
        event.accept()
