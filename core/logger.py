"""
Append-only audit log at ~/.config/swyk/audit.log
Every action (approved or declined) is recorded as a JSON line.
"""

import json
import os
import time


class AuditLogger:
    def __init__(self, config_dir, enabled=True):
        self._enabled = enabled
        self._path = os.path.join(config_dir, "audit.log")
        if enabled:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def log(self, action, params, approved, result="", workspace=""):
        if not self._enabled:
            return
        entry = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "workspace": workspace,
            "action": action,
            "params": params,
            "approved": approved,
            "result": str(result)[:500],
        }
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass
