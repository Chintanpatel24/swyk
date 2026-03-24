"""
Minimal Ollama / OpenAI-compatible chat client.

Uses only urllib (stdlib) — no requests, no httpx.
Supports streaming for responsive output.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Generator, List, Dict, Optional


class LLMError(Exception):
    """Raised on LLM communication failures."""


class LLMClient:
    """Talk to an Ollama instance (or any OpenAI-compatible server)."""

    def __init__(self, host: str = "http://127.0.0.1:11434", model: str = "mistral"):
        self.host = host.rstrip("/")
        self.model = model

    # ── availability check ────────────────────────────────────

    def ping(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ── chat (non-streaming, full JSON) ───────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        body = json.dumps(payload).encode()

        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                return data.get("message", {}).get("content", "")
        except urllib.error.URLError as exc:
            raise LLMError(f"Cannot reach Ollama at {self.host}: {exc}") from exc
        except (json.JSONDecodeError, KeyError) as exc:
            raise LLMError(f"Unexpected Ollama response: {exc}") from exc

    # ── streaming chat ────────────────────────────────────────

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
    ) -> Generator[str, None, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        body = json.dumps(payload).encode()

        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            resp = urllib.request.urlopen(req, timeout=180)
        except urllib.error.URLError as exc:
            raise LLMError(f"Cannot reach Ollama at {self.host}: {exc}") from exc

        try:
            while True:
                line = resp.readline()
                if not line:
                    break
                try:
                    chunk = json.loads(line.decode())
                except json.JSONDecodeError:
                    continue
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done", False):
                    break
        finally:
            resp.close()

    # ── model management ──────────────────────────────────────

    def list_models(self) -> List[str]:
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def set_model(self, name: str) -> None:
        self.model = name
