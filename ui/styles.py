"""
Design system for the SSR Attended Bot (single QSS source).
"""

QSS_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0B1220;
    color: #E8EEF6;
    font-family: 'Segoe UI', 'Segoe UI Variable', sans-serif;
    font-size: 13px;
}

QLabel {
    background: transparent;
    border: none;
}

QFrame#HeaderCard {
    background-color: #121A2B;
    border: 1px solid #2A3548;
    border-radius: 12px;
}

QLabel#AppHeaderKicker {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #38BDF8;
}

QLabel#AppHeaderTitle {
    font-size: 18px;
    font-weight: 700;
    color: #F8FAFC;
}

QLabel#AppHeaderSubtitle {
    font-size: 12px;
    color: #8B9BB4;
}

QFrame#Card {
    background-color: #151C2C;
    border: 1px solid #2A3548;
    border-radius: 12px;
}

QLabel#StepBadge {
    background-color: #0284C7;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 8px;
}

QLabel#CardTitle {
    font-size: 13px;
    font-weight: 650;
    color: #F1F5F9;
}

QLabel#MetricValue {
    font-size: 16px;
    font-weight: 700;
    color: #38BDF8;
}

QLabel#MetricLabel {
    font-size: 10px;
    font-weight: 600;
    color: #8B9BB4;
}

QFrame#DropZone {
    background-color: #0B1220;
    border: 1px dashed #3D4D66;
    border-radius: 10px;
}

QFrame#DropZone:hover {
    border-color: #38BDF8;
    background-color: #102033;
}

QLabel#DropPrimary {
    font-size: 13px;
    font-weight: 650;
    color: #F1F5F9;
}

QLabel#DropSecondary {
    font-size: 11px;
    color: #8B9BB4;
}

QPushButton {
    background-color: #243044;
    color: #F8FAFC;
    border: 1px solid #3D4D66;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
    font-size: 13px;
    min-height: 36px;
}

QPushButton:hover {
    background-color: #2E3D56;
    border-color: #5B6B84;
}

QPushButton:pressed {
    background-color: #1B2638;
}

QPushButton:disabled {
    background-color: #161E2E;
    color: #4B5A70;
    border-color: #243044;
}

QPushButton#PrimaryBtn {
    background-color: #0284C7;
    border: 1px solid #0369A1;
    color: #FFFFFF;
    font-weight: 700;
}

QPushButton#PrimaryBtn:hover {
    background-color: #0369A1;
}

QPushButton#PrimaryBtn:disabled {
    background-color: #16324A;
    color: #4B6B84;
    border-color: #1E3A54;
}

QPushButton#WarningBtn {
    background-color: #B45309;
    border: 1px solid #92400E;
    color: #FFFFFF;
}

QPushButton#WarningBtn:hover {
    background-color: #C2410C;
}

QPushButton#WarningBtn:disabled {
    background-color: #161E2E;
    color: #4B5A70;
    border-color: #243044;
}

QPushButton#GhostBtn {
    background-color: transparent;
    border: 1px solid #3D4D66;
    color: #C5D0E0;
    min-height: 28px;
    padding: 4px 10px;
    font-size: 12px;
}

QPushButton#GhostBtn:hover {
    background-color: #1B2638;
    border-color: #38BDF8;
    color: #F8FAFC;
}

QLabel#StatusValid, QLabel#StatusInvalid, QLabel#StatusWarning, QLabel#StatusNeutral {
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
    font-size: 12px;
}

QLabel#StatusValid {
    background-color: rgba(16, 185, 129, 0.12);
    color: #34D399;
    border: 1px solid #059669;
}

QLabel#StatusInvalid {
    background-color: rgba(239, 68, 68, 0.12);
    color: #FCA5A5;
    border: 1px solid #DC2626;
}

QLabel#StatusWarning {
    background-color: rgba(245, 158, 11, 0.12);
    color: #FBBF24;
    border: 1px solid #D97706;
}

QLabel#StatusNeutral {
    background-color: #0B1220;
    color: #8B9BB4;
    border: 1px solid #2A3548;
}

QLabel#PillIdle, QLabel#PillChecking, QLabel#PillSuccess, QLabel#PillFailed, QLabel#PillOpen {
    border-radius: 14px;
    font-size: 11px;
    font-weight: 650;
    padding: 4px 12px;
    min-width: 118px;
}

QLabel#PillIdle {
    background-color: #0B1220;
    color: #8B9BB4;
    border: 1px solid #3D4D66;
}

QLabel#PillChecking {
    background-color: rgba(245, 158, 11, 0.14);
    color: #FBBF24;
    border: 1px solid #D97706;
}

QLabel#PillSuccess {
    background-color: rgba(16, 185, 129, 0.14);
    color: #34D399;
    border: 1px solid #059669;
}

QLabel#PillFailed {
    background-color: rgba(239, 68, 68, 0.14);
    color: #F87171;
    border: 1px solid #DC2626;
}

QLabel#PillOpen {
    background-color: rgba(56, 189, 248, 0.14);
    color: #38BDF8;
    border: 1px solid #0284C7;
}

QLabel#RunChip {
    background-color: #0B1220;
    color: #8B9BB4;
    border: 1px solid #2A3548;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 650;
}

QTableWidget {
    background-color: #0B1220;
    border: 1px solid #2A3548;
    border-radius: 8px;
    gridline-color: #1E293B;
    color: #E8EEF6;
    selection-background-color: #0369A1;
    alternate-background-color: #101827;
}

QHeaderView::section {
    background-color: #1B2436;
    color: #8B9BB4;
    padding: 7px 8px;
    border: 1px solid #2A3548;
    font-weight: 650;
    font-size: 11px;
}

QTextEdit#LogConsole {
    background-color: #070B14;
    color: #E2E8F0;
    border: 1px solid #1E293B;
    border-radius: 8px;
    font-family: 'Cascadia Mono', 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    padding: 8px;
}

QProgressBar {
    background-color: #0B1220;
    border: 1px solid #2A3548;
    border-radius: 7px;
    text-align: center;
    color: #F8FAFC;
    font-weight: 600;
    font-size: 11px;
    min-height: 16px;
    max-height: 18px;
}

QProgressBar::chunk {
    background-color: #0284C7;
    border-radius: 6px;
}

QSplitter::handle {
    background-color: #1B2436;
}

QSplitter::handle:horizontal { width: 8px; }
QSplitter::handle:vertical { height: 8px; }

QSplitter::handle:hover {
    background-color: #0284C7;
}

QScrollBar:vertical {
    border: none;
    background: #0B1220;
    width: 8px;
    margin: 2px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover { background: #475569; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    border: none;
    background: #0B1220;
    height: 8px;
    margin: 2px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: #334155;
    min-width: 24px;
    border-radius: 4px;
}

QLabel#EmptyState {
    color: #64748B;
    font-style: italic;
    padding: 24px;
}

QLabel#SectionMeta {
    font-size: 11px;
    color: #8B9BB4;
}
"""
