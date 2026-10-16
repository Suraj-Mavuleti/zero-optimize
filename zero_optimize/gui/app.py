"""
Zero-Optimize Main GUI Application.
High-performance desktop application matching zero.skillissue.gg aesthetics.
Features continuous 1-second autonomous background optimization, zero popups,
automatic build worker cleanups, and GitHub release self-updating.
"""

import sys
import os
import time
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QTextEdit, QCheckBox,
    QSystemTrayIcon, QMenu, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QFont, QColor, QAction

from zero_optimize.core.system_monitor import SystemMonitor
from zero_optimize.core.optimizer import Optimizer
from zero_optimize.core.cleaner import Cleaner
from zero_optimize.core.autoguard import AutoGuard
from zero_optimize.core.updater import AutoUpdater
from zero_optimize.gui.styles import ZERO_THEME
from zero_optimize.gui.widgets import StatCard, ProcessActionWidget


class BoostWorker(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, optimizer: Optimizer):
        super().__init__()
        self.optimizer = optimizer

    def run(self):
        res = self.optimizer.run_smart_boost(allow_root_drop=False)
        self.finished_signal.emit(res)


class ZeroOptimizeApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Zero-Optimize")
        self.resize(920, 640)
        self.setStyleSheet(ZERO_THEME)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.icon_path = os.path.join(base_dir, "assets", "zero-optimize.svg")
        if os.path.exists(self.icon_path):
            app_icon = QIcon(self.icon_path)
            self.setWindowIcon(app_icon)
            QApplication.setWindowIcon(app_icon)

        # Core Engines
        self.monitor = SystemMonitor()
        self.cleaner = Cleaner()
        self.optimizer = Optimizer(monitor=self.monitor, cleaner=self.cleaner)
        self.autoguard = AutoGuard(optimizer=self.optimizer, interval_seconds=1.0)
        self.updater = AutoUpdater()

        # Process Caching
        self._cached_processes: List[Dict[str, Any]] = []
        self._last_table_populate: float = 0.0

        self._setup_ui()
        self._setup_system_tray()

        # Connect 1-second autonomous engine
        self.autoguard.set_callback(self._on_engine_tick)
        self.autoguard.start()

        # Initial refresh
        self._refresh_stats()
        self._refresh_processes()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        # 1. Header Card (zero.skillissue.gg aesthetic - clean, no fake git score)
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 12, 16, 12)

        brand_left = QHBoxLayout()
        brand_left.setSpacing(12)

        logo_lbl = QLabel()
        if os.path.exists(self.icon_path):
            logo_lbl.setPixmap(QIcon(self.icon_path).pixmap(36, 36))
        else:
            logo_lbl.setText("⚡")
            logo_lbl.setFont(QFont("Segoe UI Emoji", 20))
        brand_left.addWidget(logo_lbl)

        brand_text_box = QVBoxLayout()
        brand_text_box.setSpacing(2)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(6)
        brand_title = QLabel("devzero")
        brand_title.setStyleSheet("font-weight: 700; font-size: 15px; color: #A1A1AA;")
        brand_sep = QLabel("/")
        brand_sep.setStyleSheet("color: #52525B; font-size: 14px; font-weight: bold;")
        brand_sub = QLabel("zero-optimize")
        brand_sub.setStyleSheet("font-weight: 800; font-size: 16px; color: #FFFFFF;")
        version_badge = QLabel("v2.1.0")
        version_badge.setStyleSheet("color: #71717A; font-family: 'JetBrains Mono', monospace; font-size: 11px; margin-left: 6px;")

        brand_row.addWidget(brand_title)
        brand_row.addWidget(brand_sep)
        brand_row.addWidget(brand_sub)
        brand_row.addWidget(version_badge)
        brand_row.addStretch()
        brand_text_box.addLayout(brand_row)

        uptime_sec = self.monitor.get_uptime_seconds()
        days = int(uptime_sec // 86400)
        hrs = int((uptime_sec % 86400) // 3600)
        self.sub_info_lbl = QLabel(f"Garuda Linux (Wayland) • Uptime: {days}d {hrs}h • Kernel: {os.uname().release}")
        self.sub_info_lbl.setStyleSheet("color: #71717A; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        brand_text_box.addWidget(self.sub_info_lbl)

        brand_left.addLayout(brand_text_box)
        header_layout.addLayout(brand_left)
        header_layout.addStretch()

        # Engine Badge & Auto-Update
        engine_status_box = QHBoxLayout()
        engine_status_box.setSpacing(10)

        self.live_badge = QLabel("● AUTONOMOUS · 1.0s")
        self.live_badge.setObjectName("LiveStatusBadge")
        engine_status_box.addWidget(self.live_badge)

        self.btn_check_updates = QPushButton("Check Updates")
        self.btn_check_updates.setStyleSheet("font-size: 11px; padding: 4px 10px; font-family: 'JetBrains Mono', monospace;")
        self.btn_check_updates.clicked.connect(self._manual_check_update)
        engine_status_box.addWidget(self.btn_check_updates)

        header_layout.addLayout(engine_status_box)
        main_layout.addWidget(header_card)

        # 2. Key Metric Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.ram_card = StatCard("RAM Usage", "Active & Inactive Heap", bar_color="#10B981")
        self.cpu_card = StatCard("CPU Load", "Dynamic Core Balancing", bar_color="#3B82F6")
        self.auto_card = StatCard("Autonomous Engine", "Continuous Throttler & Compactor", bar_color="#F97316")

        cards_layout.addWidget(self.ram_card)
        cards_layout.addWidget(self.cpu_card)
        cards_layout.addWidget(self.auto_card)
        main_layout.addLayout(cards_layout)

        # 3. Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.btn_boost = QPushButton("⚡ INSTANT TURBO RECLAIM")
        self.btn_boost.setObjectName("PrimaryActionButton")
        self.btn_boost.clicked.connect(self._run_turbo_boost)
        action_bar.addWidget(self.btn_boost, 2)

        self.btn_clean_workers = QPushButton("Kill Build Daemons & Workers")
        self.btn_clean_workers.clicked.connect(self._run_clean_workers)
        action_bar.addWidget(self.btn_clean_workers, 1)

        self.btn_clean_thumbs = QPushButton("Purge Thumbnails Cache")
        self.btn_clean_thumbs.clicked.connect(self._run_clean_thumbs)
        action_bar.addWidget(self.btn_clean_thumbs, 1)

        self.btn_throttle_all = QPushButton("Renice All Background Hogs")
        self.btn_throttle_all.clicked.connect(self._run_throttle_hogs)
        action_bar.addWidget(self.btn_throttle_all, 1)

        main_layout.addLayout(action_bar)

        # 4. Tabbed Views
        self.tabs = QTabWidget()

        # Tab 1: Active Process Inspector
        self.tab_proc = QWidget()
        proc_layout = QVBoxLayout(self.tab_proc)
        proc_layout.setContentsMargins(12, 12, 12, 12)
        proc_layout.setSpacing(10)

        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter processes by name, PID, or command...")
        self.search_input.textChanged.connect(self._populate_table_filtered)
        filter_row.addWidget(self.search_input, 2)

        self.cat_filter = QComboBox()
        self.cat_filter.setStyleSheet("""
            QComboBox {
                background-color: #0E0E14; border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px; padding: 7px 12px; color: #FFFFFF; font-size: 12px;
            }
        """)
        self.cat_filter.addItems([
            "All Active Processes",
            "Heavy Apps & Renderers",
            "Background Workers",
            "User Processes Only"
        ])
        self.cat_filter.currentIndexChanged.connect(self._populate_table_filtered)
        filter_row.addWidget(self.cat_filter, 1)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._refresh_processes)
        filter_row.addWidget(btn_refresh)

        proc_layout.addLayout(filter_row)

        self.proc_table = QTableWidget()
        self.proc_table.setColumnCount(7)
        self.proc_table.setHorizontalHeaderLabels([
            "PID", "Name", "Category", "CPU %", "RAM (MB)", "Nice", "Action Controls"
        ])
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proc_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.proc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.proc_table.setSortingEnabled(True)
        proc_layout.addWidget(self.proc_table)

        self.tabs.addTab(self.tab_proc, "Active Processes")

        # Tab 2: Audit Log
        self.tab_log = QWidget()
        log_layout = QVBoxLayout(self.tab_log)
        log_layout.setContentsMargins(12, 12, 12, 12)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.append(f"[{time.strftime('%X')}] Zero-Optimize initialized. Autonomous 1-second watchdog active.")
        log_layout.addWidget(self.log_text)

        btn_clear = QPushButton("Clear Log")
        btn_clear.clicked.connect(lambda: self.log_text.clear())
        log_layout.addWidget(btn_clear, alignment=Qt.AlignmentFlag.AlignRight)

        self.tabs.addTab(self.tab_log, "Audit Log")
        main_layout.addWidget(self.tabs)

        # 5. Footer
        footer = QHBoxLayout()
        self.chk_min_tray = QCheckBox("Minimize to system tray on close")
        self.chk_min_tray.setChecked(True)
        self.chk_min_tray.setStyleSheet("color: #71717A; font-size: 11px;")
        footer.addWidget(self.chk_min_tray)
        footer.addStretch()

        self.update_status_lbl = QLabel("Updates: Suraj-Mavuleti/zero-optimize-updates")
        self.update_status_lbl.setStyleSheet("color: #52525B; font-size: 11px; font-family: 'JetBrains Mono', monospace;")
        footer.addWidget(self.update_status_lbl)

        main_layout.addLayout(footer)

    def _setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(self.icon_path):
            self.tray_icon.setIcon(QIcon(self.icon_path))
        else:
            self.tray_icon.setIcon(self.windowIcon())

        self.tray_icon.setToolTip("Zero-Optimize (Autonomous Linux Performance Guard)")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu { background-color: #0E0E14; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 6px 16px; color: #FFFFFF; font-size: 12px; border-radius: 4px; }
            QMenu::item:selected { background-color: rgba(255, 255, 255, 0.08); }
        """)

        act_show = QAction("Open Dashboard", self)
        act_show.triggered.connect(self.showNormal)
        tray_menu.addAction(act_show)

        act_boost = QAction("Instant Turbo Reclaim", self)
        act_boost.triggered.connect(self._run_turbo_boost)
        tray_menu.addAction(act_boost)

        tray_menu.addSeparator()

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
            # Silent minimize: zero annoying popups or balloon messages
        else:
            self.autoguard.stop()
            event.accept()

    def _log(self, msg: str):
        self.log_text.append(f"[{time.strftime('%X')}] {msg}")

    def _on_engine_tick(self, ev: dict):
        cycles = ev.get("cycles", 0)
        throttled_total = ev.get("throttled_total", 0)
        freed_mb = ev.get("freed_mb", 0.0)

        mem = ev.get("mem", {})
        ram = mem.get("ram", {})
        ram_pct = ram.get("percent", 0.0)
        used_mb = ram.get("used_mb", 0)
        total_mb = ram.get("total_mb", 0)
        avail_mb = ram.get("available_mb", 0)

        self.ram_card.update_stat(
            ram_pct,
            f"{used_mb:,} MB / {total_mb:,} MB",
            f"Available: {avail_mb:,} MB"
        )

        cpu = ev.get("cpu", {})
        cpu_pct = cpu.get("percent", 0.0)
        load_1m = cpu.get("load_1m", 0.0)
        self.cpu_card.update_stat(
            cpu_pct,
            f"{cpu_pct:.1f}% System Load",
            f"1m Load: {load_1m:.2f} · All Cores"
        )

        self.auto_card.update_stat(
            min(100.0, (throttled_total / 20.0) * 100.0) if throttled_total > 0 else 0.0,
            f"{throttled_total} Tasks Throttled",
            f"Cycles: {cycles:,} · Freed: {freed_mb} MB"
        )

        if time.time() - self._last_table_populate > 5.0 and self.tabs.currentIndex() == 0:
            self._refresh_processes()

    def _refresh_stats(self):
        mem = self.monitor.get_memory_usage()
        ram = mem.get("ram", {})
        self.ram_card.update_stat(
            ram.get("percent", 0.0),
            f"{ram.get('used_mb', 0):,} MB / {ram.get('total_mb', 0):,} MB",
            f"Available: {ram.get('available_mb', 0):,} MB"
        )

    def _refresh_processes(self):
        self._cached_processes = self.monitor.get_processes(limit=60)
        self._last_table_populate = time.time()
        self._populate_table_filtered()

    def _populate_table_filtered(self):
        search_query = self.search_input.text().lower().strip()
        cat_filter_idx = self.cat_filter.currentIndex()

        filtered = []
        for p in self._cached_processes:
            if search_query:
                name_match = search_query in p["name"].lower()
                pid_match = search_query in str(p["pid"])
                cmd_match = search_query in p["cmdline"].lower()
                if not (name_match or pid_match or cmd_match):
                    continue

            cat = p["category"]
            if cat_filter_idx == 1 and cat not in ("heavy_app", "browser_tab_renderer"):
                continue
            elif cat_filter_idx == 2 and cat not in ("stale_worker", "kernel_thread"):
                continue
            elif cat_filter_idx == 3 and p["uid"] != os.getuid():
                continue

            filtered.append(p)

        self.proc_table.setSortingEnabled(False)
        self.proc_table.setRowCount(len(filtered))

        for row, p in enumerate(filtered):
            pid = p["pid"]
            is_frozen = pid in self.optimizer.frozen_pids
            is_throttled = p["nice"] >= 10

            pid_item = QTableWidgetItem(str(pid))
            pid_item.setData(Qt.ItemDataRole.UserRole, pid)

            name_item = QTableWidgetItem(p["name"])
            name_item.setToolTip(p["cmdline"][:160])

            cat_item = QTableWidgetItem(p["category"])
            cat_item.setForeground(QColor("#71717A"))

            cpu_item = QTableWidgetItem(f"{p['cpu_pct']:.1f}%")
            if p["cpu_pct"] > 10.0:
                cpu_item.setForeground(QColor("#EF4444"))
            elif p["cpu_pct"] > 3.0:
                cpu_item.setForeground(QColor("#F97316"))

            ram_item = QTableWidgetItem(f"{p['rss_mb']:.1f} MB")
            if p["rss_mb"] > 500:
                ram_item.setForeground(QColor("#EF4444"))
            elif p["rss_mb"] > 150:
                ram_item.setForeground(QColor("#F59E0B"))

            nice_item = QTableWidgetItem(str(p["nice"]))
            if is_throttled:
                nice_item.setForeground(QColor("#10B981"))

            self.proc_table.setItem(row, 0, pid_item)
            self.proc_table.setItem(row, 1, name_item)
            self.proc_table.setItem(row, 2, cat_item)
            self.proc_table.setItem(row, 3, cpu_item)
            self.proc_table.setItem(row, 4, ram_item)
            self.proc_table.setItem(row, 5, nice_item)

            act_widget = ProcessActionWidget(
                pid,
                is_frozen=is_frozen,
                is_protected=p["is_protected"],
                is_throttled=is_throttled
            )
            act_widget.renice_clicked.connect(self._action_renice)
            act_widget.freeze_clicked.connect(self._action_freeze)
            act_widget.thaw_clicked.connect(self._action_thaw)
            act_widget.kill_clicked.connect(self._action_kill)
            self.proc_table.setCellWidget(row, 6, act_widget)

        self.proc_table.setSortingEnabled(True)

    def _action_renice(self, pid: int):
        try:
            os.setpriority(os.PRIO_PROCESS, pid, 15)
            self._log(f"Throttled PID {pid} to nice +15.")
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
        ok, msg = self.optimizer.terminate_process(pid, force=True)
        self._log(msg)
        self._refresh_processes()

    def _run_turbo_boost(self):
        self.btn_boost.setEnabled(False)
        self.btn_boost.setText("⚡ RECLAIMING...")
        self.worker = BoostWorker(self.optimizer)
        self.worker.finished_signal.connect(self._on_boost_done)
        self.worker.start()

    def _on_boost_done(self, res: dict):
        self.btn_boost.setEnabled(True)
        self.btn_boost.setText("⚡ INSTANT TURBO RECLAIM")
        daemons = res.get("daemons", {})
        thumbs = res.get("thumbnails", {})
        cpu = res.get("cpu_tuning", {})
        refs = res.get("cleared_refs", 0)
        self._log(f"Reclaim Complete: Cleared {refs} process memory pages, stopped {len(daemons.get('terminated_pids', []))} build daemons, throttled {cpu.get('reniced_count', 0)} background tasks.")
        self._refresh_stats()
        self._refresh_processes()

    def _run_clean_workers(self):
        w_res = self.cleaner.clean_stale_kioworkers()
        d_res = self.cleaner.clean_idle_build_daemons()
        freed = w_res.get("freed_mb", 0.0) + d_res.get("freed_mb", 0.0)
        self._log(f"Cleaned stale workers & build daemons. Freed ~{round(freed, 1)} MB.")
        self._refresh_stats()
        self._refresh_processes()

    def _run_clean_thumbs(self):
        res = self.cleaner.clean_thumbnail_cache()
        self._log(res.get("status"))
        self._refresh_stats()

    def _run_throttle_hogs(self):
        res = self.optimizer.optimize_background_priorities()
        self._log(res.get("status"))
        self._refresh_processes()

    def _manual_check_update(self):
        self._log("Checking for updates from Suraj-Mavuleti/zero-optimize-updates...")
        has_upd, meta = self.updater.check_for_updates()
        if has_upd:
            ver = meta.get("version")
            self._log(f"New update found: v{ver}. Applying update in background...")
            succ, msg = self.updater.apply_update(meta.get("download_url"))
            self._log(f"Update Result: {msg}")
        else:
            self._log(f"Zero-Optimize is up to date (v{self.updater.current_version}).")


def main():
    app = QApplication(sys.argv)
    window = ZeroOptimizeApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
