#!/usr/bin/env bash
set -euo pipefail

echo "This will remove SWYK from your system."
read -rp "Continue? [y/N] " ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

rm -f "$HOME/.local/bin/swyk" "$HOME/bin/swyk" 2>/dev/null || true
rm -rf "$HOME/.swyk" 2>/dev/null || true
rm -rf "$HOME/.config/swyk" 2>/dev/null || true
echo "SWYK removed."
