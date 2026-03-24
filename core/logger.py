"""Append-only audit log."""
import json, os, time

class Logger:
    def __init__(self, enabled=True):
        self._on = enabled
        self._path = os.path.join(os.path.expanduser("~"), ".config", "swyk", "audit.log")
    def log(self, action, params, approved, result=""):
        if not self._on: return
        try:
            with open(self._path, "a") as f:
                f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "action": action, "params": params, "ok": approved,
                    "result": str(result)[:300]}) + "\n")
        except: pass
