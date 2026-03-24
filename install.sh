#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  SWIK installer — run with:
#    curl -fsSL https://raw.githubusercontent.com/swik-ai/swik/main/install.sh | bash
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SWIK_HOME="${SWIK_HOME:-$HOME/.swik}"
SWIK_REPO="https://github.com/swik-ai/swik"          # change to your repo
SWIK_BRANCH="main"
BIN_DIR=""
MIN_PYTHON="3.8"

# ── colours ───────────────────────────────────────────────────
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'
C='\033[0;36m'; B='\033[1m'; N='\033[0m'

info()  { printf "${C}[swik]${N} %s\n" "$*"; }
ok()    { printf "${G}[  ✓ ]${N} %s\n" "$*"; }
warn()  { printf "${Y}[warn]${N} %s\n" "$*"; }
die()   { printf "${R}[fail]${N} %s\n" "$*"; exit 1; }

# ── helpers ───────────────────────────────────────────────────
version_gte() {                     # $1 >= $2  (dotted)
    printf '%s\n%s' "$1" "$2" | sort -V -C
}

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
        *":$BIN_DIR:"*) ;;
        *)
            local shell_rc=""
            if   [ -f "$HOME/.bashrc" ];    then shell_rc="$HOME/.bashrc"
            elif [ -f "$HOME/.zshrc" ];     then shell_rc="$HOME/.zshrc"
            elif [ -f "$HOME/.profile" ];   then shell_rc="$HOME/.profile"
            fi
            if [ -n "$shell_rc" ]; then
                echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$shell_rc"
                info "Added $BIN_DIR to PATH in $shell_rc — restart your shell or run:"
                info "  export PATH=\"$BIN_DIR:\$PATH\""
            fi
            ;;
    esac
}

# ── pre-flight checks ────────────────────────────────────────
info "Starting SWIK installation …"

# Python 3
if command_exists python3; then
    PY="python3"
elif command_exists python; then
    PY="python"
else
    die "Python 3.8+ is required.  Install it first."
fi

PY_VER=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if ! version_gte "$PY_VER" "$MIN_PYTHON"; then
    die "Python $MIN_PYTHON+ required (found $PY_VER)"
fi
ok "Python $PY_VER"

# git (for cloning)
if ! command_exists git; then
    die "git is required.  Install it first."
fi
ok "git found"

# ── install / check Ollama ────────────────────────────────────
if command_exists ollama; then
    ok "Ollama already installed"
else
    info "Installing Ollama (local LLM runtime) …"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        warn "On macOS, install Ollama from https://ollama.com/download"
        warn "Then re-run this script."
        exit 1
    else
        die "Unsupported OS for automatic Ollama install. See https://ollama.com"
    fi
    ok "Ollama installed"
fi

# ── pull default model ────────────────────────────────────────
info "Pulling default model (mistral) — this may take a few minutes …"
ollama pull mistral 2>/dev/null || warn "Could not pull mistral now; run 'ollama pull mistral' later."
ok "Model ready"

# ── clone / update SWIK ──────────────────────────────────────
if [ -d "$SWIK_HOME" ]; then
    info "Updating existing installation …"
    cd "$SWIK_HOME"
    git pull --ff-only origin "$SWIK_BRANCH" 2>/dev/null || true
else
    info "Cloning SWIK …"
    git clone --depth 1 --branch "$SWIK_BRANCH" "$SWIK_REPO" "$SWIK_HOME"
fi
ok "SWIK source at $SWIK_HOME"

# ── create launcher symlink ───────────────────────────────────
detect_bin_dir
chmod +x "$SWIK_HOME/bin/swik"
ln -sf "$SWIK_HOME/bin/swik" "$BIN_DIR/swik"
ensure_path
ok "Linked  swik → $BIN_DIR/swik"

# ── optional: build Rust sandbox-executor ─────────────────────
if command_exists cargo; then
    info "Rust found — building hardened sandbox-executor …"
    (cd "$SWIK_HOME/sandbox-executor" && cargo build --release 2>/dev/null) && \
        ok "sandbox-executor built" || \
        warn "Rust build failed — falling back to Python sandbox (still safe)"
else
    info "Rust not found — using Python-only sandbox (still safe)"
fi

# ── create default config ─────────────────────────────────────
CONF="$SWIK_HOME/config.json"
if [ ! -f "$CONF" ]; then
    cat > "$CONF" <<'EOF'
{
    "model": "mistral",
    "ollama_host": "http://127.0.0.1:11434",
    "max_file_size_mb": 10,
    "allow_shell_commands": false,
    "auto_approve_reads": true,
    "audit_log": true,
    "theme": "dark"
}
EOF
    ok "Default config written to $CONF"
fi

# ── done ──────────────────────────────────────────────────────
echo ""
printf "${G}${B}  ╔══════════════════════════════════════╗${N}\n"
printf "${G}${B}  ║   SWIK installed successfully! 🚀    ║${N}\n"
printf "${G}${B}  ╚══════════════════════════════════════╝${N}\n"
echo ""
info "Usage:  cd /some/project && swik"
info "Config: $CONF"
echo ""
