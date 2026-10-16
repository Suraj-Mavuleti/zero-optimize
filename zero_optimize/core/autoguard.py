"""
Zero-Optimize Autonomous 1-Second Continuous Watchdog & Optimizer.
Runs every single second to maintain peak performance and absolute smoothness with 0 manual clicks.
"""

import os
import time
import threading
import subprocess
from typing import Callable, Optional, Dict, Any
from zero_optimize.core.system_monitor import SystemMonitor
from zero_optimize.core.optimizer import Optimizer


class AutoGuard:
    def __init__(
        self,
        optimizer: Optimizer = None,
        ram_threshold: float = 82.0,
        interval_seconds: float = 1.0,
        enable_notifications: bool = False
    ):
        self.optimizer = optimizer or Optimizer()
        self.monitor = self.optimizer.monitor
        self.ram_threshold = ram_threshold
        self.interval_seconds = interval_seconds
        self.enable_notifications = enable_notifications

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[dict], None]] = None

        # Continuous performance stats
        self.total_cycles: int = 0
        self.total_throttled_count: int = 0
        self.total_freed_mb: float = 0.0
        self._last_deep_clean: float = 0.0
        self._last_kioworker_clean: float = 0.0

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

    def _notify(self, title: str, message: str):
        if not self.enable_notifications:
            return
        try:
            subprocess.run(
                ["notify-send", "-a", "Zero-Optimize", "-u", "low", title, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def _continuous_loop(self):
        """Runs every 1 second without high CPU consumption."""
        while self._running:
            loop_start = time.time()
            self.total_cycles += 1

            try:
                # 1. Continuous Background Priority Throttler (Runs every second)
                # Catches new browser tabs, Discord renderers, Steam, Java daemons instantly
                tune_res = self.optimizer.optimize_background_priorities()
                newly_reniced = tune_res.get("reniced_count", 0)
                if newly_reniced > 0:
                    self.total_throttled_count += newly_reniced

                # 2. Memory & kswapd0 monitoring
                mem = self.monitor.get_memory_usage()
                ram_info = mem.get("ram", {})
                ram_pct = ram_info.get("percent", 0.0)
                available_mb = ram_info.get("available_mb", 9999)

                # Periodic deep memory maintenance (at least 60s cooldown or high RAM pressure)
                now = time.time()
                if (ram_pct >= self.ram_threshold or available_mb < 1100) and (now - self._last_deep_clean > 45.0):
                    self._last_deep_clean = now
                    # Run background clean without interrupting the user
                    boost_res = self.optimizer.run_smart_boost(allow_root_drop=False)
                    freed = boost_res.get("thumbnails", {}).get("freed_mb", 0.0)
                    self.total_freed_mb += freed

                    if self.enable_notifications:
                        self._notify(
                            "Zero-Optimize Active",
                            f"Maintained memory: {ram_pct}% RAM, freed {freed} MB junk."
                        )

                # 3. Clean orphaned kioworkers every 30 seconds
                if now - self._last_kioworker_clean > 30.0:
                    self._last_kioworker_clean = now
                    w_res = self.optimizer.cleaner.clean_stale_kioworkers()
                    w_freed = w_res.get("freed_mb", 0.0)
                    self.total_freed_mb += w_freed

                # 4. CPU usage sample
                cpu = self.monitor.get_cpu_usage()

                # Emit real-time tick to GUI if registered
                if self._callback:
                    self._callback({
                        "type": "second_tick",
                        "cycles": self.total_cycles,
                        "throttled_total": self.total_throttled_count,
                        "freed_mb": round(self.total_freed_mb, 1),
                        "newly_throttled": newly_reniced,
                        "mem": mem,
                        "cpu": cpu,
                    })

            except Exception:
                pass

            # Sleep remaining time to guarantee 1.0s interval
            elapsed = time.time() - loop_start
            sleep_time = max(0.1, self.interval_seconds - elapsed)
            time.sleep(sleep_time)
