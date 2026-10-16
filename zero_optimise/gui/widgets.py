"""
Custom UI widgets for Zero-Optimise application.
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class StatCard(QFrame):
    def __init__(self, title: str, icon_str: str = "📊", parent=None):
        super().__init__(parent)
        self.setProperty("class", "CardFrame")
        self.setObjectName("CardFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Header: Icon + Title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        self.icon_label = QLabel(icon_str)
        self.icon_label.setFont(QFont("Segoe UI Emoji", 15))
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 13px;")
        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Big percentage label
        self.value_label = QLabel("0.0 %")
        self.value_label.setStyleSheet("color: #00f0ff; font-weight: 800; font-size: 26px;")
        layout.addWidget(self.value_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

        # Subtitle details (e.g. "6200 MB / 7655 MB")
        self.detail_label = QLabel("Initializing...")
        self.detail_label.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.detail_label)

    def update_stat(self, percent: float, detail: str, color_override: str = None):
        self.value_label.setText(f"{percent:.1f} %")
        self.progress_bar.setValue(int(min(100, max(0, percent))))
        self.detail_label.setText(detail)

        # Dynamic color coding
        if color_override:
            col = color_override
        elif percent >= 88.0:
            col = "#ef4444"  # Danger red
        elif percent >= 75.0:
            col = "#f59e0b"  # Warning amber
        else:
            col = "#00f0ff"  # Normal cyan

        self.value_label.setStyleSheet(f"color: {col}; font-weight: 800; font-size: 26px;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {col};
                border-radius: 4px;
            }}
        """)


class ProcessActionWidget(QWidget):
    freeze_clicked = pyqtSignal(int)
    thaw_clicked = pyqtSignal(int)
    renice_clicked = pyqtSignal(int)
    kill_clicked = pyqtSignal(int)

    def __init__(self, pid: int, is_frozen: bool, is_protected: bool, parent=None):
        super().__init__(parent)
        self.pid = pid
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        if not is_protected:
            # Renice Button
            self.btn_renice = QPushButton("Deprioritize")
            self.btn_renice.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b; color: #38bdf8;
                    border: 1px solid #0369a1; border-radius: 4px;
                    padding: 3px 6px; font-size: 11px; font-weight: bold;
                }
                QPushButton:hover { background-color: #0369a1; color: white; }
            """)
            self.btn_renice.setToolTip("Renice to +15 and lower I/O priority")
            self.btn_renice.clicked.connect(lambda: self.renice_clicked.emit(self.pid))
            layout.addWidget(self.btn_renice)

            # Freeze / Thaw Button
            if is_frozen:
                self.btn_freeze = QPushButton("Resume")
                self.btn_freeze.setStyleSheet("""
                    QPushButton {
                        background-color: #064e3b; color: #34d399;
                        border: 1px solid #059669; border-radius: 4px;
                        padding: 3px 6px; font-size: 11px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #059669; color: white; }
                """)
                self.btn_freeze.clicked.connect(lambda: self.thaw_clicked.emit(self.pid))
            else:
                self.btn_freeze = QPushButton("Freeze")
                self.btn_freeze.setStyleSheet("""
                    QPushButton {
                        background-color: #451a03; color: #fbbf24;
                        border: 1px solid #d97706; border-radius: 4px;
                        padding: 3px 6px; font-size: 11px; font-weight: bold;
                    }
                    QPushButton:hover { background-color: #d97706; color: white; }
                """)
                self.btn_freeze.setToolTip("Pause process execution (0% CPU) with SIGSTOP")
                self.btn_freeze.clicked.connect(lambda: self.freeze_clicked.emit(self.pid))
            layout.addWidget(self.btn_freeze)

            # Terminate Button
            self.btn_kill = QPushButton("End")
            self.btn_kill.setStyleSheet("""
                QPushButton {
                    background-color: #450a0a; color: #f87171;
                    border: 1px solid #dc2626; border-radius: 4px;
                    padding: 3px 6px; font-size: 11px; font-weight: bold;
                }
                QPushButton:hover { background-color: #dc2626; color: white; }
            """)
            self.btn_kill.clicked.connect(lambda: self.kill_clicked.emit(self.pid))
            layout.addWidget(self.btn_kill)
        else:
            lbl = QLabel("Protected System")
            lbl.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
            layout.addWidget(lbl)

        layout.addStretch()
