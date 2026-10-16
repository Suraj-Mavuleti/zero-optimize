"""
System resource monitoring module using direct /proc filesystem inspection.
Pure Python, zero third-party dependencies, ultra-lightweight.
"""

import os
import time
import pwd
from typing import Dict, List, Any, Optional

PAGE_SIZE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096
CLK_TCK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100

# Critical system processes that must never be terminated
PROTECTED_COMM_NAMES = {
    "systemd", "init", "kwin_wayland", "kwin_x11", "plasmashell",
    "pipewire", "pipewire-pulse", "wireplumber", "dbus-daemon", "dbus-broker",
    "Xwayland", "sddm", "polkitd", "udevd", "systemd-journald",
    "systemd-udevd", "systemd-logind", "systemd-resolved", "kded6",
    "ksmserver", "krunner", "zero-optimise"
}


class SystemMonitor:
    def __init__(self):
        self._last_cpu_times: Dict[str, tuple] = {}
        self._last_proc_times: Dict[int, tuple] = {}
        self._last_proc_sample_time: float = 0.0
        self._uid_to_username: Dict[int, str] = {}
        
        # Initial sample to prime CPU calculation
        self._sample_cpu_stat()

    def _get_username(self, uid: int) -> str:
        if uid not in self._uid_to_username:
            try:
                self._uid_to_username[uid] = pwd.getpwuid(uid).pw_name
            except (KeyError, Exception):
                self._uid_to_username[uid] = str(uid)
        return self._uid_to_username[uid]

    def _sample_cpu_stat(self) -> Dict[str, tuple]:
        """Reads /proc/stat and returns raw ticks for overall and each core."""
        cpu_stats = {}
        try:
            with open("/proc/stat", "r") as f:
                for line in f:
                    if line.startswith("cpu"):
                        parts = line.strip().split()
                        name = parts[0]
                        # fields: user, nice, system, idle, iowait, irq, softirq, steal
                        vals = [float(x) for x in parts[1:9]]
                        idle = vals[3] + vals[4]  # idle + iowait
                        total = sum(vals)
                        cpu_stats[name] = (idle, total)
        except Exception:
            pass
        return cpu_stats

    def get_cpu_usage(self) -> Dict[str, Any]:
        """Returns overall CPU usage % and per-core usage %."""
        new_stats = self._sample_cpu_stat()
        if not self._last_cpu_times:
            self._last_cpu_times = new_stats
            time.sleep(0.05)
            new_stats = self._sample_cpu_stat()

        usage = {}
        total_usage = 0.0
        cores = []

        for name, (idle2, total2) in new_stats.items():
            if name in self._last_cpu_times:
                idle1, total1 = self._last_cpu_times[name]
                idle_delta = idle2 - idle1
                total_delta = total2 - total1
                if total_delta > 0:
                    pct = max(0.0, min(100.0, (1.0 - idle_delta / total_delta) * 100.0))
                else:
                    pct = 0.0
            else:
                pct = 0.0

            if name == "cpu":
                total_usage = round(pct, 1)
            else:
                cores.append({"core": name, "percent": round(pct, 1)})

        self._last_cpu_times = new_stats
        
        # Load averages
        load1, load5, load15 = 0.0, 0.0, 0.0
        try:
            with open("/proc/loadavg", "r") as f:
                parts = f.read().strip().split()
                load1, load5, load15 = float(parts[0]), float(parts[1]), float(parts[2])
        except Exception:
            pass

        return {
            "percent": total_usage,
            "cores": cores,
            "load_1m": load1,
            "load_5m": load5,
            "load_15m": load15
        }

    def get_memory_usage(self) -> Dict[str, Any]:
        """Returns detailed RAM, Swap, and ZRAM usage in MB and percentages."""
        meminfo = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        meminfo[key] = int(val)  # In kB
        except Exception:
            return {}

        total_kb = meminfo.get("MemTotal", 1)
        free_kb = meminfo.get("MemFree", 0)
        available_kb = meminfo.get("MemAvailable", free_kb)
        buffers_kb = meminfo.get("Buffers", 0)
        cached_kb = meminfo.get("Cached", 0)
        dirty_kb = meminfo.get("Dirty", 0)
        sreclaimable_kb = meminfo.get("SReclaimable", 0)
        used_kb = total_kb - available_kb

        swap_total_kb = meminfo.get("SwapTotal", 0)
        swap_free_kb = meminfo.get("SwapFree", 0)
        swap_used_kb = swap_total_kb - swap_free_kb

        # Convert to MB
        total_mb = total_kb // 1024
        used_mb = used_kb // 1024
        free_mb = free_kb // 1024
        available_mb = available_kb // 1024
        cache_mb = (cached_kb + sreclaimable_kb + buffers_kb) // 1024
        dirty_mb = dirty_kb // 1024
        swap_total_mb = swap_total_kb // 1024
        swap_used_mb = swap_used_kb // 1024

        ram_pct = round((used_kb / total_kb) * 100.0, 1)
        swap_pct = round((swap_used_kb / swap_total_kb) * 100.0, 1) if swap_total_kb > 0 else 0.0

        # Check ZRAM info if present
        zram_info = self._get_zram_info()

        return {
            "ram": {
                "total_mb": total_mb,
                "used_mb": used_mb,
                "available_mb": available_mb,
                "free_mb": free_mb,
                "cache_mb": cache_mb,
                "dirty_mb": dirty_mb,
                "percent": ram_pct,
            },
            "swap": {
                "total_mb": swap_total_mb,
                "used_mb": swap_used_mb,
                "free_mb": (swap_total_mb - swap_used_mb),
                "percent": swap_pct,
            },
            "zram": zram_info,
        }

    def _get_zram_info(self) -> Optional[Dict[str, Any]]:
        """Parses zram0 statistics from sysfs if available."""
        zram_path = "/sys/block/zram0"
        if not os.path.exists(zram_path):
            return None
        try:
            with open(f"{zram_path}/disksize", "r") as f:
                disksize = int(f.read().strip()) // (1024 * 1024)
            with open(f"{zram_path}/orig_data_size", "r") as f:
                orig_size = int(f.read().strip()) // (1024 * 1024)
            with open(f"{zram_path}/mem_used_total", "r") as f:
                compr_size = int(f.read().strip()) // (1024 * 1024)
            ratio = round(orig_size / compr_size, 2) if compr_size > 0 else 1.0
            return {
                "disksize_mb": disksize,
                "data_size_mb": orig_size,
                "compr_size_mb": compr_size,
                "ratio": ratio,
            }
        except Exception:
            return None

    def get_uptime_seconds(self) -> float:
        try:
            with open("/proc/uptime", "r") as f:
                return float(f.read().split()[0])
        except Exception:
            return 0.0

    def get_processes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scans /proc/[pid] and computes CPU%, Memory, status, and category."""
        if not self._last_proc_times:
            # First time sampling processes, prime the previous table with a brief 0.1s sleep
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                try:
                    with open(f"/proc/{pid}/stat", "r") as f:
                        sc = f.read()
                    cs = sc.find("(")
                    ce = sc.rfind(")")
                    if cs != -1 and ce != -1:
                        r = sc[ce + 2:].split()
                        self._last_proc_times[pid] = int(r[11]) + int(r[12])
                except Exception:
                    pass
            self._last_proc_sample_time = time.time()
            time.sleep(0.12)
            current_time = time.time()
            time_delta = current_time - self._last_proc_sample_time
            self._last_proc_sample_time = current_time


        uptime = self.get_uptime_seconds()
        total_ram_kb = 1
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_ram_kb = int(line.split()[1])
                        break
        except Exception:
            pass

        num_cores = os.cpu_count() or 1
        processes = []
        new_proc_times = {}

        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            pid = int(entry)
            proc_path = f"/proc/{pid}"

            try:
                # Read /proc/[pid]/stat
                with open(f"{proc_path}/stat", "r") as f:
                    stat_content = f.read()

                # Process name is inside parentheses (e.g. (plasmashell))
                comm_start = stat_content.find("(")
                comm_end = stat_content.rfind(")")
                if comm_start == -1 or comm_end == -1:
                    continue
                comm = stat_content[comm_start + 1:comm_end]
                rest = stat_content[comm_end + 2:].split()

                state = rest[0]
                ppid = int(rest[1])
                utime = int(rest[11])
                stime = int(rest[12])
                nice = int(rest[16])
                starttime_ticks = int(rest[19])
                rss_pages = int(rest[21])

                total_proc_ticks = utime + stime
                new_proc_times[pid] = total_proc_ticks

                # CPU percentage calculation normalized across cores (0-100%)
                cpu_pct = 0.0
                if pid in self._last_proc_times and time_delta > 0:
                    tick_diff = total_proc_ticks - self._last_proc_times[pid]
                    cpu_pct = (tick_diff / CLK_TCK) / (time_delta * num_cores) * 100.0
                    cpu_pct = max(0.0, min(100.0, round(cpu_pct, 1)))


                # Memory
                rss_kb = (rss_pages * PAGE_SIZE) // 1024
                rss_mb = round(rss_kb / 1024, 1)
                mem_pct = round((rss_kb / total_ram_kb) * 100.0, 1)

                # Command line
                cmdline = ""
                try:
                    with open(f"{proc_path}/cmdline", "rb") as f:
                        raw = f.read()
                        cmdline = raw.replace(b"\x00", b" ").decode(errors="replace").strip()
                except Exception:
                    pass
                if not cmdline:
                    cmdline = comm

                # Owner
                uid = 0
                try:
                    stat_info = os.stat(proc_path)
                    uid = stat_info.st_uid
                except Exception:
                    pass
                user = self._get_username(uid)

                # Process running duration
                proc_uptime_sec = max(0, int(uptime - (starttime_ticks / CLK_TCK)))
                hours = proc_uptime_sec // 3600
                mins = (proc_uptime_sec % 3600) // 60
                duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

                # Classify process
                category = "normal"
                is_protected = comm in PROTECTED_COMM_NAMES or pid in (1, 2)
                is_kworker = comm.startswith("kworker") or comm.startswith("kswapd")

                if is_protected:
                    category = "system_protected"
                elif is_kworker:
                    category = "kernel_thread"
                elif "thumbnail" in cmdline or comm.startswith("kioworker"):
                    category = "stale_worker"
                elif "discord" in cmdline.lower() or "browseros" in cmdline.lower() or "firedragon" in cmdline.lower() or "chrome" in cmdline.lower() or "firefox" in cmdline.lower():
                    if "--type=renderer" in cmdline or "-contentproc" in cmdline:
                        category = "browser_tab_renderer"
                    else:
                        category = "heavy_app"
                elif "gradle" in cmdline.lower() or "steam" in cmdline.lower():
                    category = "heavy_app"

                processes.append({
                    "pid": pid,
                    "ppid": ppid,
                    "name": comm,
                    "cmdline": cmdline,
                    "user": user,
                    "uid": uid,
                    "state": state,
                    "nice": nice,
                    "cpu_pct": cpu_pct,
                    "rss_mb": rss_mb,
                    "mem_pct": mem_pct,
                    "duration": duration_str,
                    "duration_sec": proc_uptime_sec,
                    "category": category,
                    "is_protected": is_protected,
                })

            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
            except Exception:
                continue

        self._last_proc_times = new_proc_times
        return processes
