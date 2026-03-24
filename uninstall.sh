#!/usr/bin/env bash
set -euo pipefail

SWIK_HOME="${SWIK_HOME:-$HOME/.swik}"

echo "This will remove SWIK from your system."
read -rp "Continue? [y/N] " ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

rm -f "$HOME/.local/bin/swik" "$HOME/bin/swik" "/usr/local/bin/swik" 2>/dev/null || true
rm -rf "$SWIK_HOME"
echo "SWIK removed."
