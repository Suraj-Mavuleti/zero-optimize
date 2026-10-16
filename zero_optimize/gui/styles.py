"""
Zero-Optimize Modern Minimal GUI Theme.
Pure OLED dark luxe styling matching zero.skillissue.gg aesthetic.
"""

ZERO_THEME = """
QMainWindow, QWidget {
    background-color: #050507;
    color: #FFFFFF;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
}

QFrame#HeaderCard {
    background-color: #0A0A0E;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
}

QFrame.CardFrame {
    background-color: #0E0E14;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
}

QLabel#CardTitle {
    color: #A1A1AA;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel#CardValue {
    color: #FFFFFF;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.5px;
}

QLabel#CardSub {
    color: #71717A;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
}

QLabel#LiveStatusBadge {
    background: rgba(249, 115, 22, 0.12);
    border: 1px solid rgba(249, 115, 22, 0.35);
    color: #FB923C;
    border-radius: 9999px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}

QPushButton {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    color: #FFFFFF;
    font-weight: 600;
    padding: 7px 14px;
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.18);
}

QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.03);
}

QPushButton#PrimaryActionButton {
    background-color: #FFFFFF;
    color: #000000;
    border: none;
    border-radius: 9999px;
    font-weight: 800;
    font-size: 13px;
    padding: 10px 20px;
}

QPushButton#PrimaryActionButton:hover {
    background-color: #F3F4F6;
}

QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: #0A0A0E;
    border-radius: 12px;
    top: -1px;
}

QTabBar::tab {
    background: transparent;
    color: #71717A;
    font-weight: 600;
    padding: 8px 18px;
    margin-right: 4px;
    border-radius: 8px;
    font-size: 12px;
}

QTabBar::tab:selected {
    color: #FFFFFF;
    background: rgba(255, 255, 255, 0.06);
}

QTabBar::tab:hover:!selected {
    color: #A1A1AA;
}

QTableWidget {
    background-color: transparent;
    border: none;
    gridline-color: transparent;
    selection-background-color: rgba(255, 255, 255, 0.06);
    selection-color: #FFFFFF;
    font-size: 12px;
}

QHeaderView::section {
    background-color: #0A0A0E;
    color: #71717A;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLineEdit {
    background-color: #0E0E14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 7px 12px;
    color: #FFFFFF;
    font-size: 12px;
}

QLineEdit:focus {
    border-color: rgba(249, 115, 22, 0.5);
}

QProgressBar {
    background-color: rgba(255, 255, 255, 0.05);
    border: none;
    border-radius: 3px;
    height: 5px;
    text-align: right;
}

QProgressBar::chunk {
    border-radius: 3px;
}

QTextEdit {
    background-color: #07070A;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    color: #D1D5DB;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 8px;
}

QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 3px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.25);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
