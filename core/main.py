#!/usr/bin/env python3
"""
SWYK — Secure Workspace You Know
Main entry point and REPL loop.
"""

import os
import sys
import signal
import json

# fix imports
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from core.config import Config
from core.sandbox import Sandbox, SandboxError
from core.permissions import PermissionGate
from core.logger import AuditLogger
from core.llm import LLMClient, LLMError
from core.agent import Agent
from core import ui

# enable arrow-key history in input()
try:
    import readline
except ImportError:
    pass


def _slash_command(cmd, agent, config, llm):
    """Handle /commands. Returns True if handled."""
    parts = cmd.strip().split(None, 1)
    verb = parts[0].lower()

    if verb in ("/exit", "/quit", "/q"):
        ui.info("Goodbye!")
        sys.exit(0)

    if verb == "/help":
        ui.help_msg()
        return True

    if verb == "/clear":
        agent.reset()
        ui.success("Conversation cleared.")
        return True

    if verb == "/config":
        ui.info("Configuration:")
        for key in ("model", "ollama_host", "max_file_size_mb",
                     "allow_shell_commands", "auto_approve_reads", "audit_log"):
            val = getattr(config, key, "?")
            print("  {}  {}".format(ui.c(key, ui.YELLOW), val))
        return True

    if verb == "/model":
        if len(parts) < 2:
            models = llm.list_models()
            ui.info("Current: {}".format(ui.c(llm.model, ui.BOLD)))
            if models:
                ui.info("Available: {}".format(", ".join(models)))
            else:
                ui.warn("Could not list models (is Ollama running?)")
        else:
            new = parts[1].strip()
            llm.set_model(new)
            config.model = new
            ui.success("Model set to {}".format(new))
        return True

    if verb == "/tree":
        try:
            files = agent.sandbox.walk(".", max_files=80)
            print(ui.c("  {}/".format(os.path.basename(agent.sandbox.root)), ui.BOLD, ui.BLUE))
            for f in files:
                print("  {}".format(f))
            if not files:
                print("  (empty)")
        except SandboxError as e:
            ui.error(str(e))
        return True

    return False


def main():
    config = Config.load()

    ui.banner()
    ui.info("Workspace: {}".format(ui.c(config.workspace, ui.BOLD, ui.BLUE)))
    ui.info("Model:     {}".format(ui.c(config.model, ui.BOLD)))
    print()

    # sandbox
    try:
        sandbox = Sandbox(config.workspace, max_file_size_mb=config.max_file_size_mb)
    except SandboxError as e:
        ui.error("Sandbox error: {}".format(e))
        sys.exit(1)

    ui.success("Sandbox locked to {}".format(sandbox.root))

    # logger
    logger = AuditLogger(config.config_dir, enabled=config.audit_log)

    # permission gate
    gate = PermissionGate(
        auto_reads=config.auto_approve_reads,
        allow_shell=config.allow_shell_commands,
        logger=logger,
        workspace=config.workspace,
    )

    # llm
    llm = LLMClient(host=config.ollama_host, model=config.model)
    if not llm.ping():
        ui.warn("Ollama not reachable at {}".format(config.ollama_host))
        ui.warn("Start it with:  ollama serve")
    else:
        ui.success("Connected to Ollama")

    # agent
    agent = Agent(llm=llm, sandbox=sandbox, gate=gate, config=config)

    # readline history
    hist_file = os.path.join(config.config_dir, "history")
    try:
        readline.read_history_file(hist_file)
    except Exception:
        pass
    try:
        readline.set_history_length(500)
    except Exception:
        pass

    def _save_hist():
        try:
            readline.write_history_file(hist_file)
        except Exception:
            pass

    # graceful ctrl-c
    def _sigint(sig, frame):
        print()
        ui.info("Interrupted. Type /exit to quit.")

    signal.signal(signal.SIGINT, _sigint)

    ui.info("Type {} for commands. Ask me anything about your files!\n".format(
        ui.c("/help", ui.YELLOW)))

    # --- REPL ---
    while True:
        try:
            prompt = "{} {} ".format(
                ui.c("swyk", ui.GREEN, ui.BOLD),
                ui.c(">", ui.CYAN),
            )
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            _save_hist()
            ui.info("Goodbye!")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if _slash_command(user_input, agent, config, llm):
                continue
            ui.warn("Unknown command: {}  (try /help)".format(user_input))
            continue

        try:
            response = agent.process(user_input)
            ui.agent_response(response)
        except KeyboardInterrupt:
            print()
            ui.warn("Generation interrupted.")
        except Exception as e:
            ui.error("Unexpected: {}".format(e))

        _save_hist()


if __name__ == "__main__":
    main()
