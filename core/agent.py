"""
Agent — the core reasoning loop.

The agent receives user messages, constructs an LLM prompt that
includes the tool catalogue and workspace context, parses the
LLM's structured output, executes approved tools, feeds results
back, and loops until the LLM emits a final RESPONSE.

Output protocol (expected from LLM)
────────────────────────────────────
The LLM must reply with one or more blocks:

    THOUGHT: <internal reasoning — shown dimmed>
    ACTION: <tool_name>
    PARAMS: <json dict>

…or a final answer:

    THOUGHT: <reasoning>
    RESPONSE: <answer to the user>
"""

from __future__ import annotations

import json
import re
import textwrap
from typing import Dict, List, Optional, Tuple

from .config import Config
from .llm_client import LLMClient, LLMError
from .sandbox import Sandbox
from .permissions import PermissionGate
from .tools import TOOL_SCHEMAS, execute_tool
from . import ui


# ── system prompt ─────────────────────────────────────────────

def _build_system_prompt(workspace_root: str, file_snapshot: str) -> str:
    tool_docs = ""
    for name, schema in TOOL_SCHEMAS.items():
        params_str = ", ".join(
            f"{k}: {v}" for k, v in schema["parameters"].items()
        ) if schema["parameters"] else "(none)"
        tool_docs += f"  - {name}({params_str})\n    {schema['description']}\n"

    return textwrap.dedent(f"""\
        You are SWIK, a helpful and security-conscious file-system assistant.
        You operate ONLY inside this workspace directory:
          {workspace_root}

        RULES:
        1. NEVER access files outside the workspace.
        2. NEVER fabricate file contents — always use read_file first.
        3. For ANY action that creates, modifies, moves or deletes files,
           you MUST emit an ACTION block so the user can approve it.
        4. Be concise but helpful.
        5. If you are unsure, ask the user for clarification.
        6. For shell commands, prefer built-in tools over run_command.

        AVAILABLE TOOLS:
        {tool_docs}

        RESPONSE FORMAT — you must use EXACTLY this format:

        For reasoning + tool calls:
        ```
        THOUGHT: <your reasoning>
        ACTION: <tool_name>
        PARAMS: {{"param1": "value1", "param2": "value2"}}
        ```

        For final answers (no tool needed):
        ```
        THOUGHT: <your reasoning>
        RESPONSE: <your answer to the user>
        ```

        You may chain multiple THOUGHT/ACTION blocks before a final RESPONSE.
        After each ACTION, you will receive the tool result as a TOOL_RESULT message.

        CURRENT WORKSPACE SNAPSHOT:
        {file_snapshot}
    """)


# ── output parser ─────────────────────────────────────────────

_RE_THOUGHT  = re.compile(r"THOUGHT:\s*(.+?)(?=\n(?:ACTION|RESPONSE|THOUGHT)|$)", re.S)
_RE_ACTION   = re.compile(r"ACTION:\s*(\w+)")
_RE_PARAMS   = re.compile(r"PARAMS:\s*(\{.*?\})", re.S)
_RE_RESPONSE = re.compile(r"RESPONSE:\s*(.+)", re.S)


