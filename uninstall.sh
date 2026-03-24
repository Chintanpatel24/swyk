#!/usr/bin/env bash
read -rp "Remove SWYK? [y/N] " a
[[ "$a" =~ ^[Yy]$ ]] || exit 0
rm -f "$HOME/.local/bin/swyk" 2>/dev/null
rm -rf "$HOME/.swyk" "$HOME/.config/swyk" 2>/dev/null
echo "SWYK removed."
