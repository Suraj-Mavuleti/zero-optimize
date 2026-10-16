"""
Zero-Optimise Main PyQt6 Desktop Application.
Modern GUI designed for Garuda Linux (KDE Plasma Wayland / X11).
"""

import sys
import os
import time
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QTextEdit, QCheckBox,
    QSystemTrayIcon, QMenu, QMessageBox, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QIcon, QFont, QColor, QAction

from zero_optimise.core.system_monitor import SystemMonitor
from zero_optimise.core.optimizer import Optimizer
from zero_optimise.core.cleaner import Cleaner
from zero_optimise.core.autoguard import AutoGuard
from zero_optimise.gui.styles import GARUDA_THEME
from zero_optimise.gui.widgets import StatCard, ProcessActionWidget


class BoostWorker(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, optimizer: Optimizer, allow_root: bool = True):
        super().__init__()
        self.optimizer = optimizer
        self.allow_root = allow_root

    def run(self):
        res = self.optimizer.run_smart_boost(allow_root_drop=self.allow_root)
        self.finished_signal.emit(res)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zero-Optimise — Garuda Linux RAM & CPU Booster")
        self.resize(1020, 720)
        self.setMinimumSize(850, 600)

        # Icon setup
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, "assets", "zero-optimise.svg")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.setWindowIcon(app_icon)

        # Core engines
        self.monitor = SystemMonitor()
        self.cleaner = Cleaner()
        self.optimizer = Optimizer(monitor=self.monitor, cleaner=self.cleaner)
        self.autoguard = AutoGuard(optimizer=self.optimizer)


        # Track sorting and filtering
        self._cached_processes: List[Dict[str, Any]] = []
        self._last_proc_update: float = 0.0

        self._setup_ui()
        self._setup_system_tray()
        self._setup_timers()

        # Connect autoguard callback
        self.autoguard.set_callback(self._on_autoguard_event)

        # Initial refresh
        self._refresh_stats()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # 1. Header Row
        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        
        title_row = QHBoxLayout()
        icon_lbl = QLabel("⚡")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 20))
        title_lbl = QLabel("ZERO-OPTIMISE")
        title_lbl.setStyleSheet("font-weight: 900; font-size: 20px; color: #00f0ff; letter-spacing: 1px;")
        subtitle_lbl = QLabel("Garuda Linux Performance & Memory Reclaimer")
        subtitle_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; margin-left: 6px;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addWidget(subtitle_lbl)
        title_row.addStretch()

        header_left.addLayout(title_row)

        uptime_sec = self.monitor.get_uptime_seconds()
        days = int(uptime_sec // 86400)
        hrs = int((uptime_sec % 86400) // 3600)
        self.system_info_lbl = QLabel(f"Uptime: {days}d {hrs}h • Kernel: {os.uname().release}")
        self.system_info_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        header_left.addWidget(self.system_info_lbl)
        header_layout.addLayout(header_left)

        # Auto-Guard Switch in Header
        self.btn_guard_toggle = QPushButton("🛡️ Auto-Guard: OFF")
        self.btn_guard_toggle.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: #94a3b8;
                border: 1px solid #334155; border-radius: 8px;
                padding: 8px 14px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { border-color: #00f0ff; color: white; }
        """)
        self.btn_guard_toggle.clicked.connect(self._toggle_autoguard)
        header_layout.addWidget(self.btn_guard_toggle)

        main_layout.addLayout(header_layout)

        # 2. Resource Stats Row (3 Cards)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        self.ram_card = StatCard("RAM USAGE", "🧠")
        self.cpu_card = StatCard("CPU LOAD", "⚡")
        self.swap_card = StatCard("SWAP & ZRAM", "🔄")

        cards_layout.addWidget(self.ram_card)
        cards_layout.addWidget(self.cpu_card)
        cards_layout.addWidget(self.swap_card)
        main_layout.addLayout(cards_layout)

        # 3. Action Toolbar (Boost & Quick Actions)
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.btn_boost = QPushButton("🚀 1-CLICK SMART BOOST")
        self.btn_boost.setObjectName("PrimaryBoostButton")
        self.btn_boost.setToolTip("Flushes caches, throttles background hogs, frees thumbnail junk, and compacts memory")
        self.btn_boost.clicked.connect(self._run_smart_boost)
        action_bar.addWidget(self.btn_boost, 2)

        self.btn_drop_caches = QPushButton("🧹 Drop PageCache")
        self.btn_drop_caches.setProperty("class", "ActionBtn")
        self.btn_drop_caches.setToolTip("Purges cached files from memory via Polkit authorization")
        self.btn_drop_caches.clicked.connect(self._run_drop_caches)
        action_bar.addWidget(self.btn_drop_caches, 1)

        self.btn_clean_thumbs = QPushButton("📂 Clean Thumbnails")
        self.btn_clean_thumbs.setProperty("class", "ActionBtn")
        self.btn_clean_thumbs.setToolTip("Deletes accumulated cache in ~/.cache/thumbnails")
        self.btn_clean_thumbs.clicked.connect(self._run_clean_thumbnails)
        action_bar.addWidget(self.btn_clean_thumbs, 1)

        self.btn_throttle_all = QPushButton("⚡ Throttle Hogs")
        self.btn_throttle_all.setProperty("class", "ActionBtn")
        self.btn_throttle_all.setToolTip("Renices all background browser renderers and Discord tasks to nice 15")
        self.btn_throttle_all.clicked.connect(self._run_throttle_hogs)
        action_bar.addWidget(self.btn_throttle_all, 1)

        main_layout.addLayout(action_bar)

        # 4. Tabbed Content
        self.tabs = QTabWidget()
        
        # Tab 1: Process Inspector & Manager
        self.tab_processes = QWidget()
        proc_layout = QVBoxLayout(self.tab_processes)
        proc_layout.setContentsMargins(12, 12, 12, 12)
        proc_layout.setSpacing(10)

        # Filter bar
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search process name, PID, or command...")
        self.search_input.textChanged.connect(self._filter_process_table)
        filter_layout.addWidget(self.search_input, 2)

        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: #0b0f19; border: 1px solid #334155;
                border-radius: 8px; padding: 6px 12px; color: #f8fafc;
            }
        """)
        self.category_combo.addItems([
            "All Active Processes",
            "Heavy Apps & Renderers Only",
            "KDE Kioworkers / Helpers",
            "User Processes Only"
        ])
        self.category_combo.currentIndexChanged.connect(self._filter_process_table)
        filter_layout.addWidget(self.category_combo, 1)

        self.btn_refresh_procs = QPushButton("🔄 Refresh")
        self.btn_refresh_procs.clicked.connect(self._update_processes_manual)
        filter_layout.addWidget(self.btn_refresh_procs)

        proc_layout.addLayout(filter_layout)

        # Process Table
        self.proc_table = QTableWidget()
        self.proc_table.setColumnCount(7)
        self.proc_table.setHorizontalHeaderLabels([
            "PID", "Process Name", "Category", "CPU %", "RAM (MB)", "Nice", "Actions"
        ])
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proc_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.proc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.proc_table.setSortingEnabled(True)
        proc_layout.addWidget(self.proc_table)

        self.tabs.addTab(self.tab_processes, "📋 Active Processes")

        # Tab 2: Activity Log
        self.tab_log = QWidget()
        log_layout = QVBoxLayout(self.tab_log)
        log_layout.setContentsMargins(12, 12, 12, 12)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.append(f"[{time.strftime('%X')}] Zero-Optimise started. Ready.")
        log_layout.addWidget(self.log_text)

        btn_clear_log = QPushButton("Clear Log")
        btn_clear_log.clicked.connect(lambda: self.log_text.clear())
        log_layout.addWidget(btn_clear_log, alignment=Qt.AlignmentFlag.AlignRight)

        self.tabs.addTab(self.tab_log, "📜 Optimization Log")

        # Tab 3: System & Kernel Tuning
        self.tab_tuning = QWidget()
        tuning_layout = QVBoxLayout(self.tab_tuning)
        tuning_layout.setContentsMargins(16, 16, 16, 16)
        tuning_layout.setSpacing(14)

        info_box = QFrame()
        info_box.setProperty("class", "CardFrame")
        info_vbox = QVBoxLayout(info_box)

        tuning_title = QLabel("⚙️ Kernel VM & Swap Tuning Information")
        tuning_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #00f0ff;")
        info_vbox.addWidget(tuning_title)

        desc = QLabel(
            "On long-running Garuda Linux installations without restarts, background applications "
            "accumulate fragmented memory pages. The Linux kernel's [kswapd0] thread consumes high CPU "
            "attempting to reclaim contiguous memory pages, while background tabs and daemons continuously hog resources.\n\n"
            "Zero-Optimise solves this by:\n"
            "• Running memory compaction to end kswapd0 thrashing.\n"
            "• Deprioritizing idle background browser renderers and Discord to nice +15.\n"
            "• Purging accumulated thumbnail caches and stale kioworkers.\n"
            "• Dropping pagecache, dentries, and inodes safely."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cbd5e1; line-height: 1.5; font-size: 12px;")
        info_vbox.addWidget(desc)
        tuning_layout.addWidget(info_box)

        # Swappiness and config info
        try:
            with open("/proc/sys/vm/swappiness", "r") as f:
                swappiness_val = f.read().strip()
        except Exception:
            swappiness_val = "Unknown"

        try:
            with open("/proc/sys/vm/vfs_cache_pressure", "r") as f:
                vfs_val = f.read().strip()
        except Exception:
            vfs_val = "Unknown"

        status_box = QFrame()
        status_box.setProperty("class", "CardFrame")
        sbox_layout = QVBoxLayout(status_box)
        sbox_layout.addWidget(QLabel(f"<b>vm.swappiness:</b> {swappiness_val} (Garuda default optimized for ZRAM)"))
        sbox_layout.addWidget(QLabel(f"<b>vm.vfs_cache_pressure:</b> {vfs_val}"))
        sbox_layout.addWidget(QLabel("<b>Compaction helper:</b> Available (/proc/sys/vm/compact_memory)"))
        tuning_layout.addWidget(status_box)

        tuning_layout.addStretch()
        self.tabs.addTab(self.tab_tuning, "🔧 Kernel Diagnostics")

        main_layout.addWidget(self.tabs)

        # 5. Status Footer
        footer_layout = QHBoxLayout()
        self.status_bar_lbl = QLabel("System running normally")
        self.status_bar_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        footer_layout.addWidget(self.status_bar_lbl)
        footer_layout.addStretch()

        self.chk_min_tray = QCheckBox("Minimize to system tray on close")
        self.chk_min_tray.setChecked(True)
        self.chk_min_tray.setStyleSheet("color: #94a3b8; font-size: 11px;")
        footer_layout.addWidget(self.chk_min_tray)

        main_layout.addLayout(footer_layout)

    def _setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        
        tray_menu = QMenu()
        act_show = QAction("Open Zero-Optimise", self)
        act_show.triggered.connect(self.showNormal)
        tray_menu.addAction(act_show)

        act_boost = QAction("🚀 Run Smart Boost", self)
        act_boost.triggered.connect(self._run_smart_boost)
        tray_menu.addAction(act_boost)

        tray_menu.addSeparator()

        act_guard = QAction("Toggle Auto-Guard", self)
        act_guard.triggered.connect(self._toggle_autoguard)
        tray_menu.addAction(act_guard)

        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(act_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def closeEvent(self, event):
        if self.chk_min_tray.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Zero-Optimise",
                "App minimized to system tray. Performance guard is still active.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            self.autoguard.stop()
            event.accept()

    def _setup_timers(self):
        # Stats timer (every 2.0s)
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._refresh_stats)
        self.stats_timer.start(2000)

        # Process list timer (every 4.0s)
        self.proc_timer = QTimer(self)
        self.proc_timer.timeout.connect(self._refresh_processes)
        self.proc_timer.start(4000)

    def _log(self, text: str):
        timestamp = time.strftime('%X')
        self.log_text.append(f"[{timestamp}] {text}")

    def _refresh_stats(self):
        mem = self.monitor.get_memory_usage()
        cpu = self.monitor.get_cpu_usage()

        ram = mem.get("ram", {})
        ram_pct = ram.get("percent", 0.0)
        self.ram_card.update_stat(
            ram_pct,
            f"{ram.get('used_mb', 0):,} MB / {ram.get('total_mb', 0):,} MB ({ram.get('cache_mb', 0):,} MB Cache)"
        )

        cpu_pct = cpu.get("percent", 0.0)
        load_str = f"Load: {cpu.get('load_1m', 0):.2f}, {cpu.get('load_5m', 0):.2f}"
        self.cpu_card.update_stat(cpu_pct, load_str)

        swap = mem.get("swap", {})
        swap_pct = swap.get("percent", 0.0)
        zram = mem.get("zram")
        if zram:
            swap_detail = f"{swap.get('used_mb', 0):,} MB used • ZRAM {zram.get('ratio', 1.0)}x"
        else:
            swap_detail = f"{swap.get('used_mb', 0):,} MB / {swap.get('total_mb', 0):,} MB used"
        self.swap_card.update_stat(swap_pct, swap_detail)

        # Update tray tooltip
        self.tray_icon.setToolTip(f"Zero-Optimise: RAM {ram_pct:.0f}% | CPU {cpu_pct:.0f}%")

    def _refresh_processes(self):
        # Update process cache
        self._cached_processes = self.monitor.get_processes()
        self._populate_process_table()

    def _update_processes_manual(self):
        self.btn_refresh_procs.setEnabled(False)
        self._refresh_processes()
        self.btn_refresh_procs.setEnabled(True)

    def _populate_process_table(self):
        filter_text = self.search_input.text().strip().lower()
        cat_filter = self.category_combo.currentIndex()
        my_uid = os.getuid()

        # Filter processes
        filtered = []
        for p in self._cached_processes:
            # Text filter
            if filter_text:
                if filter_text not in p["name"].lower() and filter_text not in str(p["pid"]) and filter_text not in p["cmdline"].lower():
                    continue

            # Category filter
            if cat_filter == 1:  # Heavy apps only
                if p["category"] not in ("heavy_app", "browser_tab_renderer"):
                    continue
            elif cat_filter == 2:  # Kioworkers / Helpers
                if p["category"] != "stale_worker":
                    continue
            elif cat_filter == 3:  # User only
                if p["uid"] != my_uid:
                    continue

            filtered.append(p)

        self.proc_table.setSortingEnabled(False)
        self.proc_table.setRowCount(len(filtered))

        for row, p in enumerate(filtered):
            pid = p["pid"]
            is_frozen = pid in self.optimizer.frozen_pids

            # PID
            pid_item = QTableWidgetItem(str(pid))
            pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Name
            name_item = QTableWidgetItem(p["name"])
            if is_frozen:
                name_item.setForeground(QColor("#fbbf24"))
                name_item.setText(f"⏸ {p['name']} [PAUSED]")

            # Category
            cat_map = {
                "system_protected": "System Core",
                "kernel_thread": "Kernel",
                "stale_worker": "KDE Worker",
                "browser_tab_renderer": "Browser Tab",
                "heavy_app": "Heavy App",
                "normal": "Standard",
            }
            cat_item = QTableWidgetItem(cat_map.get(p["category"], p["category"]))
            cat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # CPU
            cpu_item = QTableWidgetItem()
            cpu_item.setData(Qt.ItemDataRole.DisplayRole, p["cpu_pct"])
            cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if p["cpu_pct"] > 30.0:
                cpu_item.setForeground(QColor("#ef4444"))

            # RAM
            ram_item = QTableWidgetItem()
            ram_item.setData(Qt.ItemDataRole.DisplayRole, p["rss_mb"])
            ram_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if p["rss_mb"] > 500.0:
                ram_item.setForeground(QColor("#38bdf8"))

            # Nice
            nice_item = QTableWidgetItem(str(p["nice"]))
            nice_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.proc_table.setItem(row, 0, pid_item)
            self.proc_table.setItem(row, 1, name_item)
            self.proc_table.setItem(row, 2, cat_item)
            self.proc_table.setItem(row, 3, cpu_item)
            self.proc_table.setItem(row, 4, ram_item)
            self.proc_table.setItem(row, 5, nice_item)

            # Action widget
            act_widget = ProcessActionWidget(pid, is_frozen=is_frozen, is_protected=p["is_protected"])
            act_widget.renice_clicked.connect(self._action_renice)
            act_widget.freeze_clicked.connect(self._action_freeze)
            act_widget.thaw_clicked.connect(self._action_thaw)
            act_widget.kill_clicked.connect(self._action_kill)
            self.proc_table.setCellWidget(row, 6, act_widget)

        self.proc_table.setSortingEnabled(True)

    def _filter_process_table(self):
        self._populate_process_table()

    # --- Actions ---

    def _action_renice(self, pid: int):
        try:
            os.setpriority(os.PRIO_PROCESS, pid, 15)
            self._log(f"Deprioritized PID {pid} to nice +15.")
            self._refresh_processes()
        except Exception as e:
            self._log(f"Failed to renice PID {pid}: {e}")

    def _action_freeze(self, pid: int):
        ok, msg = self.optimizer.freeze_process(pid)
        self._log(msg)
        self._refresh_processes()

    def _action_thaw(self, pid: int):
        ok, msg = self.optimizer.thaw_process(pid)
        self._log(msg)
        self._refresh_processes()

    def _action_kill(self, pid: int):
        ok, msg = self.optimizer.terminate_process(pid, force=False)
        self._log(msg)
        self._refresh_processes()

    def _run_smart_boost(self):
        self.btn_boost.setEnabled(False)
        self.btn_boost.setText("⚡ BOOSTING...")
        self.status_bar_lbl.setText("Running full system optimization...")

        self.worker = BoostWorker(self.optimizer, allow_root=True)
        self.worker.finished_signal.connect(self._on_boost_complete)
        self.worker.start()

    def _on_boost_complete(self, res: dict):
        self.btn_boost.setEnabled(True)
        self.btn_boost.setText("🚀 1-CLICK SMART BOOST")
        self.status_bar_lbl.setText("Optimization finished successfully")

        thumbs = res.get("thumbnails", {})
        workers = res.get("workers", {})
        cpu = res.get("cpu_tuning", {})
        cache = res.get("cache_drop", {})

        self._log("=== SMART BOOST COMPLETED ===")
        self._log(f"• Thumbnails: {thumbs.get('status')}")
        self._log(f"• Stale Workers: {workers.get('status')}")
        self._log(f"• CPU Tuning: {cpu.get('status')}")
        self._log(f"• PageCache Drop: {cache.get('message')}")
        self._log("==============================")

        self._refresh_stats()
        self._refresh_processes()

        self.tray_icon.showMessage(
            "Zero-Optimise Boosted",
            f"Optimized {cpu.get('reniced_count', 0)} tasks and reclaimed {thumbs.get('freed_mb', 0)} MB.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def _run_drop_caches(self):
        self.btn_drop_caches.setEnabled(False)
        succ, msg = self.cleaner.drop_caches_privileged(use_gui_auth=True)
        if succ:
            self.cleaner.compact_memory_privileged(use_gui_auth=False)
        self._log(f"PageCache Drop: {msg}")
        self._refresh_stats()
        self.btn_drop_caches.setEnabled(True)

    def _run_clean_thumbnails(self):
        res = self.cleaner.clean_thumbnail_cache()
        self._log(res.get("status"))
        self._refresh_stats()

    def _run_throttle_hogs(self):
        res = self.optimizer.optimize_background_priorities()
        self._log(res.get("status"))
        self._refresh_processes()

    def _toggle_autoguard(self):
        if self.autoguard.is_running():
            self.autoguard.stop()
            self.btn_guard_toggle.setText("🛡️ Auto-Guard: OFF")
            self.btn_guard_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b; color: #94a3b8;
                    border: 1px solid #334155; border-radius: 8px;
                    padding: 8px 14px; font-weight: bold; font-size: 12px;
                }
            """)
            self._log("Auto-Guard deactivated.")
        else:
            self.autoguard.start()
            self.btn_guard_toggle.setText("🛡️ Auto-Guard: ACTIVE")
            self.btn_guard_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #064e3b; color: #34d399;
                    border: 1px solid #059669; border-radius: 8px;
                    padding: 8px 14px; font-weight: bold; font-size: 12px;
                }
            """)
            self._log("Auto-Guard activated. Background monitoring initialized.")

    def _on_autoguard_event(self, ev: dict):
        ev_type = ev.get("type")
        if ev_type == "ram_autoboost":
            self._log(f"Auto-Guard: RAM exceeded threshold ({ev.get('ram_pct')}%). Auto-boost triggered.")
            self._refresh_stats()
            self._refresh_processes()
        elif ev_type == "cpu_autotune":
            self._log(f"Auto-Guard: High CPU detected. Reniced {ev.get('count')} background tasks.")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Zero-Optimise")
    app.setStyleSheet(GARUDA_THEME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
