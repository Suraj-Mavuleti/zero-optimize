"""
Zero-Optimise Command Line Interface.
Provides terminal access to status, memory cleanup, CPU optimization, and background guard.
"""

import sys
import time
import argparse
from zero_optimise.core.system_monitor import SystemMonitor
from zero_optimise.core.optimizer import Optimizer
from zero_optimise.core.cleaner import Cleaner
from zero_optimise.core.autoguard import AutoGuard

# ANSI color codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    print(f"""{CYAN}{BOLD}
    ╔═══════════════════════════════════════════════════════════╗
    ║       ⚡ ZERO-OPTIMISE (Garuda RAM & CPU Booster) ⚡        ║
    ╚═══════════════════════════════════════════════════════════╝{RESET}""")


def cmd_status(monitor: SystemMonitor):
    print_banner()
    mem = monitor.get_memory_usage()
    cpu = monitor.get_cpu_usage()

    ram = mem.get("ram", {})
    swap = mem.get("swap", {})
    zram = mem.get("zram")

    print(f"{BOLD}📊 Memory & CPU Status:{RESET}")
    print(f"  RAM Usage:  {YELLOW if ram.get('percent', 0) > 80 else GREEN}{ram.get('percent')} %{RESET} ({ram.get('used_mb')} MB used / {ram.get('total_mb')} MB total, {ram.get('available_mb')} MB available)")
    print(f"  Page Cache: {ram.get('cache_mb')} MB (Buffers + Cached Inodes)")
    print(f"  Swap Usage: {RED if swap.get('percent', 0) > 50 else YELLOW}{swap.get('percent')} %{RESET} ({swap.get('used_mb')} MB used / {swap.get('total_mb')} MB total)")
    if zram:
        print(f"  ZRAM (zstd): {zram.get('data_size_mb')} MB uncompressed -> {zram.get('compr_size_mb')} MB in RAM ({zram.get('ratio')}x compression)")
    print(f"  CPU Total:  {RED if cpu.get('percent', 0) > 75 else GREEN}{cpu.get('percent')} %{RESET} (Load Avg: {cpu.get('load_1m')}, {cpu.get('load_5m')}, {cpu.get('load_15m')})")
    
    print(f"\n{BOLD}🔥 Top Memory Processes:{RESET}")
    procs = monitor.get_processes()
    top_mem = sorted(procs, key=lambda p: p["rss_mb"], reverse=True)[:5]
    print(f"  {'PID':<8} {'NAME':<18} {'MEM (MB)':<12} {'CPU %':<8} {'NICE':<6} {'CATEGORY'}")
    print("  " + "-" * 62)
    for p in top_mem:
        print(f"  {p['pid']:<8} {p['name'][:17]:<18} {p['rss_mb']:<12.1f} {p['cpu_pct']:<8.1f} {p['nice']:<6} {p['category']}")

    print(f"\n{BOLD}⚡ Top CPU Processes:{RESET}")
    top_cpu = sorted(procs, key=lambda p: p["cpu_pct"], reverse=True)[:5]
    print(f"  {'PID':<8} {'NAME':<18} {'CPU %':<8} {'MEM (MB)':<12} {'NICE':<6} {'CATEGORY'}")
    print("  " + "-" * 62)
    for p in top_cpu:
        print(f"  {p['pid']:<8} {p['name'][:17]:<18} {p['cpu_pct']:<8.1f} {p['rss_mb']:<12.1f} {p['nice']:<6} {p['category']}")
    print()


def cmd_boost(optimizer: Optimizer, root_cache_drop: bool = False):
    print_banner()
    print(f"{YELLOW}▶ Initiating Smart System Optimization...{RESET}\n")

    res = optimizer.run_smart_boost(allow_root_drop=root_cache_drop)

    thumbs = res.get("thumbnails", {})
    workers = res.get("workers", {})
    cpu_res = res.get("cpu_tuning", {})
    cache_res = res.get("cache_drop", {})

    print(f"  [✓] Thumbnail Cache: {GREEN}{thumbs.get('status')}{RESET}")
    print(f"  [✓] KDE kioworkers:  {GREEN}{workers.get('status')}{RESET}")
    print(f"  [✓] CPU Scheduler:   {GREEN}{cpu_res.get('status')}{RESET}")
    if root_cache_drop:
        print(f"  [✓] System Caches:   {GREEN if cache_res.get('success') else RED}{cache_res.get('message')}{RESET}")
    else:
        print(f"  [-] System Caches:   {YELLOW}Skipped (run with --root to purge kernel pagecache & compact){RESET}")

    print(f"\n{GREEN}{BOLD}✨ Optimization Completed Successfully!{RESET}\n")


def cmd_guard(optimizer: Optimizer):
    print_banner()
    print(f"{CYAN}🛡️  Starting Zero-Optimise AutoGuard daemon (Press Ctrl+C to stop)...{RESET}")
    guard = AutoGuard(optimizer, ram_threshold=82.0, cpu_threshold=70.0, interval_seconds=3.0)

    def on_event(ev):
        ev_type = ev.get("type")
        if ev_type == "ram_autoboost":
            print(f"[{time.strftime('%X')}] {YELLOW}⚠️  RAM limit reached ({ev['ram_pct']}%). Triggered auto-boost!{RESET}")
        elif ev_type == "cpu_autotune":
            print(f"[{time.strftime('%X')}] {CYAN}⚡ High CPU ({ev['cpu_pct']}%). Reniced {ev['count']} background hogs.{RESET}")

    guard.set_callback(on_event)
    guard.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Stopping AutoGuard daemon...{RESET}")
        guard.stop()
        print(f"{GREEN}Stopped.{RESET}")


def main():
    parser = argparse.ArgumentParser(description="Zero-Optimise: Linux RAM & CPU Optimizer for Garuda Linux")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    subparsers.add_parser("status", help="Show current RAM, Swap, CPU and top processes")

    boost_parser = subparsers.add_parser("boost", help="Run 1-click system optimization")
    boost_parser.add_argument("--root", action="store_true", help="Authorize root-level pagecache drop and memory compaction via pkexec")

    subparsers.add_parser("guard", help="Run background watchdog monitoring RAM and CPU")

    clean_parser = subparsers.add_parser("clean-cache", help="Clean user thumbnail cache and journals")

    drop_parser = subparsers.add_parser("drop-caches", help="Drop kernel pagecache and compact memory via pkexec")

    freeze_parser = subparsers.add_parser("freeze", help="Suspend a runaway process (SIGSTOP)")
    freeze_parser.add_argument("pid", type=int, help="Process ID to freeze")

    thaw_parser = subparsers.add_parser("thaw", help="Resume a suspended process (SIGCONT)")
    thaw_parser.add_argument("pid", type=int, help="Process ID to thaw")

    args = parser.parse_args()

    monitor = SystemMonitor()
    cleaner = Cleaner()
    optimizer = Optimizer(monitor=monitor, cleaner=cleaner)

    if args.command == "status" or not args.command:
        cmd_status(monitor)
    elif args.command == "boost":
        cmd_boost(optimizer, root_cache_drop=args.root)
    elif args.command == "guard":
        cmd_guard(optimizer)
    elif args.command == "clean-cache":
        res1 = cleaner.clean_thumbnail_cache()
        res2 = cleaner.vacuum_user_journal()
        print(f"{GREEN}{res1['status']}{RESET}")
    elif args.command == "drop-caches":
        success, msg = cleaner.drop_caches_privileged(use_gui_auth=True)
        print(f"{GREEN if success else RED}{msg}{RESET}")
        if success:
            c_succ, c_msg = cleaner.compact_memory_privileged(use_gui_auth=False)
            print(f"{GREEN if c_succ else RED}{c_msg}{RESET}")
    elif args.command == "freeze":
        ok, msg = optimizer.freeze_process(args.pid)
        print(f"{GREEN if ok else RED}{msg}{RESET}")
    elif args.command == "thaw":
        ok, msg = optimizer.thaw_process(args.pid)
        print(f"{GREEN if ok else RED}{msg}{RESET}")


if __name__ == "__main__":
    main()
