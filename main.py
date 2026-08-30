"""
Application Launcher for SSR Attended Bot
"""
import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("DP World SSR Bot")
    app.setOrganizationName("DP World GSC")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
