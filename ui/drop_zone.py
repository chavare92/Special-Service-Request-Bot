"""Compact drag-and-drop Excel upload."""
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFontMetrics


class DropZoneWidget(QFrame):
    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self._current_file_path = ""
        self._full_path_text = "Supports .xlsx, .xls, .xlsm"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.setMinimumHeight(96)
        self.setMaximumHeight(132)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel("SSR")
        self.icon_label.setObjectName("StepBadge")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedWidth(40)

        self.primary_label = QLabel("Drop an SSR Excel file here, or browse")
        self.primary_label.setObjectName("DropPrimary")
        self.primary_label.setAlignment(Qt.AlignCenter)
        self.primary_label.setWordWrap(True)

        self.secondary_label = QLabel(self._full_path_text)
        self.secondary_label.setObjectName("DropSecondary")
        self.secondary_label.setAlignment(Qt.AlignCenter)
        self.secondary_label.setToolTip("")

        self.browse_btn = QPushButton("Browse file")
        self.browse_btn.setObjectName("GhostBtn")
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.setFixedWidth(120)
        self.browse_btn.clicked.connect(self._open_file_dialog)

        top = QHBoxLayout()
        top.setAlignment(Qt.AlignCenter)
        top.addWidget(self.icon_label)

        layout.addLayout(top)
        layout.addWidget(self.primary_label)
        layout.addWidget(self.secondary_label)
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_row.addWidget(self.browse_btn)
        layout.addLayout(btn_row)

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SSR Excel Batch File",
            "",
            "Excel Files (*.xlsx *.xls *.xlsm);;All Files (*.*)",
        )
        if file_path:
            self.set_file(file_path)

    def set_file(self, file_path: str):
        path = Path(file_path)
        if path.suffix.lower() in [".xlsx", ".xls", ".xlsm"]:
            self._current_file_path = str(path)
            self.icon_label.setText("OK")
            self.primary_label.setText(path.name)
            self._full_path_text = str(path)
            self.secondary_label.setToolTip(str(path))
            self._elide_path()
            self.file_selected.emit(str(path))
        else:
            self._full_path_text = "Invalid format. Choose an Excel (.xlsx / .xls / .xlsm) file."
            self.secondary_label.setText(self._full_path_text)

    def reset(self):
        self._current_file_path = ""
        self.icon_label.setText("SSR")
        self.primary_label.setText("Drop an SSR Excel file here, or browse")
        self._full_path_text = "Supports .xlsx, .xls, .xlsm"
        self.secondary_label.setToolTip("")
        self.secondary_label.setText(self._full_path_text)

    def _elide_path(self):
        metrics = QFontMetrics(self.secondary_label.font())
        width = max(80, self.width() - 28)
        self.secondary_label.setText(metrics.elidedText(self._full_path_text, Qt.ElideMiddle, width))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_file_path:
            self._elide_path()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".xlsx", ".xls", ".xlsm")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if local_path.lower().endswith((".xlsx", ".xls", ".xlsm")):
                    self.set_file(local_path)
                    event.acceptProposedAction()
                    return
        event.ignore()
