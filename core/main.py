#!/usr/bin/env python3
"""
SWIK — Secure Workspace Intelligence Kit
Main entry point.
"""

from __future__ import annotations

import os
import sys
import signal
import readline                       # enables ↑↓ history in input()

# make sure our package is importable
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from core.config import Config
from core.sandbox import Sandbox, SandboxError
from core.permissions import PermissionGate
from core.logger import AuditLogger
from core.llm_client import LLMClient, LLMError
from core.agent import Agent
from core import ui


def _handle_slash_command(cmd: str, agent: Agent, config: Config, llm: LLMClient) -> bool:
    """Handle /commands.  Returns True if handled."""
    parts = cmd.strip().split(maxsplit=1)
    verb = parts[0].lower()

    if verb in ("/exit", "/quit", "/q"):
        ui.info("Goodbye 👋")
        sys.exit(0)

    if verb == "/help":
        ui.help_msg()
        return True

    if verb == "/clear":
        agent.reset()
        ui.success("Conversation cleared.")
        return True

    if verb == "/config":
        import json
        ui.info("Current configuration:")
        for k in sorted(config.__dataclass_fields__):
            if k in ("swik_root", "workspace"):
                continue
            print(f"  {ui.c(k, ui.YELLOW)}: {getattr(config, k)}")
        return True

    if verb == "/model":
        if len(parts) < 2:
            models = llm.list_models()
            ui.info(f"Current model: {ui.c(llm.model, ui.BOLD)}")
            if models:
                ui.info("Available: " + ", ".join(models))
            else:
                ui.warn("Could not list models (is Ollama running?)")
        else:
            new_model = parts[1].strip()
            llm.set_model(new_model)
            config.model = new_model
            ui.success(f"Model changed to {new_model}")
        return True

    if verb == "/tree":
        try:
            files = agent.sandbox.walk(".", max_files=80)
            print(ui.format_file_tree(str(agent.sandbox.root), files))
        except SandboxError as exc:
            ui.error(str(exc))
        return True

    return False


def main() -> None:
    # ── config ────────────────────────────────────────────────
    config = Config.load()

    # ── banner ────────────────────────────────────────────────
    ui.banner()
    ui.info(f"Workspace : {ui.c(config.workspace, ui.BOLD, ui.BLUE)}")
    ui.info(f"Model     : {ui.c(config.model, ui.BOLD)}")
    print()

    # ── sandbox ───────────────────────────────────────────────
    try:
        sandbox = Sandbox(config.workspace, max_file_size_mb=config.max_file_size_mb)
    except SandboxError as exc:
        ui.error(f"Cannot create sandbox: {exc}")
        sys.exit(1)

    ui.success(f"Sandbox locked to {sandbox.root}")

    # ── audit logger ──────────────────────────────────────────
    logger = AuditLogger(config.swik_root, enabled=config.audit_log)

    # ── permission gate ───────────────────────────────────────
    gate = PermissionGate(
        auto_approve_reads=config.auto_approve_reads,
        allow_shell=config.allow_shell_commands,
        logger=logger,
        workspace=config.workspace,
    )

    # ── LLM client ────────────────────────────────────────────
    llm = LLMClient(host=config.ollama_host, model=config.model)

    if not llm.ping():
        ui.warn("Ollama is not reachable.  Start it with:  ollama serve")
        ui.warn(f"Trying {config.ollama_host} …")

    # ── agent ─────────────────────────────────────────────────
    agent = Agent(llm=llm, sandbox=sandbox, gate=gate, config=config)

    # ── REPL ──────────────────────────────────────────────────
    # readline history
    histfile = os.path.join(config.swik_root, ".swik_history")
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        pass
    readline.set_history_length(500)

    def _save_hist() -> None:
        try:
            readline.write_history_file(histfile)
        except OSError:
            pass

    # graceful Ctrl-C
    def _sigint(sig: int, frame: object) -> None:
        print()
        ui.info("Interrupted — type /exit to quit.")

    signal.signal(signal.SIGINT, _sigint)

    ui.info("Type /help for commands.  Ask me anything about this workspace!\n")

    while True:
        try:
            user_input = input(f"{ui.c('swik', ui.GREEN, ui.BOLD)} {ui.c('❯', ui.CYAN)} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            _save_hist()
            ui.info("Goodbye 👋")
            break

        if not user_input:
            continue

        # slash commands
        if user_input.startswith("/"):
            if _handle_slash_command(user_input, agent, config, llm):
                continue
            ui.warn(f"Unknown command: {user_input}  (try /help)")
            continue

        # agent conversation
        try:
            response = agent.process(user_input)
            print()
            print(ui.format_agent_response(response))
            print()
        except KeyboardInterrupt:
            print()
            ui.warn("Generation interrupted.")
        except Exception as exc:
            ui.error(f"Unexpected error: {exc}")

        _save_hist()


if __name__ == "__main__":
    main()
