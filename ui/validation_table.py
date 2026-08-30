"""Batch preview and validation diagnostics."""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.models import ValidationResult, InvoiceJob, ValidationErrorDetail


class ValidationTableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _style_table(self, table: QTableWidget):
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stacked_widget = QStackedWidget()

        self.empty_page = QLabel("No file loaded. Drop an Excel file above to preview bookings.")
        self.empty_page.setObjectName("EmptyState")
        self.empty_page.setAlignment(Qt.AlignCenter)
        self.empty_page.setWordWrap(True)
        self.stacked_widget.addWidget(self.empty_page)

        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(7)
        self.jobs_table.setHorizontalHeaderLabels([
            "Booking", "Doc type", "Invoice to", "Billing party", "Service", "Containers", "Rate (INR)"
        ])
        header = self.jobs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self._style_table(self.jobs_table)
        self.stacked_widget.addWidget(self.jobs_table)

        self.errors_table = QTableWidget()
        self.errors_table.setColumnCount(4)
        self.errors_table.setHorizontalHeaderLabels([
            "Row", "Column", "Value", "Error"
        ])
        eh = self.errors_table.horizontalHeader()
        eh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        eh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        eh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        eh.setSectionResizeMode(3, QHeaderView.Stretch)
        self._style_table(self.errors_table)
        self.stacked_widget.addWidget(self.errors_table)

        layout.addWidget(self.stacked_widget)

    def display_result(self, result: ValidationResult):
        if not result:
            self.stacked_widget.setCurrentIndex(0)
            return
        if result.is_valid:
            self._populate_jobs_table(result.jobs)
            self.stacked_widget.setCurrentIndex(1)
        else:
            self._populate_errors_table(result.errors)
            self.stacked_widget.setCurrentIndex(2)

    def _populate_jobs_table(self, jobs: List[InvoiceJob]):
        self.jobs_table.setRowCount(len(jobs))
        for r_idx, job in enumerate(jobs):
            preview = f"{len(job.containers)}  {', '.join(job.containers[:2])}"
            if len(job.containers) > 2:
                preview += "…"
            values = [
                job.booking_no,
                job.doc_type,
                job.invoice_to,
                job.billing_party,
                job.service,
                preview,
                f"{job.rate:,.2f}",
            ]
            for c_idx, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.setToolTip(text)
                self.jobs_table.setItem(r_idx, c_idx, item)

    def _populate_errors_table(self, errors: List[ValidationErrorDetail]):
        self.errors_table.setRowCount(len(errors))
        for r_idx, err in enumerate(errors):
            row_str = f"Row {err.row_number}" if err.row_number > 0 else "Header"
            values = [row_str, err.column_name, str(err.invalid_value), err.error_message]
            for c_idx, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.setForeground(QColor("#FCA5A5"))
                item.setToolTip(text)
                self.errors_table.setItem(r_idx, c_idx, item)