def parse_llm_output(text: str) -> List[Dict]:
    """
    Parse the LLM's structured output into a list of steps.
    Each step is one of:
      {"type": "thought",  "content": "..."}
      {"type": "action",   "name": "...", "params": {...}}
      {"type": "response", "content": "..."}
    """
    steps: List[Dict] = []

    # try structured parse first
    lines = text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("THOUGHT:"):
            content = line[len("THOUGHT:"):].strip()
            # consume continuation lines
            j = i + 1
            while j < len(lines) and not any(
                lines[j].strip().startswith(k)
                for k in ("THOUGHT:", "ACTION:", "RESPONSE:", "PARAMS:")
            ):
                content += "\n" + lines[j].strip()
                j += 1
            steps.append({"type": "thought", "content": content.strip()})
            i = j
            continue

        if line.startswith("ACTION:"):
            name = line[len("ACTION:"):].strip()
            params = {}
            # look for PARAMS on next line(s)
            j = i + 1
            params_text = ""
            while j < len(lines):
                l = lines[j].strip()
                if l.startswith("PARAMS:"):
                    params_text = l[len("PARAMS:"):].strip()
                    j += 1
                    # continue collecting if JSON isn't complete
                    while j < len(lines) and params_text.count("{") > params_text.count("}"):
                        params_text += "\n" + lines[j].strip()
                        j += 1
                    break
                elif any(l.startswith(k) for k in ("THOUGHT:", "ACTION:", "RESPONSE:")):
                    break
                j += 1

            if params_text:
                try:
                    params = json.loads(params_text)
                except json.JSONDecodeError:
                    # try to extract JSON from the text
                    m = re.search(r'\{.*\}', params_text, re.S)
                    if m:
                        try:
                            params = json.loads(m.group())
                        except json.JSONDecodeError:
                            params = {"_raw": params_text}

            steps.append({"type": "action", "name": name, "params": params})
            i = j
            continue

        if line.startswith("RESPONSE:"):
            content = line[len("RESPONSE:"):].strip()
            j = i + 1
            while j < len(lines):
                l = lines[j].strip()
                if any(l.startswith(k) for k in ("THOUGHT:", "ACTION:")):
                    break
                content += "\n" + lines[j]
                j += 1
            steps.append({"type": "response", "content": content.strip()})
            i = j
            continue

        i += 1

    # if nothing was parsed, treat the whole thing as a response
    if not steps:
        steps.append({"type": "response", "content": text.strip()})

    return steps


# ── agent class ───────────────────────────────────────────────

class Agent:
    MAX_TOOL_ROUNDS = 10          # prevent infinite loops

    def __init__(
        self,
        llm: LLMClient,
        sandbox: Sandbox,
        gate: PermissionGate,
        config: Config,
    ):
        self.llm = llm
        self.sandbox = sandbox
        self.gate = gate
        self.config = config

        # conversation memory
        self._history: List[Dict[str, str]] = []

        # build initial system prompt
        try:
            tree = "\n".join(sandbox.walk(".", max_files=60))
        except Exception:
            tree = "(could not list files)"

        self._system = _build_system_prompt(
            workspace_root=str(sandbox.root),
            file_snapshot=tree,
        )

    def reset(self) -> None:
        self._history.clear()

    def process(self, user_input: str) -> str:
        """
        Full agent loop:
          user_input → LLM → parse → (tool call → permission → execute → feed back)* → final response
        """
        self._history.append({"role": "user", "content": user_input})

        final_response = ""

        for _round in range(self.MAX_TOOL_ROUNDS):
            messages = [{"role": "system", "content": self._system}] + self._history[
                -self.config.history_length :
            ]

            # call LLM
            with ui.thinking_msg("Thinking"):
                try:
                    raw = self.llm.chat(messages, temperature=0.3)
                except LLMError as exc:
                    ui.error(str(exc))
                    return f"Error communicating with LLM: {exc}"

            if not raw.strip():
                return "(empty response from model)"

            steps = parse_llm_output(raw)

            # process steps
            has_action = False
            for step in steps:
                if step["type"] == "thought":
                    print(f"{ui.c('  💭 ', ui.DIM)}{ui.c(step['content'], ui.DIM)}")

                elif step["type"] == "action":
                    has_action = True
                    name = step["name"]
                    params = step["params"]

                    ui.info(f"Tool call: {ui.c(name, ui.BOLD)}({json.dumps(params, ensure_ascii=False)})")

                    ok, result = execute_tool(name, params, self.sandbox, self.gate)

                    status = "✓" if ok else "✗"
                    print(f"  {ui.c(status, ui.GREEN if ok else ui.RED)} {result[:500]}")

                    # feed result back to LLM
                    self._history.append({"role": "assistant", "content": raw})
                    self._history.append({
                        "role": "user",
                        "content": f"TOOL_RESULT ({name}): {result[:2000]}",
                    })

                elif step["type"] == "response":
                    final_response = step["content"]

            if final_response:
                self._history.append({"role": "assistant", "content": final_response})
                return final_response

            if not has_action:
                # LLM gave us something but no action and no RESPONSE tag
                # treat the raw output as the response
                self._history.append({"role": "assistant", "content": raw})
                return raw.strip()

        return "(max tool rounds reached — stopping)"
