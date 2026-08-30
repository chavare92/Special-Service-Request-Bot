"""Login status, progress, and run actions."""
import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from app.config import COMPLETED_DIR


class StatusPanelWidget(QWidget):
    open_browser_clicked = Signal()
    start_bot_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        login_row = QHBoxLayout()
        login_row.setSpacing(10)

        self.login_icon = QLabel("ID")
        self.login_icon.setObjectName("StepBadge")
        self.login_icon.setAlignment(Qt.AlignCenter)
        self.login_icon.setFixedWidth(36)

        login_info = QVBoxLayout()
        login_info.setSpacing(2)
        self.login_title = QLabel("eLOGiPark session")
        self.login_title.setObjectName("CardTitle")
        self.login_subtitle = QLabel(
            "Open the portal, log in with your credentials and OTP, then start the bot."
        )
        self.login_subtitle.setObjectName("SectionMeta")
        self.login_subtitle.setWordWrap(True)
        login_info.addWidget(self.login_title)
        login_info.addWidget(self.login_subtitle)

        self.login_pill = QLabel("Not checked")
        self.login_pill.setObjectName("PillIdle")
        self.login_pill.setAlignment(Qt.AlignCenter)
        self.login_pill.setMinimumWidth(120)
        self.login_pill.setMaximumWidth(160)
        self.login_pill.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        login_row.addWidget(self.login_icon, 0, Qt.AlignTop)
        login_row.addLayout(login_info, 1)
        login_row.addWidget(self.login_pill, 0, Qt.AlignTop)
        layout.addLayout(login_row)

        self.login_message_bar = QLabel("")
        self.login_message_bar.setObjectName("StatusInvalid")
        self.login_message_bar.setWordWrap(True)
        self.login_message_bar.setVisible(False)
        layout.addWidget(self.login_message_bar)

        self.status_banner = QLabel("Upload an SSR Excel file to begin.")
        self.status_banner.setObjectName("StatusNeutral")
        self.status_banner.setWordWrap(True)
        self.status_banner.setMaximumHeight(72)
        layout.addWidget(self.status_banner)

        self.progress_label = QLabel("Idle")
        self.progress_label.setObjectName("SectionMeta")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        self._btn_grid = QGridLayout()
        self._btn_grid.setSpacing(8)
        self._btn_grid.setContentsMargins(0, 0, 0, 0)

        self.open_portal_btn = QPushButton("Open portal")
        self.open_portal_btn.setCursor(Qt.PointingHandCursor)
        self.open_portal_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.open_portal_btn.setToolTip("Launch eLOGiPark in Edge or Chrome with remote debugging.")
        self.open_portal_btn.clicked.connect(self.open_browser_clicked.emit)

        self.start_bot_btn = QPushButton("Start bot")
        self.start_bot_btn.setObjectName("PrimaryBtn")
        self.start_bot_btn.setCursor(Qt.PointingHandCursor)
        self.start_bot_btn.setEnabled(False)
        self.start_bot_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_bot_btn.setToolTip("Validate login, then invoice remaining bookings.")
        self.start_bot_btn.clicked.connect(self.start_bot_clicked.emit)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("WarningBtn")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)

        self.open_folder_btn = QPushButton("Proofs folder")
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.open_folder_btn.setToolTip("Open the folder of audit screenshots.")
        self.open_folder_btn.clicked.connect(self._open_completed_folder)

        self._btn_grid.addWidget(self.open_portal_btn, 0, 0)
        self._btn_grid.addWidget(self.start_bot_btn, 0, 1)
        self._btn_grid.addWidget(self.cancel_btn, 1, 0)
        self._btn_grid.addWidget(self.open_folder_btn, 1, 1)
        self._btn_grid.setColumnStretch(0, 1)
        self._btn_grid.setColumnStretch(1, 1)
        layout.addLayout(self._btn_grid)

    def _apply_pill(self, object_name: str, text: str):
        self.login_pill.setObjectName(object_name)
        self.login_pill.setText(text)
        self.login_pill.style().unpolish(self.login_pill)
        self.login_pill.style().polish(self.login_pill)

    def set_login_state(self, state: str, detail: str = ""):
        if state == "checking":
            self.login_icon.setText("...")
            self._apply_pill("PillChecking", "Checking")
            self.login_subtitle.setText("Verifying login on the eLOGiPark portal.")
            self.login_message_bar.setVisible(False)
            self.start_bot_btn.setEnabled(False)
        elif state == "success":
            self.login_icon.setText("OK")
            self._apply_pill("PillSuccess", "Logged in")
            self.login_subtitle.setText("Session verified. The bot will continue with remaining bookings.")
            self.login_message_bar.setVisible(False)
        elif state == "failed":
            self.login_icon.setText("!")
            self._apply_pill("PillFailed", "Not logged in")
            self.login_subtitle.setText("Complete login on the portal, then click Start or Resume.")
            if detail:
                self.login_message_bar.setText(detail)
                self.login_message_bar.setVisible(True)
            else:
                self.login_message_bar.setVisible(False)
            self.start_bot_btn.setEnabled(True)
        elif state == "browser_open":
            self.login_icon.setText("Web")
            self._apply_pill("PillOpen", "Browser open")
            self.login_subtitle.setText("Portal is open. Log in with MFA/OTP, then start the bot.")
            self.login_message_bar.setVisible(False)
        else:
            self.login_icon.setText("ID")
            self._apply_pill("PillIdle", "Not checked")
            self.login_subtitle.setText(
                "Open the portal, log in with your credentials and OTP, then start the bot."
            )
            self.login_message_bar.setVisible(False)

    def set_status(self, text: str, state: str = "neutral"):
        state_map = {
            "valid": "StatusValid",
            "invalid": "StatusInvalid",
            "warning": "StatusWarning",
            "neutral": "StatusNeutral",
        }
        self.status_banner.setObjectName(state_map.get(state, "StatusNeutral"))
        self.status_banner.setText(text)
        self.status_banner.style().unpolish(self.status_banner)
        self.status_banner.style().polish(self.status_banner)

    def update_progress(self, current: int, total: int, status_text: str):
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        else:
            self.progress_bar.setValue(0)
        self.progress_label.setText(status_text)

    def set_running_state(self, is_running: bool, resume: bool = False):
        self.start_bot_btn.setEnabled(not is_running)
        self.open_portal_btn.setEnabled(not is_running)
        self.cancel_btn.setEnabled(is_running)
        if not is_running:
            self.start_bot_btn.setText("Resume bot" if resume else "Start bot")

    def _open_completed_folder(self):
        try:
            folder_path = str(COMPLETED_DIR.resolve())
            if os.name == "nt":
                os.startfile(folder_path)
            else:
                subprocess.Popen(["xdg-open", folder_path])
        except Exception:
            pass
