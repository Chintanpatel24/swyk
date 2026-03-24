"""
Ollama chat client — pure stdlib (urllib only).
No requests, no httpx, no pip packages.
"""

import json
import urllib.request
import urllib.error


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, host="http://127.0.0.1:11434", model="mistral"):
        self.host = host.rstrip("/")
        self.model = model

    def ping(self):
        try:
            req = urllib.request.Request(self.host + "/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def chat(self, messages, temperature=0.3):
        """Send messages, get full response (non-streaming)."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.host + "/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "")
        except urllib.error.URLError as e:
            raise LLMError("Cannot reach Ollama at {}: {}".format(self.host, e))
        except (json.JSONDecodeError, KeyError) as e:
            raise LLMError("Bad response from Ollama: {}".format(e))

    def list_models(self):
        try:
            req = urllib.request.Request(self.host + "/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def set_model(self, name):
        self.model = name
