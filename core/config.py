"""
Configuration loader.
Reads ~/.config/swyk/config.json and optional .swyk.json in workspace.
Pure stdlib — no dependencies.
"""

import json
import os


DEFAULTS = {
    "model": "mistral",
    "ollama_host": "http://127.0.0.1:11434",
    "max_file_size_mb": 10,
    "allow_shell_commands": False,
    "auto_approve_reads": True,
    "audit_log": True,
    "history_length": 40,
}


class Config:
    def __init__(self):
        self.model = DEFAULTS["model"]
        self.ollama_host = DEFAULTS["ollama_host"]
        self.max_file_size_mb = DEFAULTS["max_file_size_mb"]
        self.allow_shell_commands = DEFAULTS["allow_shell_commands"]
        self.auto_approve_reads = DEFAULTS["auto_approve_reads"]
        self.audit_log = DEFAULTS["audit_log"]
        self.history_length = DEFAULTS["history_length"]
        self.swyk_root = os.environ.get("SWYK_ROOT", os.path.join(os.path.expanduser("~"), ".swyk"))
        self.workspace = os.environ.get("SWYK_WORKSPACE", os.getcwd())
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "swyk")

    @classmethod
    def load(cls):
        c = cls()
        # global config
        gpath = os.path.join(c.config_dir, "config.json")
        if os.path.isfile(gpath):
            try:
                with open(gpath, "r") as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(c, k):
                        setattr(c, k, v)
            except Exception:
                pass
        # workspace override
        lpath = os.path.join(c.workspace, ".swyk.json")
        if os.path.isfile(lpath):
            try:
                with open(lpath, "r") as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(c, k):
                        setattr(c, k, v)
            except Exception:
                pass
        return c
