"""
Zero-Optimize Desktop Application.
Modern minimalist desktop architecture modeled on ZeroMusic's desktop shell:
- 240px native left sidebar (Dashboard, Processes, Cleaners, Daemon status)
- Clean metric telemetry tiles with real-time gauges
- Process management with individual kill, throttle, and freeze actions
- Thread-safe QTimer & QThread autonomous engine (prevents cross-thread crashes)
"""

import sys
import os
import time

# Ensure project root is always in sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QTextEdit,
    QSystemTrayIcon, QMenu, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QIcon, QFont, QColor, QAction

from zero_optimize.core.system_monitor import SystemMonitor
from zero_optimize.core.optimizer import Optimizer
from zero_optimize.core.cleaner import Cleaner
from zero_optimize.core.updater import AutoUpdater
from zero_optimize.gui.styles import ZERO_THEME
from zero_optimize.gui.widgets import StatCard, ProcessActionWidget


class EngineWorker(QObject):
    tick_signal = pyqtSignal(dict)

    def __init__(self, optimizer: Optimizer, monitor: SystemMonitor):
        super().__init__()
        self.optimizer = optimizer
        self.monitor = monitor
        self.total_cycles = 0
        self.total_throttled = 0
        self.total_freed_mb = 0.0
        self._last_clean = 0.0

    def run_tick(self):
        self.total_cycles += 1
        now = time.time()
        try:
            # Non-destructive priority balancing every second
            tune_res = self.optimizer.optimize_background_priorities()
            newly_reniced = tune_res.get("reniced_count", 0)
            self.total_throttled += newly_reniced

            # Periodic background app sleep (every 15s)
            if self.total_cycles % 15 == 0:
                self.optimizer.snooze_background_apps()

            # Periodic non-destructive maintenance (every 45s)
            if now - self._last_clean > 45.0:
                self._last_clean = now
                boost_res = self.optimizer.run_smart_boost(allow_root_drop=False)
                freed = boost_res.get("ram_freed_mb", 0.0) or boost_res.get("caches", {}).get("freed_mb", 0.0)
                self.total_freed_mb += freed

            mem = self.monitor.get_memory_usage()
            cpu = self.monitor.get_cpu_usage()

            self.tick_signal.emit({
                "cycles": self.total_cycles,
                "throttled_total": self.total_throttled,
                "freed_mb": round(self.total_freed_mb, 1),
                "mem": mem,
                "cpu": cpu
            })
        except Exception:
            pass


class BoostWorker(QThread):
    finished_signal = pyqtSignal(dict)

    def __init__(self, optimizer: Optimizer):
        super().__init__()
        self.optimizer = optimizer

    def run(self):
        res = self.optimizer.run_smart_boost(allow_root_drop=True)
        self.finished_signal.emit(res)


class ZeroOptimizeApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Zero-Optimize")
        self.resize(1020, 680)
        self.setMinimumSize(880, 560)
        self.setStyleSheet(ZERO_THEME)

        self.icon_path = os.path.join(_PROJECT_ROOT, "assets", "zero-optimize.svg")
        if os.path.exists(self.icon_path):
            app_icon = QIcon(self.icon_path)
            self.setWindowIcon(app_icon)
            QApplication.setWindowIcon(app_icon)

        # Core Engines
        self.monitor = SystemMonitor()
        self.cleaner = Cleaner()
        self.optimizer = Optimizer(monitor=self.monitor, cleaner=self.cleaner)
        self.updater = AutoUpdater()

        self._cached_processes: List[Dict[str, Any]] = []
        self._last_table_populate: float = 0.0

        self._setup_ui()
        self._setup_system_tray()

        # Thread-safe Engine Loop using QTimer (Prevents cross-thread GUI segmentation faults)
        self.engine_worker = EngineWorker(self.optimizer, self.monitor)
        self.engine_worker.tick_signal.connect(self._on_engine_tick)

        self.engine_timer = QTimer(self)
        self.engine_timer.setInterval(1000)  # Exactly 1.0 second loop
        self.engine_timer.timeout.connect(self.engine_worker.run_tick)
        self.engine_timer.start()

        # Initial refresh
        self._refresh_stats()
        self._refresh_processes()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 1. LEFT SIDEBAR (ZeroMusic Desktop Shell) ──
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(6)

        # Brand Lockup
        brand_box = QHBoxLayout()
        brand_box.setSpacing(10)
        logo_lbl = QLabel()
        if os.path.exists(self.icon_path):
            logo_lbl.setPixmap(QIcon(self.icon_path).pixmap(30, 30))
        brand_box.addWidget(logo_lbl)

        brand_text_col = QVBoxLayout()
        brand_text_col.setSpacing(0)
        b_name = QLabel("Zero-Optimize")
        b_name.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        b_sub = QLabel("by devzero")
        b_sub.setStyleSheet("font-size: 11px; color: #52525B; font-family: 'JetBrains Mono', monospace;")
        brand_text_col.addWidget(b_name)
        brand_text_col.addWidget(b_sub)
        brand_box.addLayout(brand_text_col)
        brand_box.addStretch()
        sidebar_layout.addLayout(brand_box)
        sidebar_layout.addSpacing(16)

        # Navigation: Section 1
        t1 = QLabel("DASHBOARD")
        t1.setProperty("class", "SidebarBlockTitle")
        sidebar_layout.addWidget(t1)

        self.btn_nav_overview = QPushButton("Overview")
        self.btn_nav_overview.setProperty("class", "SidebarNavBtn")
        self.btn_nav_overview.setProperty("active", "true")
        self.btn_nav_overview.clicked.connect(lambda: self._switch_view(0))
        sidebar_layout.addWidget(self.btn_nav_overview)

        self.btn_nav_procs = QPushButton("Process Inspector")
        self.btn_nav_procs.setProperty("class", "SidebarNavBtn")
        self.btn_nav_procs.clicked.connect(lambda: self._switch_view(1))
        sidebar_layout.addWidget(self.btn_nav_procs)

        self.btn_nav_log = QPushButton("Real-Time Audit")
        self.btn_nav_log.setProperty("class", "SidebarNavBtn")
        self.btn_nav_log.clicked.connect(lambda: self._switch_view(2))
        sidebar_layout.addWidget(self.btn_nav_log)

        sidebar_layout.addSpacing(12)

        # Navigation: Section 2
        t2 = QLabel("AUTONOMOUS ENGINE")
        t2.setProperty("class", "SidebarBlockTitle")
        sidebar_layout.addWidget(t2)

        self.engine_status_pill = QLabel("● Active (1.0s loop)")
        self.engine_status_pill.setStyleSheet("""
            color: #FB923C; font-size: 11px; font-family: 'JetBrains Mono', monospace;
            padding: 6px 10px; background: rgba(249, 115, 22, 0.08); border-radius: 6px;
        """)
        sidebar_layout.addWidget(self.engine_status_pill)

        sidebar_layout.addStretch()

        # Bottom System Info
        uptime_sec = self.monitor.get_uptime_seconds()
        days = int(uptime_sec // 86400)
        hrs = int((uptime_sec % 86400) // 3600)
        sys_lbl = QLabel(f"Garuda Wayland\nUptime: {days}d {hrs}h")
        sys_lbl.setStyleSheet("color: #52525B; font-size: 11px; font-family: 'JetBrains Mono', monospace; line-height: 1.4;")
        sidebar_layout.addWidget(sys_lbl)

        root_layout.addWidget(sidebar)

        # ── 2. MAIN STAGE (Content Pages) ──
        stage = QWidget()
        stage.setObjectName("MainStage")
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(28, 24, 28, 24)
        stage_layout.setSpacing(20)

        # Header Bar
        stage_header = QHBoxLayout()
        self.page_title_lbl = QLabel("Overview")
        self.page_title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; letter-spacing: -0.5px;")
        stage_header.addWidget(self.page_title_lbl)
        stage_header.addStretch()

        self.btn_snooze_apps = QPushButton("🌙 Sleep Background Apps")
        self.btn_snooze_apps.setProperty("class", "SecondaryAction")
        self.btn_snooze_apps.clicked.connect(self._run_snooze_background)
        stage_header.addWidget(self.btn_snooze_apps)

        self.btn_quick_boost = QPushButton("⚡ Instant Reclaim")
        self.btn_quick_boost.setObjectName("PrimaryAction")
        self.btn_quick_boost.clicked.connect(self._run_turbo_boost)
        stage_header.addWidget(self.btn_quick_boost)

        stage_layout.addLayout(stage_header)

        # Stacked Pages
        self.stack = QStackedWidget()

        # PAGE 0: Overview
        page_overview = QWidget()
        ov_layout = QVBoxLayout(page_overview)
        ov_layout.setContentsMargins(0, 0, 0, 0)
        ov_layout.setSpacing(16)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        self.ram_card = StatCard("RAM Usage", "Active & Anonymous Heap", bar_color="#10B981")
        self.cpu_card = StatCard("CPU Load", "Dynamic Scheduling", bar_color="#3B82F6")
        self.auto_card = StatCard("Autonomous Engine", "Every 1.0s Continuous", bar_color="#F97316")
        cards_row.addWidget(self.ram_card)
        cards_row.addWidget(self.cpu_card)
        cards_row.addWidget(self.auto_card)
        ov_layout.addLayout(cards_row)

        ov_lbl = QLabel("Top Memory Consumers (Active Application Heaps)")
        ov_lbl.setStyleSheet("color: #71717A; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 10px;")
        ov_layout.addWidget(ov_lbl)

        self.mini_proc_table = QTableWidget()
        self.mini_proc_table.setColumnCount(5)
        self.mini_proc_table.setHorizontalHeaderLabels(["PID", "Process Name", "Memory (MB)", "CPU %", "Actions"])
        self.mini_proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.mini_proc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.mini_proc_table.setColumnWidth(4, 210)
        self.mini_proc_table.verticalHeader().setVisible(False)
        self.mini_proc_table.verticalHeader().setDefaultSectionSize(40)
        self.mini_proc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.mini_proc_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mini_proc_table.setShowGrid(False)
        self.mini_proc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        ov_layout.addWidget(self.mini_proc_table)

        self.stack.addWidget(page_overview)

        # PAGE 1: Full Process Inspector
        page_procs = QWidget()
        p_layout = QVBoxLayout(page_procs)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(12)

        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchBar")
        self.search_input.setPlaceholderText("Filter processes by name, PID, or command line...")
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

        btn_ref = QPushButton("Refresh Table")
        btn_ref.setProperty("class", "SecondaryAction")
        btn_ref.clicked.connect(self._refresh_processes)
        filter_row.addWidget(btn_ref)
        p_layout.addLayout(filter_row)

        self.proc_table = QTableWidget()
        self.proc_table.setColumnCount(7)
        self.proc_table.setHorizontalHeaderLabels([
            "PID", "Name", "Category", "CPU %", "RAM (MB)", "Nice", "Action Controls"
        ])
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proc_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.proc_table.setColumnWidth(6, 210)
        self.proc_table.verticalHeader().setVisible(False)
        self.proc_table.verticalHeader().setDefaultSectionSize(40)
        self.proc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.proc_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.proc_table.setShowGrid(False)
        self.proc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        p_layout.addWidget(self.proc_table)

        self.stack.addWidget(page_procs)

        # PAGE 2: Real-Time Audit Log
        page_log = QWidget()
        l_layout = QVBoxLayout(page_log)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(10)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.append(f"[{time.strftime('%X')}] Zero-Optimize initialized. Autonomous engine active (1.0s interval).")
        l_layout.addWidget(self.log_text)

        b_clear = QPushButton("Clear Audit Log")
        b_clear.setProperty("class", "SecondaryAction")
        b_clear.clicked.connect(lambda: self.log_text.clear())
        l_layout.addWidget(b_clear, alignment=Qt.AlignmentFlag.AlignRight)

        self.stack.addWidget(page_log)

        stage_layout.addWidget(self.stack)
        root_layout.addWidget(stage, 1)

    def _switch_view(self, index: int):
        self.stack.setCurrentIndex(index)
        titles = ["Overview", "Process Inspector", "Real-Time Audit"]
        self.page_title_lbl.setText(titles[index])

        buttons = [self.btn_nav_overview, self.btn_nav_procs, self.btn_nav_log]
        for idx, btn in enumerate(buttons):
            btn.setProperty("active", "true" if idx == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(self.icon_path):
            self.tray_icon.setIcon(QIcon(self.icon_path))
        else:
            self.tray_icon.setIcon(self.windowIcon())

        self.tray_icon.setToolTip("Zero-Optimize (Autonomous Performance Engine)")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu { background-color: #0E0E14; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 6px 16px; color: #FFFFFF; font-size: 12px; border-radius: 4px; }
            QMenu::item:selected { background-color: rgba(255, 255, 255, 0.08); }
        """)

        act_show = QAction("Open Dashboard", self)
        act_show.triggered.connect(self.showNormal)
        tray_menu.addAction(act_show)

        act_boost = QAction("Instant Reclaim", self)
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
        event.ignore()
        self.hide()

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

        if time.time() - self._last_table_populate > 2.5 and self.stack.currentIndex() in (0, 1):
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
        self._populate_mini_table()

    def _populate_mini_table(self):
        if not self._cached_processes:
            self._cached_processes = self.monitor.get_processes(limit=60)
        top_procs = sorted(self._cached_processes, key=lambda x: x["rss_mb"], reverse=True)[:12]
        self.mini_proc_table.setRowCount(len(top_procs))
        for row, p in enumerate(top_procs):
            pid = p["pid"]
            pid_item = QTableWidgetItem(str(pid))
            pid_item.setForeground(QColor("#71717A"))

            name_item = QTableWidgetItem(p["name"])
            name_item.setForeground(QColor("#FFFFFF"))

            mem_val = f"{p['rss_mb']:.1f} MB"
            ram_item = QTableWidgetItem(mem_val)
            if p["rss_mb"] > 400:
                ram_item.setForeground(QColor("#F59E0B"))
            else:
                ram_item.setForeground(QColor("#E4E4E7"))

            cpu_item = QTableWidgetItem(f"{p['cpu_pct']:.1f}%")
            if p["cpu_pct"] > 10.0:
                cpu_item.setForeground(QColor("#EF4444"))
            else:
                cpu_item.setForeground(QColor("#A1A1AA"))

            self.mini_proc_table.setItem(row, 0, pid_item)
            self.mini_proc_table.setItem(row, 1, name_item)
            self.mini_proc_table.setItem(row, 2, ram_item)
            self.mini_proc_table.setItem(row, 3, cpu_item)

            is_frozen = pid in self.optimizer.frozen_pids
            is_throttled = p["nice"] >= 10
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
            self.mini_proc_table.setCellWidget(row, 4, act_widget)

        self.mini_proc_table.viewport().update()

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

        self.proc_table.setRowCount(len(filtered))
        for row, p in enumerate(filtered):
            pid = p["pid"]
            is_frozen = pid in self.optimizer.frozen_pids
            is_throttled = p["nice"] >= 10

            self.proc_table.setItem(row, 0, QTableWidgetItem(str(pid)))
            name_item = QTableWidgetItem(p["name"])
            name_item.setToolTip(p["cmdline"][:160])
            self.proc_table.setItem(row, 1, name_item)

            cat_item = QTableWidgetItem(p["category"])
            cat_item.setForeground(QColor("#71717A"))
            self.proc_table.setItem(row, 2, cat_item)

            cpu_item = QTableWidgetItem(f"{p['cpu_pct']:.1f}%")
            if p["cpu_pct"] > 10.0:
                cpu_item.setForeground(QColor("#EF4444"))
            self.proc_table.setItem(row, 3, cpu_item)

            ram_item = QTableWidgetItem(f"{p['rss_mb']:.1f} MB")
            if p["rss_mb"] > 400:
                ram_item.setForeground(QColor("#F59E0B"))
            self.proc_table.setItem(row, 4, ram_item)

            nice_item = QTableWidgetItem(str(p["nice"]))
            if is_throttled:
                nice_item.setForeground(QColor("#10B981"))
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

    def _run_snooze_background(self):
        res = self.optimizer.snooze_background_apps()
        count = res.get("snoozed_count", 0)
        self._log(f"Background Apps Hibernated: Put {count} background tasks to low-power sleep (paged cold memory to zram). Antigravity and core desktop stay full speed.")
        self._refresh_stats()
        self._refresh_processes()

    def _run_turbo_boost(self):
        self.btn_quick_boost.setEnabled(False)
        self.btn_quick_boost.setText("Reclaiming...")
        self.worker = BoostWorker(self.optimizer)
        self.worker.finished_signal.connect(self._on_boost_done)
        self.worker.start()

    def _on_boost_done(self, res: dict):
        self.btn_quick_boost.setEnabled(True)
        self.btn_quick_boost.setText("⚡ Instant Reclaim")
        caches = res.get("caches", {})
        cpu = res.get("cpu_tuning", {})
        refs = res.get("cleared_refs", 0)
        ram_freed = res.get("ram_freed_mb", 0.0)
        freed = ram_freed if ram_freed > 0 else caches.get("freed_mb", 0.0)
        self.engine_worker.total_freed_mb += freed
        comp_msg = res.get("compaction", {}).get("message", "Standard")
        self._log(f"Reclaim Complete: Freed ~{freed:.1f} MB RAM ({comp_msg}), cleared {refs} process memory page refs, balanced {cpu.get('reniced_count', 0)} background tasks.")
        self._refresh_stats()
        self._refresh_processes()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = ZeroOptimizeApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
