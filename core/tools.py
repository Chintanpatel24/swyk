"""
Tool registry.

Each tool is a plain function.  The TOOLS dict maps names to
(function, schema, tier) triples so the agent can discover them
and the permission gate can classify them.
"""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .sandbox import Sandbox, SandboxError
from .permissions import PermissionGate, Tier


class ToolError(Exception):
    pass


# ── individual tool implementations ──────────────────────────

def tool_list_files(sandbox: Sandbox, path: str = ".") -> str:
    entries = sandbox.list_dir(path)
    if not entries:
        return "(empty directory)"
    return "\n".join(entries)


def tool_read_file(sandbox: Sandbox, path: str) -> str:
    return sandbox.read_file(path)


def tool_write_file(sandbox: Sandbox, path: str, content: str) -> str:
    return sandbox.write_file(path, content)


def tool_move_file(sandbox: Sandbox, source: str, destination: str) -> str:
    return sandbox.move_file(source, destination)


def tool_copy_file(sandbox: Sandbox, source: str, destination: str) -> str:
    return sandbox.copy_file(source, destination)


def tool_delete_file(sandbox: Sandbox, path: str) -> str:
    return sandbox.delete_file(path)


def tool_create_directory(sandbox: Sandbox, path: str) -> str:
    return sandbox.mkdir(path)


def tool_file_info(sandbox: Sandbox, path: str) -> str:
    info = sandbox.file_info(path)
    info["modified"] = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(info["modified"])
    )
    info["size_human"] = _human_size(info["size"])
    return json.dumps(info, indent=2)


def tool_search_files(sandbox: Sandbox, pattern: str) -> str:
    results = sandbox.search_files(pattern)
    if not results:
        return f"No files matching '{pattern}'"
    return "\n".join(results)


def tool_search_content(sandbox: Sandbox, query: str, path: str = ".") -> str:
    results = sandbox.search_content(query, path)
    if not results:
        return f"No matches for '{query}'"
    lines = []
    for r in results:
        lines.append(f"{r['file']}:{r['line']}: {r['text']}")
    return "\n".join(lines)


def tool_workspace_tree(sandbox: Sandbox) -> str:
    files = sandbox.walk(".", max_files=100)
    if not files:
        return "(empty workspace)"
    return "\n".join(files)


def tool_run_command(
    sandbox: Sandbox, command: str, timeout: int = 30
) -> str:
    """
    Run a shell command **inside the sandbox directory**.
    stdout + stderr are captured.  Timeout = 30s default.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(sandbox.root),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "HOME": str(sandbox.root)},  # restrict $HOME
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        parts = []
        if out:
            parts.append(f"STDOUT:\n{out}")
        if err:
            parts.append(f"STDERR:\n{err}")
        parts.append(f"(exit code {result.returncode})")
        return "\n".join(parts) if parts else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s."
    except Exception as exc:
        return f"Command failed: {exc}"


# ── tool table ────────────────────────────────────────────────

TOOL_SCHEMAS = {
    "list_files": {
        "description": "List files and directories at the given path (relative to workspace root).",
        "parameters": {"path": "string (default '.')"},
    },
    "read_file": {
        "description": "Read the full contents of a file.",
        "parameters": {"path": "string"},
    },
    "write_file": {
        "description": "Write content to a file (create or overwrite).",
        "parameters": {"path": "string", "content": "string"},
    },
    "move_file": {
        "description": "Move or rename a file/directory.",
        "parameters": {"source": "string", "destination": "string"},
    },
    "copy_file": {
        "description": "Copy a file or directory.",
        "parameters": {"source": "string", "destination": "string"},
    },
    "delete_file": {
        "description": "Delete a file or directory (cannot be undone).",
        "parameters": {"path": "string"},
    },
    "create_directory": {
        "description": "Create a new directory (including parents).",
        "parameters": {"path": "string"},
    },
    "file_info": {
        "description": "Get metadata about a file (size, permissions, modified date).",
        "parameters": {"path": "string"},
    },
    "search_files": {
        "description": "Find files matching a glob pattern (e.g. '*.py', 'src/**/*.js').",
        "parameters": {"pattern": "string"},
    },
    "search_content": {
        "description": "Search for text inside files (case-insensitive grep).",
        "parameters": {"query": "string", "path": "string (default '.')"},
    },
    "workspace_tree": {
        "description": "Show the full file tree of the workspace.",
        "parameters": {},
    },
    "run_command": {
        "description": "Run a shell command in the workspace directory. Use sparingly.",
        "parameters": {"command": "string"},
    },
}


# dispatcher
_DISPATCH: Dict[str, Callable] = {
    "list_files":       tool_list_files,
    "read_file":        tool_read_file,
    "write_file":       tool_write_file,
    "move_file":        tool_move_file,
    "copy_file":        tool_copy_file,
    "delete_file":      tool_delete_file,
    "create_directory": tool_create_directory,
    "file_info":        tool_file_info,
    "search_files":     tool_search_files,
    "search_content":   tool_search_content,
    "workspace_tree":   tool_workspace_tree,
    "run_command":      tool_run_command,
}


def execute_tool(
    tool_name: str,
    params: dict,
    sandbox: Sandbox,
    gate: PermissionGate,
) -> Tuple[bool, str]:
    """
    Execute a tool after passing the permission gate.
    Returns (success, result_string).
    """
    if tool_name not in _DISPATCH:
        return False, f"Unknown tool: {tool_name}"

    # permission check
    if not gate.check(tool_name, params):
        return False, "Action declined by user."

    fn = _DISPATCH[tool_name]

    try:
        # build kwargs — first positional arg is always sandbox
        result = fn(sandbox, **params)
        return True, result
    except SandboxError as exc:
        return False, f"Sandbox violation: {exc}"
    except Exception as exc:
        return False, f"Tool error: {exc}"


def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"
