#!/usr/bin/env bash
# Zero-Optimise Installer for Garuda Linux / KDE Plasma
set -e

DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
echo "Installing Zero-Optimise from $DIR..."

# 1. Ensure directories exist
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps"

# 2. Symlink/copy executables into ~/.local/bin
ln -sf "$DIR/bin/zero-optimise" "$HOME/.local/bin/zero-optimise"
ln -sf "$DIR/bin/zero-optimise-cli" "$HOME/.local/bin/zero-optimise-cli"
chmod +x "$DIR/bin/zero-optimise" "$DIR/bin/zero-optimise-cli" "$DIR/helper/zero-optimise-root-helper"

# 3. Copy Icon
cp "$DIR/assets/zero-optimise.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/zero-optimise.svg"

# 4. Generate & Install Desktop Entry with absolute path
cat > "$HOME/.local/share/applications/zero-optimise.desktop" <<EOF
[Desktop Entry]
Name=Zero-Optimise
Comment=Garuda Linux RAM & CPU Booster
GenericName=System Optimizer
Exec=$HOME/.local/bin/zero-optimise
Icon=$HOME/.local/share/icons/hicolor/scalable/apps/zero-optimise.svg
Terminal=false
Type=Application
Categories=System;Monitor;Utility;
Keywords=ram;cpu;optimize;boost;clean;memory;garuda;task;
StartupNotify=true
EOF

chmod +x "$HOME/.local/share/applications/zero-optimise.desktop"

# 5. Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
    kbuildsycoca5 >/dev/null 2>&1 || true
fi

echo "=========================================================="
echo "✨ Zero-Optimise successfully installed!"
echo "• Launch GUI from app menu or terminal: zero-optimise"
echo "• Launch CLI tool: zero-optimise-cli"
echo "=========================================================="
