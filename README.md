# ⚡ Zero-Optimize — Garuda Linux RAM & CPU Booster

A lightweight, high-performance system optimizer and watchdog specifically engineered for **Garuda Linux** (KDE Plasma Wayland/X11, Arch Linux). 

Built to keep your system fast, responsive, and cool **even if you keep your PC running for weeks without restarting**.

---

## 🔍 Why RAM and CPU Peak on Long-Running Linux Systems

When Linux systems run for days or weeks without rebooting, several hidden bottlenecks accumulate:

1. **`kswapd0` CPU Thrashing**: As memory becomes fragmented over days of usage, the kernel's background page-reclaimer (`kswapd0`) begins burning high CPU trying to allocate contiguous memory blocks.
2. **PageCache Saturation**: File reads and writes slowly fill gigabytes of RAM with cached pages, buffers, and inodes (`buff/cache`).
3. **Heavy Background Electron & Browser Renderers**: Discord, Steam, and browser tabs (Chromium / Firefox / Firedragon) continue to consume CPU cycles and hold gigabytes of uncompacted RAM even while minimized.
4. **ZRAM & Swapfile Saturation**: Garuda sets `vm.swappiness=133` for ZRAM. When compressed RAM fills up, pages overflow into the disk swapfile (`/swap/swapfile2`), causing severe disk I/O latency and desktop micro-stuttering.
5. **Orphaned KDE Workers**: Preview thumbnailers (`kioworker thumbnail.so`) and stale background daemons linger in memory.

---

## 🚀 Key Features

- **⚡ 1-Click Smart Boost**:
  - Drops inactive pagecache, dentries, and directory inodes safely.
  - Compacts memory pages (`/proc/sys/vm/compact_memory`) to immediately eliminate `kswapd0` CPU thrashing.
  - Automatically renices background browser tabs, Discord renderers, and heavy apps to `nice 15` and `ionice idle` so games and foreground desktop remain butter-smooth.
  - Reclaims accumulated thumbnail cache in `~/.cache/thumbnails` and dead worker sockets.
  - Vacuums systemd user journal logs.
- **🛡️ Auto-Guard Daemon**:
  - Runs in the background (using < 0.1% CPU itself).
  - Automatically activates optimization whenever RAM exceeds threshold (e.g. 85%) or background tasks spike CPU.
  - Sends native Garuda desktop notifications via `notify-send`.
- **⏸️ Process Freeze & Thaw (Zero-CPU Tab/App Suspension)**:
  - Freeze heavy background apps or browser renderers (`SIGSTOP`) down to **0% CPU and 0% disk activity** without closing them.
  - Click **Resume** (`SIGCONT`) anytime to continue exactly where you left off.
- **📊 Real-time Dashboard**:
  - Live RAM breakdown (Used, Free, Available, PageCache, Dirty).
  - Live Swap & ZRAM compression ratio tracking.
  - Live normalized CPU load and process table with instant search and category filtering.
- **🎨 Modern Garuda Aesthetic & System Tray**:
  - Sleek Cyber/Neon dark theme matching Garuda Linux.
  - Minimizes to KDE Plasma system tray with live RAM/CPU tooltip.
- **💻 Dual Interface (GUI + CLI)**:
  - GUI: `zero-optimize` (searchable in Garuda Application Launcher).
  - CLI: `zero-optimize-cli` for terminal lovers, SSH sessions, or cron scripts.

---

## 📦 Installation & Quick Start

Zero-Optimize is already installed in your user environment:

### Launch the Desktop App (GUI)
- Open your **Garuda Application Launcher** (Application Menu) and search for **Zero-Optimize**.
- Or run in terminal:
  ```bash
  zero-optimize
  ```

### Use the Command-Line Interface (CLI)
```bash
# Check current system status & top resource hogs
zero-optimize-cli status

# Run 1-Click Smart Boost
zero-optimize-cli boost

# Run 1-Click Boost with root pagecache drop & memory compaction
zero-optimize-cli boost --root

# Clean user thumbnail cache and journals
zero-optimize-cli clean-cache

# Drop system pagecache and compact memory via Polkit
zero-optimize-cli drop-caches

# Suspend a runaway background process (reduces to 0% CPU)
zero-optimize-cli freeze <PID>

# Resume a suspended process
zero-optimize-cli thaw <PID>

# Run Auto-Guard watchdog in terminal
zero-optimize-cli guard
```

---

## 🛠️ Project Structure

```
zero-optimize/
├── bin/
│   ├── zero-optimize        # GUI executable wrapper
│   └── zero-optimize-cli    # CLI executable wrapper
├── zero_optimize/
│   ├── core/
│   │   ├── system_monitor.py # Ultra-fast /proc reader (RAM, CPU, Swap, ZRAM)
│   │   ├── cleaner.py        # Cache purger, kioworker cleaner, privileged drop
│   │   ├── optimizer.py      # Background renicer, freeze/thaw engine, smart boost
│   │   └── autoguard.py      # Background monitoring watchdog daemon
│   ├── gui/
│   │   ├── app.py            # Main PyQt6 application with System Tray
│   │   ├── widgets.py        # Stat cards, action buttons, process manager
│   │   └── styles.py         # Garuda dark neon cyber stylesheet
│   └── cli.py                # Command-line interface
├── helper/
│   └── zero-optimize-root-helper # Privileged helper for drop_caches & compaction
├── desktop/
│   └── zero-optimize.desktop     # KDE Plasma application entry
├── assets/
│   └── zero-optimize.svg         # High-resolution vector icon
└── install.sh                    # Setup and application registration script
```

---

## 🛡️ Safety & Reliability

- **System Protection**: Critical system processes (`plasmashell`, `kwin_wayland`, `pipewire`, `systemd`, `Xwayland`, etc.) are protected from accidental termination or freezing.
- **Filesystem Integrity**: All memory drops execute `sync` first to flush unwritten disk buffers safely.
- **Root Polkit Integration**: Uses `pkexec` for elevated operations, prompting native KDE graphical authentication without needing unsafe `sudo` aliases.
