"""
Zero-Optimise AutoGuard Daemon & Watchdog.
Monitors memory and CPU in the background, automatically maintaining low resource usage.
"""

import time
import threading
import subprocess
from typing import Callable, Optional
from zero_optimise.core.system_monitor import SystemMonitor
from zero_optimise.core.optimizer import Optimizer


class AutoGuard:
    def __init__(
        self,
        optimizer: Optimizer = None,
        ram_threshold: float = 85.0,
        cpu_threshold: float = 75.0,
        interval_seconds: float = 4.0,
        enable_notifications: bool = True
    ):
        self.optimizer = optimizer or Optimizer()
        self.monitor = self.optimizer.monitor
        self.ram_threshold = ram_threshold
        self.cpu_threshold = cpu_threshold
        self.interval_seconds = interval_seconds
        self.enable_notifications = enable_notifications

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_auto_boost_time: float = 0.0
        self._callback: Optional[Callable[[dict], None]] = None

    def set_callback(self, cb: Callable[[dict], None]):
        self._callback = cb

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def is_running(self) -> bool:
        return self._running

    def _notify(self, title: str, message: str):
        if not self.enable_notifications:
            return
        try:
            subprocess.run(
                ["notify-send", "-a", "Zero-Optimise", "-u", "normal", title, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def _watch_loop(self):
        while self._running:
            try:
                mem = self.monitor.get_memory_usage()
                cpu = self.monitor.get_cpu_usage()
                ram_pct = mem.get("ram", {}).get("percent", 0.0)
                cpu_pct = cpu.get("percent", 0.0)

                current_time = time.time()
                # Cooldown of at least 30 seconds between auto-boosts
                if ram_pct >= self.ram_threshold and (current_time - self._last_auto_boost_time > 30.0):
                    # Trigger auto-reclaim
                    self._last_auto_boost_time = current_time
                    result = self.optimizer.run_smart_boost(allow_root_drop=False)
                    reniced_count = result.get("cpu_tuning", {}).get("reniced_count", 0)
                    freed_thumbs = result.get("thumbnails", {}).get("freed_mb", 0.0)

                    msg = f"RAM reached {ram_pct}%. Throttled {reniced_count} background tasks & freed {freed_thumbs} MB."
                    self._notify("Zero-Optimise Auto-Guard", msg)

                    if self._callback:
                        self._callback({
                            "type": "ram_autoboost",
                            "ram_pct": ram_pct,
                            "result": result
                        })

                # Check if overall CPU is high and background tasks need nice tuning
                elif cpu_pct >= self.cpu_threshold:
                    tune_res = self.optimizer.optimize_background_priorities()
                    count = tune_res.get("reniced_count", 0)
                    if count > 0:
                        if self._callback:
                            self._callback({
                                "type": "cpu_autotune",
                                "cpu_pct": cpu_pct,
                                "count": count
                            })

                if self._callback:
                    self._callback({
                        "type": "tick",
                        "mem": mem,
                        "cpu": cpu
                    })

            except Exception:
                pass

            time.sleep(self.interval_seconds)
