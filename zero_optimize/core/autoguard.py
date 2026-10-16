"""
Zero-Optimize Autonomous Continuous Guard.
Runs every single second to maintain peak performance with zero popups and zero manual intervention.
"""

import os
import time
import threading
from typing import Callable, Optional, Dict, Any
from zero_optimize.core.system_monitor import SystemMonitor
from zero_optimize.core.optimizer import Optimizer
from zero_optimize.core.updater import AutoUpdater


class AutoGuard:
    def __init__(
        self,
        optimizer: Optimizer = None,
        ram_threshold: float = 80.0,
        interval_seconds: float = 1.0
    ):
        self.optimizer = optimizer or Optimizer()
        self.monitor = self.optimizer.monitor
        self.updater = AutoUpdater()
        self.ram_threshold = ram_threshold
        self.interval_seconds = interval_seconds

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[dict], None]] = None

        # Continuous performance stats
        self.total_cycles: int = 0
        self.total_throttled_count: int = 0
        self.total_freed_mb: float = 0.0
        self._last_deep_clean: float = 0.0
        self._last_worker_clean: float = 0.0
        self._last_update_check: float = 0.0

    def set_callback(self, cb: Callable[[dict], None]):
        self._callback = cb

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._continuous_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.5)
            self._thread = None

    def is_running(self) -> bool:
        return self._running

    def _continuous_loop(self):
        """Runs every 1 second without high CPU consumption."""
        while self._running:
            loop_start = time.time()
            self.total_cycles += 1
            now = time.time()

            try:
                # 1. Continuous Background Priority Throttler (Runs every second)
                tune_res = self.optimizer.optimize_background_priorities()
                newly_reniced = tune_res.get("reniced_count", 0)
                if newly_reniced > 0:
                    self.total_throttled_count += newly_reniced

                # 2. Check memory pressure
                mem = self.monitor.get_memory_usage()
                ram_info = mem.get("ram", {})
                ram_pct = ram_info.get("percent", 0.0)
                available_mb = ram_info.get("available_mb", 9999)

                # Periodic deep memory maintenance (every 30s or when RAM >= 80%)
                if (ram_pct >= self.ram_threshold or available_mb < 1200) and (now - self._last_deep_clean > 30.0):
                    self._last_deep_clean = now
                    boost_res = self.optimizer.run_smart_boost(allow_root_drop=False)
                    freed = boost_res.get("thumbnails", {}).get("freed_mb", 0.0)
                    freed += boost_res.get("daemons", {}).get("freed_mb", 0.0)
                    self.total_freed_mb += freed

                # 3. Clean orphaned kioworkers & stale background indexers every 20 seconds
                if now - self._last_worker_clean > 20.0:
                    self._last_worker_clean = now
                    w_res = self.optimizer.cleaner.clean_stale_kioworkers()
                    d_res = self.optimizer.cleaner.clean_idle_build_daemons()
                    self.total_freed_mb += w_res.get("freed_mb", 0.0) + d_res.get("freed_mb", 0.0)

                # 4. Background auto-update check every 30 minutes
                if now - self._last_update_check > 1800.0:
                    self._last_update_check = now
                    has_upd, meta = self.updater.check_for_updates()
                    if has_upd and meta.get("download_url"):
                        self.updater.apply_update(meta["download_url"])

                # 5. CPU usage sample
                cpu = self.monitor.get_cpu_usage()

                # Emit real-time tick to GUI
                if self._callback:
                    self._callback({
                        "type": "second_tick",
                        "cycles": self.total_cycles,
                        "throttled_total": self.total_throttled_count,
                        "newly_throttled": newly_reniced,
                        "freed_mb": round(self.total_freed_mb, 1),
                        "mem": mem,
                        "cpu": cpu,
                    })

            except Exception:
                pass

            # Sleep remainder of 1 second
            elapsed = time.time() - loop_start
            sleep_time = max(0.05, self.interval_seconds - elapsed)
            time.sleep(sleep_time)
