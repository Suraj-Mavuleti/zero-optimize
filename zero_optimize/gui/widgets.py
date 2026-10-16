"""
Zero-Optimize Custom GUI Widgets.
Clean, modern stat indicators and process controls.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QWidget, QPushButton
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class StatCard(QFrame):
    def __init__(self, title: str, subtitle: str = "", bar_color: str = "#F97316"):
        super().__init__()
        self.setProperty("class", "CardFrame")
        self.bar_color = bar_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Header: Title + Percentage
        header = QHBoxLayout()
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("CardTitle")
        header.addWidget(self.title_lbl)
        header.addStretch()

        self.metric_pct_lbl = QLabel("0.0%")
        self.metric_pct_lbl.setStyleSheet("color: #FFFFFF; font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700;")
        header.addWidget(self.metric_pct_lbl)
        layout.addLayout(header)

        # Value
        self.val_lbl = QLabel("--")
        self.val_lbl.setObjectName("CardValue")
        layout.addWidget(self.val_lbl)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 2px;
                height: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {self.bar_color};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.progress)

        # Subtitle
        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setObjectName("CardSub")
        layout.addWidget(self.sub_lbl)

    def update_stat(self, percent: float, val_text: str, sub_text: str = None):
        self.progress.setValue(int(min(100, max(0, percent))))
        self.metric_pct_lbl.setText(f"{percent:.1f}%")
        self.val_lbl.setText(val_text)
        if sub_text:
            self.sub_lbl.setText(sub_text)


class ProcessActionWidget(QWidget):
    renice_clicked = pyqtSignal(int)
    freeze_clicked = pyqtSignal(int)
    thaw_clicked = pyqtSignal(int)
    kill_clicked = pyqtSignal(int)

    def __init__(self, pid: int, is_frozen: bool = False, is_protected: bool = False, is_throttled: bool = False):
        super().__init__()
        self.pid = pid

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)

        if is_protected:
            lbl = QLabel("Protected System")
            lbl.setStyleSheet("color: #52525B; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
            layout.addWidget(lbl)
            return

        # Renice Button
        btn_renice = QPushButton("Throttled" if is_throttled else "Throttle")
        btn_renice.setStyleSheet("""
            QPushButton {
                background: rgba(249, 115, 22, 0.1); border: 1px solid rgba(249, 115, 22, 0.25);
                color: #FB923C; font-size: 11px; font-weight: 600; padding: 3px 6px; border-radius: 4px;
            }
            QPushButton:hover { background: rgba(249, 115, 22, 0.25); }
        """)
        btn_renice.clicked.connect(lambda: self.renice_clicked.emit(self.pid))
        layout.addWidget(btn_renice)

        # Freeze / Thaw Button
        if is_frozen:
            btn_freeze = QPushButton("Resume")
            btn_freeze.setStyleSheet("""
                QPushButton {
                    background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25);
                    color: #34D399; font-size: 11px; font-weight: 600; padding: 3px 6px; border-radius: 4px;
                }
                QPushButton:hover { background: rgba(16, 185, 129, 0.25); }
            """)
            btn_freeze.clicked.connect(lambda: self.thaw_clicked.emit(self.pid))
        else:
            btn_freeze = QPushButton("Pause")
            btn_freeze.setStyleSheet("""
                QPushButton {
                    background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.25);
                    color: #60A5FA; font-size: 11px; font-weight: 600; padding: 3px 6px; border-radius: 4px;
                }
                QPushButton:hover { background: rgba(59, 130, 246, 0.25); }
            """)
            btn_freeze.clicked.connect(lambda: self.freeze_clicked.emit(self.pid))
        layout.addWidget(btn_freeze)

        # Terminate Button
        btn_kill = QPushButton("Kill")
        btn_kill.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.25);
                color: #F87171; font-size: 11px; font-weight: 600; padding: 3px 6px; border-radius: 4px;
            }
            QPushButton:hover { background: rgba(239, 68, 68, 0.25); }
        """)
        btn_kill.clicked.connect(lambda: self.kill_clicked.emit(self.pid))
        layout.addWidget(btn_kill)
