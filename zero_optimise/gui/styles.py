"""
Garuda Linux Dark / Neon Theme Stylesheet for Zero-Optimise.
Crafted for KDE Plasma Wayland and Arch/Garuda desktop aesthetics.
"""

GARUDA_THEME = """
QMainWindow, QDialog {
    background-color: #0b0f19;
    color: #e2e8f0;
    font-family: 'Inter', 'Noto Sans', 'Segoe UI', sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: transparent;
    color: #e2e8f0;
}

QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 12px;
    background-color: #0f172a;
    top: -1px;
}

QTabBar::tab {
    background-color: #0b0f19;
    color: #94a3b8;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #0f172a;
    color: #00f0ff;
    border-bottom: 2px solid #00f0ff;
}

QTabBar::tab:hover:!selected {
    color: #38bdf8;
    background-color: #131d33;
}

/* Cards */
QFrame.CardFrame {
    background-color: #131d33;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 14px;
}

QFrame.CardFrame:hover {
    border: 1px solid #334155;
}

/* Progress Bars */
QProgressBar {
    background-color: #0b0f19;
    border: 1px solid #1e293b;
    border-radius: 8px;
    text-align: center;
    color: #f8fafc;
    font-weight: bold;
    font-size: 11px;
    height: 18px;
}

QProgressBar::chunk {
    border-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00b4d8, stop:1 #00f0ff);
}

QProgressBar.warning::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #fbbf24);
}

QProgressBar.danger::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #f87171);
}

/* Buttons */
QPushButton {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #00f0ff;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #0f172a;
}

QPushButton:disabled {
    background-color: #0f172a;
    color: #64748b;
    border-color: #1e293b;
}

/* Primary Boost Button */
QPushButton#PrimaryBoostButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0052d4, stop:0.5 #4364f7, stop:1 #6fb1fc);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-size: 15px;
    font-weight: bold;
}

QPushButton#PrimaryBoostButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4364f7, stop:1 #00f0ff);
}

QPushButton#PrimaryBoostButton:pressed {
    background-color: #0052d4;
}

/* Secondary Action Buttons */
QPushButton.ActionBtn {
    background-color: #131d33;
    border: 1px solid #2d3748;
    border-radius: 8px;
    font-size: 12px;
    padding: 8px 14px;
}

QPushButton.ActionBtn:hover {
    border-color: #38bdf8;
    background-color: #1e293b;
}

/* Table View */
QTableWidget {
    background-color: #0b0f19;
    border: 1px solid #1e293b;
    border-radius: 10px;
    gridline-color: #131d33;
    color: #e2e8f0;
    selection-background-color: #1e293b;
    selection-color: #00f0ff;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #1e293b;
    font-weight: bold;
    font-size: 12px;
}

QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #131d33;
}

/* Inputs & Filter Bar */
QLineEdit {
    background-color: #0b0f19;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 7px 12px;
    color: #f8fafc;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #00f0ff;
    background-color: #0f172a;
}

/* Log Text Edit */
QTextEdit {
    background-color: #070a12;
    border: 1px solid #1e293b;
    border-radius: 10px;
    color: #a5f3fc;
    font-family: 'JetBrains Mono', 'Fira Code', 'Monospace', monospace;
    font-size: 12px;
    padding: 10px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #0b0f19;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 25px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00f0ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
