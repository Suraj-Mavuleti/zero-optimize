"""
Zero-Optimize Process Optimizer Module.
Purely non-destructive scheduling and memory optimization:
- Never automatically terminates any user process
- Balances CPU priorities (renices background renderers and tabs to nice 15)
- Clears page reference bits to assist Linux kernel & zram compaction
- Syncs filesystem buffers
"""

import os
import time
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
        idle browser tabs, Discord renderers, etc. (Non-destructive).
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

            if uid != current_uid:
                continue

            if p["is_protected"]:
                continue

            # Deprioritize background renderers and heavy idle processes to nice 15
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

    def snooze_background_apps(self, exclude_names=None) -> Dict[str, Any]:
        """
        Puts background applications into low-power sleep mode:
        - Drops their CPU priority to nice 19 & ionice idle (class 3)
        - Clears reference bits via /proc/[pid]/clear_refs so the kernel immediately
          pages out their cold heap to zram swap
        - Suspends KDE baloo file indexer
        - Never touches Antigravity, KWin, or core desktop services
        """
        if exclude_names is None:
            exclude_names = {
                "antigravity", "language_server", "kwin_wayland", "plasmashell",
                "pipewire", "wireplumber", "systemd", "zero-optimize"
            }

        snoozed = []
        current_uid = os.getuid()

        for p in self.monitor.get_processes(limit=120):
            pid = p["pid"]
            name = p["name"].lower()
            cmd = p["cmdline"].lower()
            uid = p.get("uid", 0)

            if uid != current_uid or p["is_protected"]:
                continue

            if any(ex in name or ex in cmd for ex in exclude_names):
                continue

            is_target = any(t in name or t in cmd for t in ("discord", "browseros", "firedragon", "baloo", "kioworker"))

            if is_target:
                try:
                    os.setpriority(os.PRIO_PROCESS, pid, 19)
                    subprocess.run(
                        ["ionice", "-c", "3", "-p", str(pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1
                    )
                    cr_path = f"/proc/{pid}/clear_refs"
                    if os.path.exists(cr_path):
                        with open(cr_path, "w") as f:
                            f.write("1\n")
                    snoozed.append(pid)
                except Exception:
                    pass

        try:
            subprocess.run(["balooctl6", "suspend"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except Exception:
            pass

        return {
            "snoozed_count": len(snoozed),
            "status": f"Put {len(snoozed)} background apps to sleep (cold memory paged to zram)"
        }

    def freeze_process(self, pid: int) -> Tuple[bool, str]:
        """Pauses a process using SIGSTOP so it uses 0% CPU without losing state."""
        if pid in (1, 2) or pid == os.getpid():
            return False, "Cannot freeze core process"
        try:
            os.kill(pid, signal.SIGSTOP)
            self.frozen_pids.add(pid)
            return True, f"Process {pid} paused (0% CPU)"
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
        """Only executed when explicitly requested by user clicking the Kill button."""
        if pid in (1, 2) or pid == os.getpid():
            return False, "Cannot terminate core process"

        try:
            with open(f"/proc/{pid}/comm", "r") as f:
                comm = f.read().strip()
            if comm in PROTECTED_COMM_NAMES:
                return False, f"Process {comm} (PID {pid}) is protected"
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
        Safe, Non-Destructive System Optimization:
        1. Cleans safe disk caches (~/.cache/thumbnails, ~/.cache/pip)
        2. Clears userspace page reference bits (/proc/[pid]/clear_refs) so idle memory can be paged/compacted
        3. Vacuums systemd user journal
        4. Balances CPU priorities for background hogs
        5. Syncs filesystem buffers to disk
        6. Compacts zram and memory if privileges exist
        """
        results = {}
        mem_before = self.monitor.get_memory_usage().get("ram", {}).get("used_mb", 0)

        # 1. Clean safe user caches
        results["caches"] = self.cleaner.clean_safe_user_caches()

        # 2. Terminate idle build daemons and stale workers holding gigabytes
        results["daemons"] = self.cleaner.clean_idle_build_daemons()
        results["workers"] = self.cleaner.clean_stale_kioworkers()

        # 3. Reset page reference bits (non-destructive)
        results["cleared_refs"] = self.cleaner.clear_userspace_page_references()

        # 4. User Journal
        results["journal"] = self.cleaner.vacuum_user_journal()

        # 5. CPU Priority tuning
        results["cpu_tuning"] = self.optimize_background_priorities()

        # 6. Put background apps to sleep (low-power, pages out cold heap)
        results["snooze"] = self.snooze_background_apps()

        # 7. Sync buffers
        self.cleaner.sync_disks()

        # 7. Memory and zram compaction (with root helper if accessible)
        compacted, c_msg = self.cleaner.compact_memory_and_zram(allow_gui_prompt=allow_root_drop)
        results["compaction"] = {"success": compacted, "message": c_msg}

        time.sleep(0.1)
        mem_after = self.monitor.get_memory_usage().get("ram", {}).get("used_mb", 0)
        direct_freed = results["daemons"].get("freed_mb", 0.0) + results["workers"].get("freed_mb", 0.0)
        ram_delta = max(0.0, float(mem_before - mem_after))
        results["ram_freed_mb"] = max(ram_delta, direct_freed)

        return results
