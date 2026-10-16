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
import subprocess
from typing import Dict, List, Any, Tuple

SAFE_CACHE_DIRS = [
    os.path.expanduser("~/.cache/thumbnails"),
    os.path.expanduser("~/.cache/pip"),
    os.path.expanduser("~/.cache/go-build"),
]


class Cleaner:
    def __init__(self, helper_path: str = None):
        if helper_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.helper_path = os.path.join(base_dir, "helper", "zero-optimize-root-helper")
        else:
            self.helper_path = helper_path

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

    def compact_memory_and_zram(self) -> Tuple[bool, str]:
        """Triggers zram and kernel memory compaction via helper if available."""
        self.sync_disks()

        # Try sudo without password prompt
        try:
            res = subprocess.run(
                ["sudo", "-n", self.helper_path, "compact"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0:
                return True, "Memory & zram compacted"
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
