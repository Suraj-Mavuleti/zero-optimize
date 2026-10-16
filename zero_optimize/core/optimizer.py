"""
Zero-Optimize Process Optimizer Module.
Manages priority balancing, memory reclaiming, stale worker elimination, and CPU throttling.
"""

import os
import signal
import subprocess
from typing import Dict, List, Any, Tuple
from zero_optimize.core.system_monitor import SystemMonitor, PROTECTED_COMM_NAMES
from zero_optimize.core.cleaner import Cleaner


class Optimizer:
    def __init__(self, monitor: SystemMonitor = None, cleaner: Cleaner = None):
        self.monitor = monitor or SystemMonitor()
        self.cleaner = cleaner or Cleaner()
        self.frozen_pids: set = set()

    def optimize_background_priorities(self) -> Dict[str, Any]:
        """
        Dynamically adjusts scheduling priority for background hogs,
        browser tabs, Discord workers, and compiler threads.
        """
        processes = self.monitor.get_processes()
        reniced = []
        current_uid = os.getuid()

        for p in processes:
            pid = p["pid"]
            nice = p["nice"]
            category = p["category"]
            name = p["name"]
            uid = p.get("uid", 0)

            # Only manage our own user's processes
            if uid != current_uid:
                continue

            # Skip core system processes
            if p["is_protected"]:
                continue

            # Prioritize foreground / interactive applications (keep normal nice 0)
            # Deprioritize background renderers, idle browser tabs, and heavy background daemons
            is_background_hog = category in ("browser_tab_renderer", "heavy_app") or (
                p["cpu_pct"] > 5.0 and nice < 10 and category != "system_protected"
            )

            if is_background_hog and nice < 15:
                try:
                    os.setpriority(os.PRIO_PROCESS, pid, 15)
                    subprocess.run(
                        ["ionice", "-c", "2", "-n", "7", "-p", str(pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1
                    )
                    reniced.append({"pid": pid, "name": name, "new_nice": 15})
                except Exception:
                    continue

        return {
            "reniced_count": len(reniced),
            "reniced_processes": reniced,
            "status": f"Balanced CPU scheduling for {len(reniced)} background tasks"
        }

    def freeze_process(self, pid: int) -> Tuple[bool, str]:
        """Pauses a process using SIGSTOP so it uses 0% CPU and 0% disk while remaining alive."""
        if pid in (1, 2) or pid == os.getpid():
            return False, "Cannot freeze core process"
        try:
            os.kill(pid, signal.SIGSTOP)
            self.frozen_pids.add(pid)
            return True, f"Process {pid} suspended (0% CPU)"
        except Exception as e:
            return False, f"Failed freezing process {pid}: {e}"

    def thaw_process(self, pid: int) -> Tuple[bool, str]:
        """Resumes a paused process using SIGCONT."""
        try:
            os.kill(pid, signal.SIGCONT)
            self.frozen_pids.discard(pid)
            return True, f"Process {pid} resumed"
        except Exception as e:
            return False, f"Failed resuming process {pid}: {e}"

    def terminate_process(self, pid: int, force: bool = False) -> Tuple[bool, str]:
        """Safely terminates a process."""
        if pid in (1, 2) or pid == os.getpid():
            return False, "Cannot terminate core process"

        try:
            with open(f"/proc/{pid}/comm", "r") as f:
                comm = f.read().strip()
            if comm in PROTECTED_COMM_NAMES:
                return False, f"Process {comm} (PID {pid}) is protected from termination"
        except Exception:
            pass

        try:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            return True, f"Terminated PID {pid}"
        except Exception as e:
            return False, f"Failed to terminate process {pid}: {e}"

    def run_smart_boost(self, allow_root_drop: bool = False) -> Dict[str, Any]:
        """
        Complete Instant System Optimization (No Popups):
        1. Cleans user thumbnail cache
        2. Kills orphaned kioworkers
        3. Terminates stale build/Gradle daemons taking gigabytes
        4. Clears page references in /proc/[pid]/clear_refs so inactive pages are evicted
        5. Balances CPU priorities (renice background hogs to nice 15)
        6. Vacuums systemd user journal
        7. Flushes unwritten buffers to disk
        """
        results = {}

        # 1. Thumbnails
        results["thumbnails"] = self.cleaner.clean_thumbnail_cache()

        # 2. Orphaned Workers
        results["workers"] = self.cleaner.clean_stale_kioworkers()

        # 3. Kill idle build daemons (Gradle/Kotlin/etc.)
        results["daemons"] = self.cleaner.clean_idle_build_daemons()

        # 4. User-level memory reference clearing (evicts cold heap pages)
        results["cleared_refs"] = self.cleaner.clear_userspace_page_references()

        # 5. User Journal
        results["journal"] = self.cleaner.vacuum_user_journal()

        # 6. CPU Priority optimization
        results["cpu_tuning"] = self.optimize_background_priorities()

        # 7. Sync buffers to disk
        self.cleaner.sync_disks()

        # 8. Privileged cache drop (strictly without intrusive GUI popup)
        cache_dropped, cache_msg = self.cleaner.drop_caches_privileged(use_gui_auth=False)
        if cache_dropped:
            self.cleaner.compact_memory_privileged(use_gui_auth=False)
        results["cache_drop"] = {"success": cache_dropped, "message": cache_msg}

        return results
