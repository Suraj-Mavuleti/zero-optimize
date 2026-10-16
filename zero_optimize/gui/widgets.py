"""
Custom UI widgets for Zero-Optimize application matching zero.skillissue.gg style.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class StatCard(QFrame):
    def __init__(self, title: str, subtitle: str = "", bar_color: str = "#10B981", parent=None):
        super().__init__(parent)
        self.setProperty("class", "CardFrame")
        self.setObjectName("CardFrame")
        self.bar_color = bar_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Header Row: Title + Subtitle
        header = QHBoxLayout()
        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        
        self.metric_score_lbl = QLabel("0.0%")
        self.metric_score_lbl.setStyleSheet("color: #FFFFFF; font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700;")
        
        header.addWidget(self.title_lbl)
        header.addStretch()
        header.addWidget(self.metric_score_lbl)
        layout.addLayout(header)

        # Main Value Readout (e.g. 6.2 GB / 7.5 GB or 18% Load)
        self.value_lbl = QLabel("0.0 %")
        self.value_lbl.setStyleSheet("color: #FFFFFF; font-family: 'JetBrains Mono', monospace; font-weight: 800; font-size: 22px; letter-spacing: -0.5px;")
        layout.addWidget(self.value_lbl)

        # Slim Progress Bar (6px, matching zero.skillissue.gg)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self._apply_bar_color(self.bar_color)
        layout.addWidget(self.progress_bar)

        # Bottom detail row
        self.detail_lbl = QLabel(subtitle)
        self.detail_lbl.setStyleSheet("color: #6B7280; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        layout.addWidget(self.detail_lbl)

    def _apply_bar_color(self, color: str):
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)

    def update_stat(self, percent: float, main_text: str, detail_text: str = None):
        self.metric_score_lbl.setText(f"{percent:.1f}%")
        self.value_lbl.setText(main_text)
        self.progress_bar.setValue(int(min(100, max(0, percent))))
        if detail_text is not None:
            self.detail_lbl.setText(detail_text)

        # Dynamic color adaptation
        if percent >= 88.0:
            col = "#EF4444"  # Red
        elif percent >= 75.0:
            col = "#F59E0B"  # Amber
        else:
            col = self.bar_color

        self._apply_bar_color(col)


class ProcessActionWidget(QWidget):
    freeze_clicked = pyqtSignal(int)
    thaw_clicked = pyqtSignal(int)
    renice_clicked = pyqtSignal(int)
    kill_clicked = pyqtSignal(int)

    def __init__(self, pid: int, is_frozen: bool, is_protected: bool, is_throttled: bool, parent=None):
        super().__init__(parent)
        self.pid = pid
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        if not is_protected:
            # Throttle Button
            self.btn_renice = QPushButton("Throttled" if is_throttled else "Throttle")
            self.btn_renice.setEnabled(not is_throttled)
            self.btn_renice.setStyleSheet("""
                QPushButton {
                    background-color: rgba(249, 115, 22, 0.12);
                    color: #FB923C;
                    border: 1px solid rgba(249, 115, 22, 0.3);
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                    font-family: -apple-system, sans-serif;
                }
                QPushButton:hover {
                    background-color: #F97316;
                    color: #000000;
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.03);
                    color: #6B7280;
                    border-color: rgba(255, 255, 255, 0.06);
                }
            """)
            self.btn_renice.clicked.connect(lambda: self.renice_clicked.emit(self.pid))
            layout.addWidget(self.btn_renice)

            # Freeze / Thaw Button
            if is_frozen:
                self.btn_freeze = QPushButton("Resume")
                self.btn_freeze.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(16, 185, 129, 0.15);
                        color: #10B981;
                        border: 1px solid rgba(16, 185, 129, 0.35);
                        border-radius: 5px;
                        padding: 3px 8px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                    QPushButton:hover { background-color: #10B981; color: #000000; }
                """)
                self.btn_freeze.clicked.connect(lambda: self.thaw_clicked.emit(self.pid))
            else:
                self.btn_freeze = QPushButton("Freeze")
                self.btn_freeze.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(245, 158, 11, 0.12);
                        color: #FBBF24;
                        border: 1px solid rgba(245, 158, 11, 0.3);
                        border-radius: 5px;
                        padding: 3px 8px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                    QPushButton:hover { background-color: #F59E0B; color: #000000; }
                """)
                self.btn_freeze.clicked.connect(lambda: self.freeze_clicked.emit(self.pid))
            layout.addWidget(self.btn_freeze)

            # Kill Button
            self.btn_kill = QPushButton("End")
            self.btn_kill.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.12);
                    color: #F87171;
                    border: 1px solid rgba(239, 68, 68, 0.25);
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover { background-color: #EF4444; color: #FFFFFF; }
            """)
            self.btn_kill.clicked.connect(lambda: self.kill_clicked.emit(self.pid))
            layout.addWidget(self.btn_kill)
        else:
            lbl = QLabel("SYSTEM PROTECTED")
            lbl.setStyleSheet("color: #4B5563; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
            layout.addWidget(lbl)

        layout.addStretch()
