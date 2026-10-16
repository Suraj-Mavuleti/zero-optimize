"""
Zero-Optimize Theme Stylesheet.
Faithfully designed to match the high-end aesthetic of zero.skillissue.gg:
Pitch black (#0A0A0A), glassmorphic cards, JetBrains Mono readouts,
S-tier rating badges, and sleek orange/neon accents.
"""

ZERO_THEME = """
QMainWindow, QDialog {
    background-color: #0A0A0A;
    color: #F3F4F6;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: transparent;
    color: #F3F4F6;
}

/* Glassmorphic Container Cards */
QFrame.CardFrame {
    background-color: #111111;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 14px;
}

QFrame.CardFrame:hover {
    border: 1px solid rgba(255, 255, 255, 0.16);
    background-color: #141414;
}

/* Hero / Header Container */
QFrame#HeaderCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #121212, stop:1 #0c0c0c);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 14px;
    padding: 14px 18px;
}

/* Navigation Tabs */
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    background-color: #0D0D0D;
    top: -1px;
}

QTabBar::tab {
    background-color: #0A0A0A;
    color: #9CA3AF;
    padding: 9px 20px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
    font-size: 12px;
    border: 1px solid transparent;
}

QTabBar::tab:selected {
    background-color: #0D0D0D;
    color: #F3F4F6;
    border-top: 1px solid rgba(255, 255, 255, 0.15);
    border-left: 1px solid rgba(255, 255, 255, 0.08);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    border-bottom: 2px solid #F97316;
}

QTabBar::tab:hover:!selected {
    color: #E5E7EB;
    background-color: #141414;
}

/* Sleek Metrics Bars (Matching zero.skillissue.gg profile metrics) */
QProgressBar {
    background-color: rgba(255, 255, 255, 0.05);
    border: none;
    border-radius: 4px;
    text-align: right;
    color: transparent;
    height: 6px;
}

QProgressBar::chunk {
    border-radius: 4px;
    background: #10B981;
}

QProgressBar.blue::chunk {
    background: #3B82F6;
}

QProgressBar.orange::chunk {
    background: #F97316;
}

QProgressBar.amber::chunk {
    background: #F59E0B;
}

QProgressBar.purple::chunk {
    background: #8B5CF6;
}

QProgressBar.pink::chunk {
    background: #EC4899;
}

/* Sleek zero.skillissue.gg Buttons */
QPushButton {
    background-color: #171717;
    color: #E5E7EB;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #212121;
    border-color: rgba(255, 255, 255, 0.22);
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #0e0e0e;
}

QPushButton:disabled {
    background-color: #121212;
    color: #525252;
    border-color: rgba(255, 255, 255, 0.04);
}

/* Primary Orange Action Button (zero.skillissue.gg style) */
QPushButton#PrimaryActionButton {
    background: #F97316;
    color: #000000;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

QPushButton#PrimaryActionButton:hover {
    background: #FB923C;
    color: #000000;
}

QPushButton#PrimaryActionButton:pressed {
    background: #EA580C;
}

/* Real-time Status Badge */
QLabel#LiveStatusBadge {
    background-color: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.25);
    color: #10B981;
    border-radius: 6px;
    padding: 3px 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
}

/* Tier S Badge */
QLabel#TierBadge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #A855F7, stop:1 #EC4899);
    color: #FFFFFF;
    font-weight: 900;
    font-size: 12px;
    padding: 2px 7px;
    border-radius: 4px;
}

/* Process Table */
QTableWidget {
    background-color: #0A0A0A;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    gridline-color: rgba(255, 255, 255, 0.04);
    color: #E5E7EB;
    selection-background-color: rgba(249, 115, 22, 0.12);
    selection-color: #FFFFFF;
    font-family: 'JetBrains Mono', 'Inter', monospace;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #111111;
    color: #9CA3AF;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

/* Inputs & Filter Search Bar */
QLineEdit {
    background-color: #111111;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 12px;
    color: #F3F4F6;
    font-size: 12px;
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
}

QLineEdit:focus {
    border: 1px solid #F97316;
    background-color: #141414;
}

/* Text Edit / Logs */
QTextEdit {
    background-color: #070707;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    color: #E5E7EB;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 12px;
    padding: 12px;
    line-height: 1.6;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #0A0A0A;
    width: 6px;
    margin: 0;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background-color: rgba(255, 255, 255, 0.15);
    min-height: 25px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background-color: #F97316;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
