"""Streaming log console."""
from html import escape
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor


class LogViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("Activity log")
        title.setObjectName("CardTitle")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("GhostBtn")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_logs)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.clear_btn)

        self.console = QTextEdit()
        self.console.setObjectName("LogConsole")
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(120)
        self.console.setAcceptRichText(True)

        layout.addLayout(header)
        layout.addWidget(self.console, 1)

    def append_log(self, level: str, message: str):
        color_map = {
            "INFO": "#93C5FD",
            "SUCCESS": "#34D399",
            "WARNING": "#FBBF24",
            "ERROR": "#F87171",
            "DEBUG": "#94A3B8",
        }
        color = color_map.get(level.upper(), "#E2E8F0")
        safe = escape(message)
        html_line = f"<span style='color:{color};'>{safe}</span><br>"
        self.console.moveCursor(QTextCursor.End)
        self.console.insertHtml(html_line)
        self.console.moveCursor(QTextCursor.End)

    def clear_logs(self):
        self.console.clear()
