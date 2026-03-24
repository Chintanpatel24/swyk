<div align="center">

# 🛡️ SWYK

### **S**ecure **W**orkspace **Y**ou **K**now

A sandboxed, open-source AI agent that lives in your terminal.  
Zero pip dependencies. Pure Python. Fully local. Privacy-first.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-orange.svg)](https://ollama.com)
[![No Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen.svg)](#zero-dependencies)

</div>

---

## What is SWYK?

SWYK is a CLI AI assistant that:

- 📂 **Lives where you work** — run `swyk` in any directory and it becomes your workspace-aware copilot
- 🔒 **Sandboxed** — can only access files inside the directory where you launched it
- ✋ **Permission-gated** — every write, move, and delete requires your explicit `y` approval
- 🏠 **Fully local** — powered by [Ollama](https://ollama.com), your data never leaves your machine
- 📦 **Zero pip dependencies** — pure Python stdlib, nothing to install via pip
- 📝 **Audit logged** — every action (approved or declined) is recorded

```
cd ~/my-project
swyk

swyk > what files are in this project?
swyk > read the README.md
swyk > create a .gitignore for Python projects
swyk > move old_config.yaml to backup/
swyk > find all TODO comments in the codebase
```

---

## ⚡ Install (One Command)

```bash
curl -fsSL https://raw.githubusercontent.com/Chintanpatel24/swyk/main/install.sh | bash
```

That's it. The installer will:

1. ✅ Check Python 3.8+ is installed
2. ✅ Check git is installed
3. ✅ Install [Ollama](https://ollama.com) if missing (Linux)
4. ✅ Pull the default `mistral` model
5. ✅ Clone SWYK to `~/.swyk`
6. ✅ Link `swyk` into your `PATH`
7. ✅ Create default config at `~/.config/swyk/config.json`

### Requirements

| Requirement | Why |
|---|---|
| **Python 3.8+** | Runtime (uses only stdlib) |
| **git** | For cloning/updating |
| **Ollama** | Local LLM server (auto-installed on Linux) |
| **~4 GB disk** | For the Mistral model |

### Manual Install (if you prefer)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull mistral

# 3. Clone SWYK
git clone https://github.com/AiCodingBattle/swyk.git ~/.swyk

# 4. Link it
chmod +x ~/.swyk/bin/swyk
ln -sf ~/.swyk/bin/swyk ~/.local/bin/swyk

# 5. Make sure ~/.local/bin is in your PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## 🚀 Usage

### Start SWYK

```bash
cd /path/to/your/project
swyk
```

SWYK launches locked to that directory. It can see and work with files only inside that folder.

### Talk Naturally

```
swyk > show me all Python files
swyk > what does main.py do?
swyk > create a new file called utils.py with a helper function
swyk > move config.json to settings/config.json
swyk > delete the old logs directory
swyk > search for "database" in all files
```

### Permission Flow

When SWYK wants to modify something, it asks first:

```
  +--- Permission Required ------------------
  |  MOVE config.json -> backup/config.json
  +-----------------------------------------
  Approve? [y/n]: y
  [ ok ]  Approved
  +  Moved config.json -> backup/config.json
```

Type `n` to decline — SWYK skips the action and waits for your next instruction.

### Slash Commands

| Command | What it does |
|---|---|
| `/help` | Show available commands |
| `/tree` | Print workspace file tree |
| `/model mistral` | Switch LLM model |
| `/model` | Show current model + available models |
| `/config` | Show current configuration |
| `/clear` | Clear conversation history |
| `/exit` | Quit (Ctrl+C also works) |

---

## 🔐 Security Model

SWYK is designed with security as a core principle:

### 1. Path Jail (Sandbox)

Every file path goes through `os.path.realpath()` + boundary check before any I/O:

```
User asks: "read ../../etc/passwd"
Sandbox:   BLOCKED — path escapes workspace
```

- ✅ `..` traversal blocked
- ✅ Symlink escapes blocked (resolved to real path first)
- ✅ Absolute paths outside workspace blocked

### 2. Tiered Permissions

| Tier | Actions | Approval |
|---|---|---|
| **0 — READ** | list, read, search, info | Auto-approved |
| **1 — WRITE** | create file, write, mkdir | Requires `y` |
| **2 — MOVE** | move, copy, rename | Requires `y` |
| **3 — DELETE** | delete file/directory | Requires `y` |
| **4 — EXECUTE** | shell commands | Requires `y` + config flag |

### 3. Sensitive File Guard

These files are **read-only** by default (writes blocked):

```
.env  .env.local  .env.production  .env.staging
.npmrc  .pypirc  id_rsa  id_ed25519
```

### 4. Shell Command Lock

Shell commands (`run_command`) are **disabled by default**. Enable them explicitly:

```json
{
    "allow_shell_commands": true
}
```

Even when enabled, every command still requires `y/n` approval.

### 5. Audit Log

Every action is logged to `~/.config/swyk/audit.log` as JSONL:

```json
{"time":"2025-01-15T10:30:45","workspace":"/home/user/project","action":"move_file","params":{"source":"a.txt","destination":"b.txt"},"approved":true,"result":""}
{"time":"2025-01-15T10:31:02","workspace":"/home/user/project","action":"delete_file","params":{"path":"temp/"},"approved":false,"result":""}
```

### 6. Fully Local

```
┌─────────────────────────────────────────────────┐
│                 YOUR MACHINE                     │
│                                                  │
│   Terminal                                       │
│   ┌──────┐     HTTP (localhost)   ┌──────────┐  │
│   │ SWYK │ ◄──────────────────► │  Ollama   │  │
│   │      │                       │ (Mistral) │  │
│   └──┬───┘                       └──────────┘  │
│      │                                           │
│      ▼                                           │
│   ┌──────────┐    ┌─────────────┐               │
│   │ Sandbox  │───►│ Audit Log   │               │
│   │ (jail)   │    │ (append)    │               │
│   └──┬───────┘    └─────────────┘               │
│      │                                           │
│      ▼                                           │
│   ┌────────────┐                                │
│   │ Your Files │  ← workspace dir only          │
│   └────────────┘                                │
│                                                  │
│   Nothing leaves this box.                       │
└─────────────────────────────────────────────────┘
```

- No API keys needed
- No cloud services
- No telemetry
- No network calls except `localhost:11434` (Ollama)

---

## ⚙️ Configuration

### Global Config

Location: `~/.config/swyk/config.json`

```json
{
    "model": "mistral",
    "ollama_host": "http://127.0.0.1:11434",
    "max_file_size_mb": 10,
    "allow_shell_commands": false,
    "auto_approve_reads": true,
    "audit_log": true
}
```

| Key | Default | Description |
|---|---|---|
| `model` | `"mistral"` | Ollama model name |
| `ollama_host` | `"http://127.0.0.1:11434"` | Ollama server URL |
| `max_file_size_mb` | `10` | Refuse to read files larger than this |
| `allow_shell_commands` | `false` | Whether `run_command` tool is available |
| `auto_approve_reads` | `true` | Skip y/n for read-only operations |
| `audit_log` | `true` | Enable/disable audit logging |

### Per-Workspace Config

Drop a `.swyk.json` in any project to override global settings:

```json
{
    "model": "codellama",
    "allow_shell_commands": true
}
```

### Switch Models

```bash
# Pull a different model
ollama pull llama3
ollama pull codellama
ollama pull deepseek-coder

# Switch in SWYK
swyk > /model llama3
```

---

## 🛠 Available Tools

SWYK has 13 built-in tools:

| Tool | Tier | Description |
|---|---|---|
| `list_files` | READ | List directory contents |
| `read_file` | READ | Read file contents |
| `search_files` | READ | Glob search (`*.py`, `src/**/*.js`) |
| `search_content` | READ | Grep-like text search across files |
| `file_info` | READ | Size, permissions, modified date |
| `workspace_tree` | READ | Full file tree |
| `write_file` | WRITE | Create / overwrite file |
| `append_file` | WRITE | Append to file |
| `create_directory` | WRITE | mkdir -p |
| `move_file` | MOVE | Move / rename |
| `copy_file` | MOVE | Copy file or directory |
| `delete_file` | DELETE | Remove file / directory |
| `run_command` | EXECUTE | Shell command (disabled by default) |

---

## 📝 Example Session

```
  +=========================================+
  |  SWYK — Secure Workspace You Know       |
  +=========================================+

[swyk]  Workspace: /home/user/my-project
[swyk]  Model:     mistral
[ ok ]  Sandbox locked to /home/user/my-project
[ ok ]  Connected to Ollama
[swyk]  Type /help for commands. Ask me anything about your files!

swyk > what files are here?

  >  The user wants to see the workspace contents. I'll use workspace_tree.
[swyk]  Tool: workspace_tree({})
  +  README.md
     src/main.py
     src/utils.py
     config.json
     tests/test_main.py

  +--- swyk ---------------------------------
  |  Your workspace has 5 files:
  |  - README.md
  |  - src/main.py and src/utils.py
  |  - config.json
  |  - tests/test_main.py
  +-----------------------------------------

swyk > move config.json to settings/config.json

  >  The user wants to move config.json. I need to create the
     settings directory first, then move the file.
[swyk]  Tool: create_directory({"path": "settings"})

  +--- Permission Required ------------------
  |  MKDIR settings
  +-----------------------------------------
  Approve? [y/n]: y
  [ ok ]  Approved
  +  Created directory settings

[swyk]  Tool: move_file({"source": "config.json", "destination": "settings/config.json"})

  +--- Permission Required ------------------
  |  MOVE config.json -> settings/config.json
  +-----------------------------------------
  Approve? [y/n]: y
  [ ok ]  Approved
  +  Moved config.json -> settings/config.json

  +--- swyk ---------------------------------
  |  Done! Moved config.json to settings/config.json.
  +-----------------------------------------

swyk > /exit
[swyk]  Goodbye!
```

---

## 🏗 Project Structure

```
swyk/
├── install.sh           # One-line curl installer
├── uninstall.sh         # Clean removal
├── LICENSE              # MIT
├── README.md            # This file
├── bin/
│   └── swyk             # Launcher script (bash)
└── core/
    ├── __init__.py      # Package marker + version
    ├── main.py          # Entry point + REPL loop
    ├── agent.py         # LLM reasoning loop
    ├── llm.py           # Ollama HTTP client (urllib only)
    ├── tools.py         # 13 file-system tools
    ├── sandbox.py       # Path jail + symlink guard
    ├── permissions.py   # Tiered y/n permission gate
    ├── config.py        # Config loader
    ├── ui.py            # Terminal colours + spinners
    └── logger.py        # Append-only audit log
```

---

## 🔌 Zero Dependencies

SWYK uses **only Python standard library modules**:

```
os, sys, json, time, shutil, stat, fnmatch, signal,
threading, itertools, textwrap, re, subprocess,
urllib.request, urllib.error, readline
```

**No pip. No virtualenv. No requirements.txt.** If you have Python 3.8+, it works.

---

## 🗑 Uninstall

```bash
~/.swyk/uninstall.sh
```

Or manually:

```bash
rm -f ~/.local/bin/swyk
rm -rf ~/.swyk
rm -rf ~/.config/swyk
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-idea`
3. Make your changes
4. Test locally: `cd /tmp/test-dir && ~/.swyk/bin/swyk`
5. Submit a PR

### Dev Tips

- All code is in `core/` — pure Python, no build step
- To test without installing: `SWYK_ROOT=/path/to/swyk SWYK_WORKSPACE=/tmp/test python3 core/main.py`
- The audit log at `~/.config/swyk/audit.log` is useful for debugging

---

## 🗺️ Roadmap

- [ ] Streaming responses (token-by-token output)
- [ ] Multi-file edit mode
- [ ] Git integration (status, diff, commit)
- [ ] Plugin system for custom tools
- [ ] RAG over large codebases
- [ ] Windows support (PowerShell launcher)
- [ ] Optional Rust sandbox executor
- [ ] Web UI mode

---

## ❓ FAQ

**Q: Which models work?**  
Any model available through Ollama: `mistral`, `llama3`, `codellama`, `deepseek-coder`, `gemma2`, `phi3`, etc.

**Q: Can SWYK access files outside my project?**  
No. The sandbox resolves every path through `os.path.realpath()` and checks it's inside the workspace root. Symlink escapes and `..` traversal are blocked.

**Q: Can SWYK run arbitrary commands?**  
Only if `allow_shell_commands` is `true` in config, AND you approve each command with `y`. By default, shell commands are completely disabled.

**Q: Does SWYK phone home?**  
No. The only network call is to your local Ollama instance at `localhost:11434`. No telemetry, no analytics, no cloud.

**Q: What about Windows?**  
Currently Linux and macOS. Windows support (via a `.ps1` launcher) is planned.

**Q: What if Ollama isn't running?**  
SWYK will warn you and still launch. Start Ollama with `ollama serve` in another terminal.

---

## 📄 License

[MIT](LICENSE) — use it, fork it, improve it.

---

<div align="center">

**Built with ❤️ and zero dependencies**

[Report Bug](https://github.com/AiCodingBattle/swyk/issues) · [Request Feature](https://github.com/AiCodingBattle/swyk/issues)

</div>
