#!/usr/bin/env bash
set -euo pipefail

SWYK_HOME="${SWYK_HOME:-$HOME/.swyk}"
SWYK_REPO="https://github.com/AiCodingBattle/swyk"
SWYK_BRANCH="main"
BIN_DIR=""
MIN_PYTHON="3.8"

R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'
C='\033[0;36m'; B='\033[1m'; N='\033[0m'

info()  { printf "${C}[swyk]${N} %s\n" "$*"; }
ok()    { printf "${G}[  ok]${N} %s\n" "$*"; }
warn()  { printf "${Y}[warn]${N} %s\n" "$*"; }
die()   { printf "${R}[fail]${N} %s\n" "$*"; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

detect_bin_dir() {
    if [ -d "$HOME/.local/bin" ]; then
        BIN_DIR="$HOME/.local/bin"
    elif [ -d "$HOME/bin" ]; then
        BIN_DIR="$HOME/bin"
    else
        mkdir -p "$HOME/.local/bin"
        BIN_DIR="$HOME/.local/bin"
    fi
}

ensure_path() {
    case ":$PATH:" in
        *":$BIN_DIR:"*) return ;;
    esac
    local rc=""
    if   [ -f "$HOME/.bashrc" ];  then rc="$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ];   then rc="$HOME/.zshrc"
    elif [ -f "$HOME/.profile" ]; then rc="$HOME/.profile"
    fi
    if [ -n "$rc" ]; then
        printf '\nexport PATH="%s:$PATH"\n' "$BIN_DIR" >> "$rc"
        info "Added $BIN_DIR to PATH in $rc"
        info "Run: source $rc   or restart your terminal"
    fi
}

info "Starting SWYK installation ..."

# --- python check ---
PY=""
if command_exists python3; then PY=python3
elif command_exists python; then PY=python
else die "Python 3.8+ is required. Install it first."; fi

PY_VER=$($PY -c 'import sys; print("{}.{}".format(sys.version_info.major, sys.version_info.minor))')
PY_MAJOR=$($PY -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$($PY -c 'import sys; print(sys.version_info.minor)')

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    die "Python 3.8+ required (found $PY_VER)"
fi
ok "Python $PY_VER"

# --- git check ---
command_exists git || die "git is required. Install it first."
ok "git found"

# --- ollama check/install ---
if command_exists ollama; then
    ok "Ollama already installed"
else
    info "Installing Ollama (local AI runtime) ..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        warn "On macOS install Ollama from https://ollama.com/download then re-run."
        exit 1
    else
        die "Auto-install not supported on this OS. See https://ollama.com"
    fi
    ok "Ollama installed"
fi

# --- pull model ---
info "Pulling default model (mistral) — may take a few minutes on first run ..."
ollama pull mistral 2>/dev/null || warn "Could not pull model now. Run: ollama pull mistral"
ok "Model ready"

# --- clone/update ---
if [ -d "$SWYK_HOME" ]; then
    info "Updating existing installation ..."
    cd "$SWYK_HOME"
    git pull --ff-only origin "$SWYK_BRANCH" 2>/dev/null || true
else
    info "Cloning SWYK ..."
    git clone --depth 1 --branch "$SWYK_BRANCH" "$SWYK_REPO" "$SWYK_HOME"
fi
ok "Source at $SWYK_HOME"

# --- link binary ---
detect_bin_dir
chmod +x "$SWYK_HOME/bin/swyk"
ln -sf "$SWYK_HOME/bin/swyk" "$BIN_DIR/swyk"
ensure_path
ok "Linked swyk -> $BIN_DIR/swyk"

# --- default config ---
CONF_DIR="$HOME/.config/swyk"
CONF="$CONF_DIR/config.json"
if [ ! -f "$CONF" ]; then
    mkdir -p "$CONF_DIR"
    cat > "$CONF" <<'ENDJSON'
{
    "model": "mistral",
    "ollama_host": "http://127.0.0.1:11434",
    "max_file_size_mb": 10,
    "allow_shell_commands": false,
    "auto_approve_reads": true,
    "audit_log": true
}
ENDJSON
    ok "Config at $CONF"
fi

echo ""
printf "${G}${B}  ========================================${N}\n"
printf "${G}${B}     SWYK installed successfully!         ${N}\n"
printf "${G}${B}  ========================================${N}\n"
echo ""
info "Usage:  cd /your/project && swyk"
info "Config: $CONF"
echo ""
