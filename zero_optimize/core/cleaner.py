"""
Zero-Optimize Memory & Cache Cleaner Module.
Handles userspace cache clearing, aggressive stale worker termination,
clear_refs page reference clearing, and non-blocking maintenance.
"""

import os
import glob
import shutil
import signal
import subprocess
from typing import Dict, List, Any, Tuple
from zero_optimize.core.system_monitor import PROTECTED_COMM_NAMES

BUILD_DAEMON_PATTERNS = [
    "org.gradle.launcher.daemon",
    "gradle-launcher",
    "gradle-wrapper",
    "kotlin-compiler-embeddable",
    "jdtls",
    "rust-analyzer-proc-macro-srv",
    "jest-worker",
    "pytest-xdist"
]

STALE_WORKER_PATTERNS = [
    "kioworker",
    "kio_thumbnail",
    "thumbnail.so",
    "tracker-miner",
    "tracker-extract"
]


class Cleaner:
    def __init__(self, helper_path: str = None):
        if helper_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.helper_path = os.path.join(base_dir, "helper", "zero-optimize-root-helper")
        else:
            self.helper_path = helper_path

    def clean_thumbnail_cache(self) -> Dict[str, Any]:
        """Clears user thumbnail cache (~/.cache/thumbnails)."""
        cache_dir = os.path.expanduser("~/.cache/thumbnails")
        freed_bytes = 0
        deleted_count = 0

        if os.path.exists(cache_dir):
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
            "status": f"Cleaned {deleted_count} thumbnails, reclaimed {freed_mb} MB"
        }

    def clean_stale_kioworkers(self) -> Dict[str, Any]:
        """Kills orphaned thumbnail generators and tracker indexers taking memory."""
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

                        os.kill(pid, signal.SIGKILL)
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

    def clean_idle_build_daemons(self) -> Dict[str, Any]:
        """Terminates forgotten background compilation & Gradle daemons holding gigabytes of RAM."""
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
                        cmd = f.read().replace(b"\x00", b" ").decode(errors="replace")

                    # Target idle gradle daemons, stale test runners, build workers
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

    def clear_userspace_page_references(self) -> int:
        """
        Writes '1' to /proc/[pid]/clear_refs for current user's processes.
        Forces the kernel to unmark active page references on idle memory,
        allowing the kernel and zram/kswapd to immediately evict cold pages without thrashing.
        """
        cleared_count = 0
        current_uid = os.getuid()

        for pid_dir in glob.glob("/proc/[0-9]*"):
            pid = os.path.basename(pid_dir)
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
        """Flushes all unwritten system buffers to disk."""
        try:
            subprocess.run(["sync"], check=True, timeout=5)
            return True
        except Exception:
            return False

    def drop_caches_privileged(self, use_gui_auth: bool = False) -> Tuple[bool, str]:
        """
        Drops Linux pagecache, dentries, and inodes via /proc/sys/vm/drop_caches.
        NOTE: use_gui_auth is defaulted to False to prevent annoying pkexec popups.
        """
        self.sync_disks()

        if os.geteuid() == 0:
            try:
                with open("/proc/sys/vm/drop_caches", "w") as f:
                    f.write("3\n")
                return True, "Caches dropped (Root)"
            except Exception as e:
                return False, f"Failed writing to /proc/sys/vm/drop_caches: {e}"

        # Try sudo -n (NOPASSWD) without interactive prompt
        try:
            res = subprocess.run(
                ["sudo", "-n", self.helper_path, "drop_caches"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0:
                return True, "Caches dropped via sudo"
        except Exception:
            pass

        # Only use pkexec if explicitly requested by interactive button click
        if use_gui_auth:
            try:
                res = subprocess.run(
                    ["pkexec", self.helper_path, "drop_caches"],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if res.returncode == 0:
                    return True, "Caches dropped via Polkit"
                return False, "Authorization cancelled"
            except Exception as e:
                return False, f"Error calling pkexec: {e}"

        return False, "Root privileges required (sudoers or helper)"

    def compact_memory_privileged(self, use_gui_auth: bool = False) -> Tuple[bool, str]:
        """Compacts memory to stop kswapd0 thrashing."""
        if os.geteuid() == 0:
            try:
                with open("/proc/sys/vm/compact_memory", "w") as f:
                    f.write("1\n")
                return True, "Memory compacted"
            except Exception as e:
                return False, f"Failed compacting memory: {e}"

        try:
            res = subprocess.run(
                ["sudo", "-n", self.helper_path, "compact"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0:
                return True, "Memory compacted via sudo"
        except Exception:
            pass

        if use_gui_auth:
            try:
                res = subprocess.run(
                    ["pkexec", self.helper_path, "compact"],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if res.returncode == 0:
                    return True, "Memory compacted via Polkit"
            except Exception:
                pass

        return False, "Root privileges required"

    def vacuum_user_journal(self) -> Dict[str, Any]:
        """Vacuums systemd user journal to free RAM and disk logs."""
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
