"""
Agent — the reasoning loop.

Sends user messages + tool catalogue to the LLM.
Parses structured output (THOUGHT / ACTION / RESPONSE).
Executes approved tools, feeds results back, loops until
the LLM emits a final RESPONSE.
"""

import json
import re
import textwrap

from core.config import Config
from core.llm import LLMClient, LLMError
from core.sandbox import Sandbox
from core.permissions import PermissionGate
from core.tools import TOOL_SCHEMAS, execute_tool
from core import ui


def _system_prompt(workspace, file_tree):
    tool_docs = ""
    for name, schema in TOOL_SCHEMAS.items():
        params = ", ".join("{}: {}".format(k, v) for k, v in schema["params"].items()) if schema["params"] else "(none)"
        tool_docs += "  - {}({})\n    {}\n".format(name, params, schema["desc"])

    return textwrap.dedent("""\
You are SWYK, a helpful and security-conscious file-system assistant.
You operate ONLY inside this workspace:
  {workspace}

RULES:
1. NEVER access files outside the workspace.
2. NEVER make up file contents — always read_file first.
3. For ANY action that creates, modifies, moves or deletes files,
   you MUST use an ACTION block so the user can approve.
4. Be concise.
5. If unsure, ask the user.

TOOLS:
{tools}

OUTPUT FORMAT (follow EXACTLY):

When you need a tool:
THOUGHT: your reasoning
ACTION: tool_name
PARAMS: {{"param": "value"}}

When giving a final answer (no tool needed):
THOUGHT: your reasoning
RESPONSE: your answer

You may chain multiple THOUGHT+ACTION blocks. After each ACTION you
will get a TOOL_RESULT message with the output.

WORKSPACE FILES:
{tree}
""").format(workspace=workspace, tools=tool_docs, tree=file_tree)


def _parse_output(text):
    """Parse LLM output into steps: thought / action / response."""
    steps = []
    lines = text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.upper().startswith("THOUGHT:"):
            content = line[len("THOUGHT:"):].strip()
            j = i + 1
            while j < len(lines) and not _is_header(lines[j]):
                content += "\n" + lines[j].strip()
                j += 1
            steps.append({"type": "thought", "content": content.strip()})
            i = j
            continue

        if line.upper().startswith("ACTION:"):
            name = line[len("ACTION:"):].strip()
            params = {}
            j = i + 1
            params_text = ""
            while j < len(lines):
                l = lines[j].strip()
                if l.upper().startswith("PARAMS:"):
                    params_text = l[len("PARAMS:"):].strip()
                    j += 1
                    while j < len(lines) and params_text.count("{") > params_text.count("}"):
                        params_text += " " + lines[j].strip()
                        j += 1
                    break
                elif _is_header(l):
                    break
                j += 1

            if params_text:
                try:
                    params = json.loads(params_text)
                except json.JSONDecodeError:
                    m = re.search(r'\{.*\}', params_text, re.S)
                    if m:
                        try:
                            params = json.loads(m.group())
                        except json.JSONDecodeError:
                            params = {}

            steps.append({"type": "action", "name": name, "params": params})
            i = j
            continue

        if line.upper().startswith("RESPONSE:"):
            content = line[len("RESPONSE:"):].strip()
            j = i + 1
            while j < len(lines) and not _is_header(lines[j]):
                content += "\n" + lines[j]
                j += 1
            steps.append({"type": "response", "content": content.strip()})
            i = j
            continue

        i += 1

    if not steps:
        steps.append({"type": "response", "content": text.strip()})

    return steps


def _is_header(line):
    l = line.strip().upper()
    return l.startswith("THOUGHT:") or l.startswith("ACTION:") or l.startswith("RESPONSE:") or l.startswith("PARAMS:")


class Agent:
    MAX_ROUNDS = 10

    def __init__(self, llm, sandbox, gate, config):
        self.llm = llm
        self.sandbox = sandbox
        self.gate = gate
        self.config = config
        self._history = []

        try:
            tree = "\n".join(sandbox.walk(".", max_files=60))
        except Exception:
            tree = "(could not read workspace)"

        self._system = _system_prompt(sandbox.root, tree)

    def reset(self):
        self._history = []

    def process(self, user_input):
        """Full agent loop. Returns final response string."""
        self._history.append({"role": "user", "content": user_input})

        for _ in range(self.MAX_ROUNDS):
            messages = [{"role": "system", "content": self._system}]
            messages += self._history[-self.config.history_length:]

            with ui.Spinner("Thinking"):
                try:
                    raw = self.llm.chat(messages, temperature=0.3)
                except LLMError as e:
                    ui.error(str(e))
                    return "Error talking to LLM: {}".format(e)

            if not raw.strip():
                return "(empty response from model)"

            steps = _parse_output(raw)

            has_action = False
            final = ""

            for step in steps:
                if step["type"] == "thought":
                    ui.thought(step["content"])

                elif step["type"] == "action":
                    has_action = True
                    name = step["name"]
                    params = step["params"]

                    ui.tool_call(name, json.dumps(params, ensure_ascii=False))

                    ok, result = execute_tool(name, params, self.sandbox, self.gate)
                    ui.tool_result(ok, result[:500])

                    self._history.append({"role": "assistant", "content": raw})
                    self._history.append({
                        "role": "user",
                        "content": "TOOL_RESULT ({}): {}".format(name, result[:2000]),
                    })

                elif step["type"] == "response":
                    final = step["content"]

            if final:
                self._history.append({"role": "assistant", "content": final})
                return final

            if not has_action:
                self._history.append({"role": "assistant", "content": raw})
                return raw.strip()

        return "(max tool rounds reached)"
