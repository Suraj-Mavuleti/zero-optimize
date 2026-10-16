"""
Zero-Optimize System Optimizer Engine.
Intelligently optimizes CPU scheduling, memory footprints, and manages background processes.
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
        Lowers CPU (nice +15) and I/O priority (idle class) for heavy background renderers
        and helper processes so interactive apps and games never stutter.
        """
        processes = self.monitor.get_processes()
        reniced = []
        my_uid = os.getuid()

        for p in processes:
            pid = p["pid"]
            category = p["category"]
            user = p["user"]
            uid = p.get("uid", -1)
            nice = p["nice"]
            name = p["name"]

            # Only manage our own user's processes
            if uid != my_uid or p["is_protected"]:
                continue

            # Identify background candidates
            is_background_hog = category in ("browser_tab_renderer", "heavy_app") or (
                any(kw in p["cmdline"].lower() for kw in [
                    "--type=renderer", "discord", "steam", "firedragon -contentproc",
                    "kioworker", "language_server"
                ]) and not any(kw in p["cmdline"].lower() for kw in [
                    "plasmashell", "kwin", "konsole", "alacritty", "kitty"
                ])
            )

            if is_background_hog and nice < 10:
                try:
                    # renice to +15 (lower priority)
                    os.setpriority(os.PRIO_PROCESS, pid, 15)
                    # ionice to idle or best-effort low priority
                    subprocess.run(["ionice", "-c", "2", "-n", "7", "-p", str(pid)], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    reniced.append({"pid": pid, "name": name, "old_nice": nice, "new_nice": 15})
                except Exception:
                    continue

        return {
            "reniced_count": len(reniced),
            "reniced_processes": reniced,
            "status": f"Optimized CPU scheduling for {len(reniced)} background processes"
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

        # Check protected name
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
            return True, f"Sent {'SIGKILL' if force else 'SIGTERM'} to PID {pid}"
        except Exception as e:
            return False, f"Failed to terminate process {pid}: {e}"

    def run_smart_boost(self, allow_root_drop: bool = True) -> Dict[str, Any]:
        """
        Complete 1-Click System Optimization:
        1. Cleans user thumbnail cache
        2. Kills orphaned kioworkers
        3. Vacuums user journal
        4. Optimizes CPU priorities (renice background hogs)
        5. Syncs filesystem buffers
        6. Drops pagecache and compacts memory (if authorized)
        """
        results = {}

        # 1. Thumbnails
        results["thumbnails"] = self.cleaner.clean_thumbnail_cache()

        # 2. Orphaned Workers
        results["workers"] = self.cleaner.clean_stale_kioworkers()

        # 3. User Journal
        results["journal"] = self.cleaner.vacuum_user_journal()

        # 4. CPU Priority optimization
        results["cpu_tuning"] = self.optimize_background_priorities()

        # 5. Privileged cache drop & compaction
        cache_dropped = False
        cache_msg = "Skipped"
        if allow_root_drop:
            cache_dropped, cache_msg = self.cleaner.drop_caches_privileged(use_gui_auth=True)
            if cache_dropped:
                self.cleaner.compact_memory_privileged(use_gui_auth=False)

        results["cache_drop"] = {"success": cache_dropped, "message": cache_msg}

        return results
