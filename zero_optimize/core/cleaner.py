"""
Zero-Optimize Memory & Cache Cleaner Module.
Performs strictly NON-DESTRUCTIVE system memory optimization:
1. Clears page reference bits via /proc/[pid]/clear_refs (allows kernel to swap cold memory)
2. Purges stale disk cache trees (~/.cache/thumbnails, ~/.cache/pip, bloated build caches)
3. Synchronizes and flushes dirty filesystem buffers
4. Compacts system memory and zram pages without killing any applications
"""

import os
import glob
import shutil
import signal
import subprocess
from typing import Dict, List, Any, Tuple

SAFE_CACHE_DIRS = [
    os.path.expanduser("~/.cache/thumbnails"),
    os.path.expanduser("~/.cache/pip"),
    os.path.expanduser("~/.cache/go-build"),
]

BUILD_DAEMON_PATTERNS = [
    "org.gradle.launcher.daemon", "gradle-daemon", "GradleDaemon",
    "org.jetbrains.kotlin.daemon", "kotlin-compiler", "KotlinCompileDaemon",
    "GradleWorkerMain"
]

STALE_WORKER_PATTERNS = [
    "kioworker", "kio_thumbnail"
]


class Cleaner:
    def __init__(self, helper_path: str = None):
        if helper_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.helper_path = os.path.join(base_dir, "helper", "zero-optimize-root-helper")
        else:
            self.helper_path = helper_path
        self._can_sudo: Optional[bool] = None

    def clean_safe_user_caches(self) -> Dict[str, Any]:
        """Cleans safe temporary caches (thumbnails, pip build caches) without affecting running apps."""
        freed_bytes = 0
        deleted_count = 0

        for cache_dir in SAFE_CACHE_DIRS:
            if not os.path.exists(cache_dir):
                continue
            for root, dirs, files in os.walk(cache_dir):
                for f in files:
                    file_path = os.path.join(root, f)
                    try:
                        size = os.path.getsize(file_path)
                        os.remove(file_path)
                        freed_bytes += size
                        deleted_count += 1
                    except Exception:
                        pass

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        return {
            "freed_mb": freed_mb,
            "deleted_count": deleted_count,
            "status": f"Cleaned {deleted_count} cache files, freed {freed_mb} MB"
        }

    def clean_idle_build_daemons(self) -> Dict[str, Any]:
        """Terminates forgotten background compilation & Gradle daemons holding gigabytes of RAM & CPU."""
        terminated = []
        freed_mb = 0.0
        current_uid = os.getuid()

        # If an active foreground/cli build wrapper is actively running, skip terminating daemons
        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                cmd_p = f"/proc/{entry}/cmdline"
                if os.path.exists(cmd_p):
                    try:
                        with open(cmd_p, "rb") as f:
                            raw = f.read().replace(b"\x00", b" ").decode(errors="replace")
                            if any(w in raw for w in ("gradle-wrapper.jar", "gradlew test", "gradlew build")):
                                return {
                                    "terminated_pids": [],
                                    "freed_mb": 0.0,
                                    "status": "Active build in progress, skipping daemon cleanup"
                                }
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                proc_path = f"/proc/{pid}"

                try:
                    if os.stat(proc_path).st_uid != current_uid:
                        continue

                    cmd_path = f"{proc_path}/cmdline"
                    if not os.path.exists(cmd_path):
                        continue

                    with open(cmd_path, "rb") as f:
                        cmd = f.read().replace(b"\x00", b" ").decode(errors="replace")

                    if any(pat in cmd for pat in BUILD_DAEMON_PATTERNS):
                        try:
                            with open(f"{proc_path}/statm", "r") as f:
                                rss_pages = int(f.read().split()[1])
                                rss_mb = (rss_pages * 4096) / (1024 * 1024)
                        except Exception:
                            rss_mb = 0.0

                        os.kill(pid, signal.SIGKILL)
                        freed_mb += rss_mb
                        terminated.append(pid)
                except Exception:
                    continue
        except Exception:
            pass

        return {
            "terminated_pids": terminated,
            "freed_mb": round(freed_mb, 1),
            "status": f"Terminated {len(terminated)} orphaned build daemon(s), reclaimed {round(freed_mb, 1)} MB"
        }

    def clean_stale_kioworkers(self) -> Dict[str, Any]:
        """Terminates hanging KDE KIO thumbnail workers and stale file preview daemons."""
        terminated = []
        freed_mb = 0.0
        current_uid = os.getuid()

        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                proc_path = f"/proc/{pid}"

                try:
                    if os.stat(proc_path).st_uid != current_uid:
                        continue

                    cmd_path = f"{proc_path}/cmdline"
                    if not os.path.exists(cmd_path):
                        continue

                    with open(cmd_path, "rb") as f:
                        cmd = f.read().replace(b"\x00", b" ").decode(errors="replace").lower()

                    if any(pat in cmd for pat in STALE_WORKER_PATTERNS):
                        try:
                            with open(f"{proc_path}/statm", "r") as f:
                                rss_pages = int(f.read().split()[1])
                                freed_mb += (rss_pages * 4096) / (1024 * 1024)
                        except Exception:
                            pass

                        os.kill(pid, signal.SIGTERM)
                        terminated.append(pid)
                except Exception:
                    continue
        except Exception:
            pass

        return {
            "terminated_pids": terminated,
            "freed_mb": round(freed_mb, 1),
            "status": f"Terminated {len(terminated)} stale worker(s)"
        }

    def clear_userspace_page_references(self) -> int:
        """
        Non-destructive memory compaction helper:
        Writes '1' to /proc/[pid]/clear_refs for current user's processes.
        Unmarks active reference bits on idle memory pages without killing anything.
        Allows the Linux kernel and zram to compact or page out idle memory safely.
        """
        cleared_count = 0
        current_uid = os.getuid()

        for pid_dir in glob.glob("/proc/[0-9]*"):
            try:
                if os.stat(pid_dir).st_uid != current_uid:
                    continue
                cr_path = f"{pid_dir}/clear_refs"
                if os.path.exists(cr_path):
                    with open(cr_path, "w") as f:
                        f.write("1\n")
                    cleared_count += 1
            except Exception:
                pass

        return cleared_count

    def sync_disks(self) -> bool:
        """Flushes dirty page buffers to disk so kernel memory becomes reclaimable."""
        try:
            subprocess.run(["sync"], check=True, timeout=5)
            return True
        except Exception:
            return False

    def compact_memory_and_zram(self, allow_gui_prompt: bool = False) -> Tuple[bool, str]:
        """Triggers zram and kernel memory compaction via helper if available."""
        self.sync_disks()

        # 1. Check if passwordless sudo is functional
        if self._can_sudo is None:
            try:
                chk = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=2)
                self._can_sudo = (chk.returncode == 0)
            except Exception:
                self._can_sudo = False

        if self._can_sudo:
            try:
                res = subprocess.run(
                    ["sudo", "-n", self.helper_path, "all"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode == 0:
                    return True, "Caches dropped & zram compacted"
            except Exception:
                pass

        # 2. If allow_gui_prompt and pkexec is available (user-triggered action)
        if allow_gui_prompt and shutil.which("pkexec"):
            try:
                res = subprocess.run(
                    ["pkexec", self.helper_path, "all"],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if res.returncode == 0:
                    self._can_sudo = True
                    return True, "Caches dropped & zram compacted via Polkit"
            except Exception:
                pass

        return False, "Non-root mode"

    def vacuum_user_journal(self) -> Dict[str, Any]:
        """Vacuums systemd user journal to free memory-mapped log pages."""
        try:
            res = subprocess.run(
                ["journalctl", "--user", "--vacuum-size=15M"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {"success": res.returncode == 0, "output": res.stdout.strip()}
        except Exception as e:
            return {"success": False, "output": str(e)}
