"""
Configuration loader.
Reads $SWIK_ROOT/config.json and merges with per-workspace .swik.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass, field

DEFAULTS = {
    "model": "mistral",
    "ollama_host": "http://127.0.0.1:11434",
    "max_file_size_mb": 10,
    "allow_shell_commands": False,
    "auto_approve_reads": True,
    "audit_log": True,
    "theme": "dark",
    "max_context_files": 20,
    "history_length": 50,
}


@dataclass
class Config:
    model: str = "mistral"
    ollama_host: str = "http://127.0.0.1:11434"
    max_file_size_mb: int = 10
    allow_shell_commands: bool = False
    auto_approve_reads: bool = True
    audit_log: bool = True
    theme: str = "dark"
    max_context_files: int = 20
    history_length: int = 50

    # runtime (not serialised)
    swik_root: str = ""
    workspace: str = ""

    @classmethod
    def load(cls) -> "Config":
        swik_root = os.environ.get("SWIK_ROOT", str(Path.home() / ".swik"))
        workspace = os.environ.get("SWIK_WORKSPACE", os.getcwd())

        data = dict(DEFAULTS)

        # global config
        global_cfg = Path(swik_root) / "config.json"
        if global_cfg.is_file():
            with open(global_cfg) as f:
                data.update(json.load(f))

        # per-workspace override
        local_cfg = Path(workspace) / ".swik.json"
        if local_cfg.is_file():
            with open(local_cfg) as f:
                data.update(json.load(f))

        cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        cfg.swik_root = swik_root
        cfg.workspace = workspace
        return cfg

    def save_global(self) -> None:
        path = Path(self.swik_root) / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            k: getattr(self, k)
            for k in self.__dataclass_fields__
            if k not in ("swik_root", "workspace")
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
