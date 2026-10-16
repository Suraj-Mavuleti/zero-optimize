#!/usr/bin/env bash
# Zero-Optimize Installer for Garuda Linux / KDE Plasma
set -e

DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
echo "Installing Zero-Optimize from $DIR..."

# 1. Ensure directories exist
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps"

# 2. Symlink/copy executables into ~/.local/bin
ln -sf "$DIR/bin/zero-optimize" "$HOME/.local/bin/zero-optimize"
ln -sf "$DIR/bin/zero-optimize-cli" "$HOME/.local/bin/zero-optimize-cli"
chmod +x "$DIR/bin/zero-optimize" "$DIR/bin/zero-optimize-cli" "$DIR/helper/zero-optimize-root-helper"

# 3. Copy Icon
cp "$DIR/assets/zero-optimize.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/zero-optimize.svg"

# 4. Generate & Install Desktop Entry with absolute path
cat > "$HOME/.local/share/applications/zero-optimize.desktop" <<EOF
[Desktop Entry]
Name=Zero-Optimize
Comment=Garuda Linux RAM & CPU Booster
GenericName=System Optimizer
Exec=$HOME/.local/bin/zero-optimize
Icon=$HOME/.local/share/icons/hicolor/scalable/apps/zero-optimize.svg
Terminal=false
Type=Application
Categories=System;Monitor;Utility;
Keywords=ram;cpu;optimize;boost;clean;memory;garuda;task;
StartupNotify=true
EOF

chmod +x "$HOME/.local/share/applications/zero-optimize.desktop"

# 5. Install systemd user service
mkdir -p "$HOME/.config/systemd/user"
cp "$DIR/systemd/zero-optimize-guard.service" "$HOME/.config/systemd/user/zero-optimize-guard.service"
systemctl --user daemon-reload 2>/dev/null || true

# 6. Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
    kbuildsycoca5 >/dev/null 2>&1 || true
fi

echo "=========================================================="
echo "✨ Zero-Optimize successfully installed!"
echo "• Launch GUI from app menu or terminal: zero-optimize"
echo "• Launch CLI tool: zero-optimize-cli"
echo "• Enable background auto-guard on boot (optional):"
echo "  systemctl --user enable --now zero-optimize-guard"
echo "=========================================================="

