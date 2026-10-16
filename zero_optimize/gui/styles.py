"""
Zero-Optimize Modern Minimal Theme.
Crafted to match zero.skillissue.gg and zero-music desktop web luxury aesthetic:
- 250px left sidebar navigation with SVG icons and active accents
- OLED pure dark canvas (#050507, #08080B)
- Ultra-clean cards with subtle borders (rgba(255, 255, 255, 0.06))
- Clean typography: Inter + JetBrains Mono
- Zero AI-slop badges, zero gradients, zero gimmicks
"""

ZERO_THEME = """
/* ── Universal Reset ── */
QWidget {
    background-color: #050507;
    color: #FFFFFF;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: rgba(249, 115, 22, 0.25);
    selection-color: #FFFFFF;
}

/* ── Left Sidebar (250px Luxury App Nav) ── */
#Sidebar {
    background-color: #08080B;
    border-right: 1px solid rgba(255, 255, 255, 0.06);
    min-width: 240px;
    max-width: 240px;
}

#SidebarBrand {
    padding: 16px 12px 14px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.SidebarBlockTitle {
    color: #52525B;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    padding: 14px 12px 6px 12px;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}

QPushButton.SidebarNavBtn {
    text-align: left;
    height: 38px;
    padding: 0 12px;
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: #A1A1AA;
    font-size: 13px;
    font-weight: 500;
}

QPushButton.SidebarNavBtn:hover {
    color: #FFFFFF;
    background-color: rgba(255, 255, 255, 0.05);
}

QPushButton.SidebarNavBtn[active="true"] {
    color: #FFFFFF;
    background-color: rgba(255, 255, 255, 0.09);
    font-weight: 600;
}

/* ── Main Canvas ── */
#MainStage {
    background-color: #050507;
    padding: 24px;
}

/* ── Cards & Frames ── */
QFrame.MetricCard {
    background-color: #0B0B0F;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 16px;
}

QFrame.MetricCard:hover {
    border-color: rgba(255, 255, 255, 0.12);
}

QLabel.CardTitle {
    color: #71717A;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

QLabel.CardValue {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.5px;
    font-family: 'JetBrains Mono', monospace;
}

QLabel.CardSub {
    color: #52525B;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Primary Action Buttons ── */
QPushButton#PrimaryAction {
    background-color: #FFFFFF;
    color: #000000;
    border: none;
    border-radius: 8px;
    font-weight: 700;
    font-size: 13px;
    height: 38px;
    padding: 0 18px;
}

QPushButton#PrimaryAction:hover {
    background-color: #F4F4F5;
}

QPushButton.SecondaryAction {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    color: #FFFFFF;
    font-weight: 500;
    font-size: 12px;
    height: 36px;
    padding: 0 14px;
}

QPushButton.SecondaryAction:hover {
    background-color: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.16);
}

/* ── Process Table ── */
QTableWidget {
    background-color: #0B0B0F;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    gridline-color: transparent;
    font-size: 12px;
    color: #FFFFFF;
    outline: none;
}

QTableWidget::item {
    color: #FFFFFF;
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

QTableWidget::item:selected {
    background-color: rgba(255, 255, 255, 0.08);
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #0B0B0F;
    color: #71717A;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    padding: 10px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Search Input ── */
QLineEdit#SearchBar {
    background-color: #0E0E14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px 14px;
    color: #FFFFFF;
    font-size: 12px;
}

QLineEdit#SearchBar:focus {
    border-color: rgba(249, 115, 22, 0.5);
}

/* ── Minimal Scrollbar ── */
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
