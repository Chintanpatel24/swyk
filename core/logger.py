"""
Immutable, append-only audit logger.

Every file-system mutation is logged with a timestamp, the action,
parameters, and whether the user approved it.  The log lives at
  ~/.swik/audit.log
and is human-readable (JSONL).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


class AuditLogger:
    def __init__(self, swik_root: str, enabled: bool = True):
        self._enabled = enabled
        self._path = Path(swik_root) / "audit.log"
        if enabled:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        action: str,
        params: dict,
        approved: bool,
        result: str = "",
        workspace: str = "",
    ) -> None:
        if not self._enabled:
            return
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "epoch": time.time(),
            "workspace": workspace,
            "action": action,
            "params": params,
            "approved": approved,
            "result": result[:500],         # cap result size
        }
        with open(self._path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
