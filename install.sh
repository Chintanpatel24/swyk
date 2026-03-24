#!/usr/bin/env bash
set -euo pipefail
SWYK_HOME="$HOME/.swyk"
REPO="https://github.com/AiCodingBattle/swyk"
R='\033[31m';G='\033[32m';Y='\033[33m';C='\033[36m';B='\033[1m';N='\033[0m'
info(){ printf "${C}[swyk]${N} %s\n" "$*"; }
ok(){ printf "${G}[  ok]${N} %s\n" "$*"; }
die(){ printf "${R}[fail]${N} %s\n" "$*"; exit 1; }

info "Installing SWYK ..."

# python check
PY=""
command -v python3 &>/dev/null && PY=python3 || { command -v python &>/dev/null && PY=python; }
[ -z "$PY" ] && die "Python 3.8+ required"
VER=$($PY -c 'import sys;v=sys.version_info;print(f"{v.major}.{v.minor}")')
MAJ=$($PY -c 'import sys;print(sys.version_info.major)')
MIN=$($PY -c 'import sys;print(sys.version_info.minor)')
[ "$MAJ" -lt 3 ] || { [ "$MAJ" -eq 3 ] && [ "$MIN" -lt 8 ]; } && die "Python 3.8+ needed (got $VER)"
ok "Python $VER"

# tkinter check
$PY -c "import tkinter" 2>/dev/null || {
    die "tkinter not found. Install: sudo apt install python3-tk (Debian/Ubuntu) or sudo dnf install python3-tkinter (Fedora)"
}
ok "tkinter available"

# git check
command -v git &>/dev/null || die "git required"
ok "git found"

# clone/update
if [ -d "$SWYK_HOME" ]; then
    info "Updating ..."
    cd "$SWYK_HOME" && git pull --ff-only 2>/dev/null || true
else
    git clone --depth 1 "$REPO" "$SWYK_HOME"
fi
ok "Source at $SWYK_HOME"

# link binary
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
chmod +x "$SWYK_HOME/bin/swyk"
ln -sf "$SWYK_HOME/bin/swyk" "$BIN_DIR/swyk"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *)
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        [ -f "$rc" ] && { echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$rc"; break; }
    done
    info "Added $BIN_DIR to PATH — restart shell or: export PATH=\"$BIN_DIR:\$PATH\""
;; esac
ok "Linked swyk"

# config dir
mkdir -p "$HOME/.config/swyk/conversations"
ok "Config dir ready"

echo ""
printf "${G}${B}  SWYK installed! Run: swyk${N}\n"
echo ""
