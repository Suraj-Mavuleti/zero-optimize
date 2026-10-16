"""
Zero-Optimize Autonomous Continuous Guard.
Non-destructive 1-second watchdog:
- Balances process CPU priority every second
- Cleans safe thumbnail caches and resets memory reference bits
- Never terminates user processes automatically
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
        ram_threshold: float = 85.0,
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

        self.total_cycles: int = 0
        self.total_throttled_count: int = 0
        self.total_freed_mb: float = 0.0
        self._last_deep_clean: float = 0.0
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
        while self._running:
            loop_start = time.time()
            self.total_cycles += 1
            now = time.time()

            try:
                # 1. Non-destructive priority balancing (every 1 second)
                tune_res = self.optimizer.optimize_background_priorities()
                newly_reniced = tune_res.get("reniced_count", 0)
                if newly_reniced > 0:
                    self.total_throttled_count += newly_reniced

                # 2. Check memory pressure
                mem = self.monitor.get_memory_usage()
                ram_info = mem.get("ram", {})
                ram_pct = ram_info.get("percent", 0.0)

                # Periodic non-destructive maintenance (every 45s)
                if now - self._last_deep_clean > 45.0:
                    self._last_deep_clean = now
                    boost_res = self.optimizer.run_smart_boost()
                    freed = boost_res.get("caches", {}).get("freed_mb", 0.0)
                    self.total_freed_mb += freed

                # 3. Check for updates periodically (every 30 mins)
                if now - self._last_update_check > 1800.0:
                    self._last_update_check = now
                    has_upd, meta = self.updater.check_for_updates()
                    if has_upd and meta.get("download_url"):
                        self.updater.apply_update(meta["download_url"])

                cpu = self.monitor.get_cpu_usage()

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

            elapsed = time.time() - loop_start
            sleep_time = max(0.05, self.interval_seconds - elapsed)
            time.sleep(sleep_time)
