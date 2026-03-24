"""
Tool registry and executor.
Every tool is a plain function. The dispatcher runs them after
the permission gate approves.
"""

import json
import os
import subprocess
import time

from core.sandbox import Sandbox, SandboxError
from core.permissions import PermissionGate


class ToolError(Exception):
    pass


# --- tool functions ---

def tool_list_files(sb, path="."):
    entries = sb.list_dir(path)
    return "\n".join(entries) if entries else "(empty directory)"


def tool_read_file(sb, path=""):
    return sb.read_file(path)


def tool_write_file(sb, path="", content=""):
    return sb.write_file(path, content)


def tool_append_file(sb, path="", content=""):
    return sb.append_file(path, content)


def tool_move_file(sb, source="", destination=""):
    return sb.move_file(source, destination)


def tool_copy_file(sb, source="", destination=""):
    return sb.copy_file(source, destination)


def tool_delete_file(sb, path=""):
    return sb.delete(path)


def tool_create_directory(sb, path=""):
    return sb.mkdir(path)


def tool_file_info(sb, path=""):
    info = sb.file_info(path)
    info["modified"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info["modified"]))
    info["size_human"] = _human_size(info["size"])
    return json.dumps(info, indent=2)


def tool_search_files(sb, pattern=""):
    results = sb.search_files(pattern)
    return "\n".join(results) if results else "No files matching '{}'".format(pattern)


def tool_search_content(sb, query="", path="."):
    results = sb.search_content(query, path)
    if not results:
        return "No matches for '{}'".format(query)
    lines = []
    for r in results:
        lines.append("{}:{}: {}".format(r["file"], r["line"], r["text"]))
    return "\n".join(lines)


def tool_workspace_tree(sb):
    files = sb.walk(".", max_files=100)
    return "\n".join(files) if files else "(empty workspace)"


def tool_run_command(sb, command="", timeout=30):
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=sb.root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        parts = []
        if result.stdout.strip():
            parts.append("STDOUT:\n" + result.stdout.strip())
        if result.stderr.strip():
            parts.append("STDERR:\n" + result.stderr.strip())
        parts.append("(exit code {})".format(result.returncode))
        return "\n".join(parts)
    except subprocess.TimeoutExpired:
        return "Command timed out after {}s".format(timeout)
    except Exception as e:
        return "Command failed: {}".format(e)


# --- dispatch table ---

TOOL_SCHEMAS = {
    "list_files": {
        "desc": "List files/directories at a path relative to workspace.",
        "params": {"path": "string, default '.'"},
    },
    "read_file": {
        "desc": "Read full contents of a file.",
        "params": {"path": "string"},
    },
    "write_file": {
        "desc": "Create or overwrite a file with content.",
        "params": {"path": "string", "content": "string"},
    },
    "append_file": {
        "desc": "Append content to end of a file.",
        "params": {"path": "string", "content": "string"},
    },
    "move_file": {
        "desc": "Move or rename a file/directory.",
        "params": {"source": "string", "destination": "string"},
    },
    "copy_file": {
        "desc": "Copy a file or directory.",
        "params": {"source": "string", "destination": "string"},
    },
    "delete_file": {
        "desc": "Delete a file or directory permanently.",
        "params": {"path": "string"},
    },
    "create_directory": {
        "desc": "Create a directory (including parents).",
        "params": {"path": "string"},
    },
    "file_info": {
        "desc": "Get file metadata (size, permissions, modified date).",
        "params": {"path": "string"},
    },
    "search_files": {
        "desc": "Find files by glob pattern (e.g. '*.py').",
        "params": {"pattern": "string"},
    },
    "search_content": {
        "desc": "Grep: search text inside files (case-insensitive).",
        "params": {"query": "string", "path": "string, default '.'"},
    },
    "workspace_tree": {
        "desc": "Show full file tree of workspace.",
        "params": {},
    },
    "run_command": {
        "desc": "Run a shell command inside the workspace. Use sparingly.",
        "params": {"command": "string"},
    },
}

_DISPATCH = {
    "list_files":       tool_list_files,
    "read_file":        tool_read_file,
    "write_file":       tool_write_file,
    "append_file":      tool_append_file,
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


def execute_tool(tool_name, params, sandbox, gate):
    """
    Run a tool after checking permissions.
    Returns (success: bool, result: str).
    """
    if tool_name not in _DISPATCH:
        return False, "Unknown tool: {}".format(tool_name)

    if not gate.check(tool_name, params):
        return False, "Action declined by user."

    fn = _DISPATCH[tool_name]

    try:
        result = fn(sandbox, **params)
        return True, result
    except SandboxError as e:
        return False, "Sandbox: {}".format(e)
    except TypeError as e:
        return False, "Bad params: {}".format(e)
    except Exception as e:
        return False, "Error: {}".format(e)


def _human_size(nbytes):
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return "{:.1f} {}".format(nbytes, unit)
        nbytes /= 1024.0
    return "{:.1f} TB".format(nbytes)
