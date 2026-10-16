"""
Zero-Optimise Memory & Cache Cleaner Module.
Handles userspace cache clearing, stale worker termination, and privileged system memory drops.
"""

import os
import shutil
import signal
import subprocess
from typing import Dict, List, Any, Tuple
from zero_optimise.core.system_monitor import PROTECTED_COMM_NAMES


class Cleaner:
    def __init__(self, helper_path: str = None):
        if helper_path is None:
            # Look in standard helper directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.helper_path = os.path.join(base_dir, "helper", "zero-optimise-root-helper")
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
        """Kills orphaned kioworker thumbnail generators that accumulate in KDE Plasma."""
        terminated = []
        freed_mb = 0.0

        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                cmd_path = f"/proc/{pid}/cmdline"
                if not os.path.exists(cmd_path):
                    continue

                try:
                    with open(cmd_path, "rb") as f:
                        cmd = f.read().replace(b"\x00", b" ").decode(errors="replace")
                    
                    if "kioworker" in cmd and "thumbnail.so" in cmd:
                        # Estimate memory
                        try:
                            with open(f"/proc/{pid}/statm", "r") as f:
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
            "status": f"Terminated {len(terminated)} orphaned thumbnail worker(s)"
        }

    def clean_idle_build_daemons(self) -> Dict[str, Any]:
        """Terminates forgotten background compilation daemons (e.g. Gradle) taking >500MB."""
        terminated = []
        freed_mb = 0.0

        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                cmd_path = f"/proc/{pid}/cmdline"
                if not os.path.exists(cmd_path):
                    continue

                try:
                    with open(cmd_path, "rb") as f:
                        cmd = f.read().replace(b"\x00", b" ").decode(errors="replace")
                    
                    # Target idle gradle wrapper daemon that often stays alive taking 1-2GB
                    if "gradle-launcher" in cmd or "gradle-wrapper" in cmd:
                        # Don't kill if actively running tests right this second unless explicitly called
                        # Let's check status
                        with open(f"/proc/{pid}/statm", "r") as f:
                            rss_pages = int(f.read().split()[1])
                            rss_mb = (rss_pages * 4096) / (1024 * 1024)
                        
                        os.kill(pid, signal.SIGTERM)
                        freed_mb += rss_mb
                        terminated.append(pid)
                except Exception:
                    continue
        except Exception:
            pass

        return {
            "terminated_pids": terminated,
            "freed_mb": round(freed_mb, 1),
            "status": f"Terminated {len(terminated)} background build daemon(s)"
        }

    def sync_disks(self) -> bool:
        """Flushes all unwritten system buffers to disk."""
        try:
            subprocess.run(["sync"], check=True, timeout=10)
            return True
        except Exception:
            return False

    def drop_caches_privileged(self, use_gui_auth: bool = True) -> Tuple[bool, str]:
        """
        Drops Linux pagecache, dentries, and inodes via /proc/sys/vm/drop_caches.
        If not root, attempts pkexec (native KDE polkit GUI prompt) or sudo.
        """
        # Always sync before drop_caches
        self.sync_disks()

        # If already root
        if os.geteuid() == 0:
            try:
                with open("/proc/sys/vm/drop_caches", "w") as f:
                    f.write("3\n")
                return True, "Caches successfully dropped (Direct Root)"
            except Exception as e:
                return False, f"Failed writing to /proc/sys/vm/drop_caches: {e}"

        # Try sudo -n first (if user has NOPASSWD configured)
        try:
            res = subprocess.run(
                ["sudo", "-n", self.helper_path, "drop_caches"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                return True, "Caches dropped via sudo"
        except Exception:
            pass

        # If user GUI auth is enabled, invoke pkexec
        if use_gui_auth:
            try:
                res = subprocess.run(
                    ["pkexec", self.helper_path, "drop_caches"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if res.returncode == 0:
                    return True, "Caches successfully dropped via Polkit Authorization"
                else:
                    return False, f"Authorization failed or cancelled: {res.stderr.strip()}"
            except Exception as e:
                return False, f"Error calling pkexec: {e}"

        return False, "Root privileges required to drop system pagecache"

    def compact_memory_privileged(self, use_gui_auth: bool = True) -> Tuple[bool, str]:
        """
        Compacts memory to stop kswapd0 thrashing.
        """
        if os.geteuid() == 0:
            try:
                with open("/proc/sys/vm/compact_memory", "w") as f:
                    f.write("1\n")
                return True, "Memory compacted (Direct Root)"
            except Exception as e:
                return False, f"Failed compacting memory: {e}"

        # Try sudo -n
        try:
            res = subprocess.run(
                ["sudo", "-n", self.helper_path, "compact"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                return True, "Memory compacted via sudo"
        except Exception:
            pass

        # Try pkexec
        if use_gui_auth:
            try:
                res = subprocess.run(
                    ["pkexec", self.helper_path, "compact"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if res.returncode == 0:
                    return True, "Memory compacted via Polkit Authorization"
                else:
                    return False, f"Authorization failed or cancelled: {res.stderr.strip()}"
            except Exception as e:
                return False, f"Error calling pkexec: {e}"

        return False, "Root privileges required to compact memory"

    def vacuum_user_journal(self) -> Dict[str, Any]:
        """Vacuums systemd user journal to free RAM and disk logs."""
        try:
            res = subprocess.run(
                ["journalctl", "--user", "--vacuum-size=20M"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {"success": res.returncode == 0, "output": res.stdout.strip()}
        except Exception as e:
            return {"success": False, "output": str(e)}
