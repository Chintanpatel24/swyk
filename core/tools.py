"""Tool executor for file ops — with permission callbacks."""
import json, os, time

TOOLS = {
    "list_files": {"tier": 0, "desc": "List directory"},
    "read_file": {"tier": 0, "desc": "Read file"},
    "search": {"tier": 0, "desc": "Search text in files"},
    "find": {"tier": 0, "desc": "Find files by pattern"},
    "tree": {"tier": 0, "desc": "Workspace tree"},
    "write_file": {"tier": 1, "desc": "Write file"},
    "mkdir": {"tier": 1, "desc": "Create directory"},
    "move": {"tier": 2, "desc": "Move/rename"},
    "copy": {"tier": 2, "desc": "Copy"},
    "delete": {"tier": 3, "desc": "Delete"},
}

def execute(sandbox, tool, params, approve_fn=None):
    """Execute tool. approve_fn(desc)->bool for tier>0. Returns (ok, result)."""
    t = TOOLS.get(tool)
    if not t: return False, f"Unknown tool: {tool}"
    if t["tier"] > 0 and approve_fn:
        desc = f"{tool}({json.dumps(params)})"
        if not approve_fn(desc): return False, "Declined"
    try:
        if tool=="list_files": return True, "\n".join(sandbox.list_dir(params.get("path",".")))
        if tool=="read_file": return True, sandbox.read_file(params["path"])
        if tool=="search": return True, "\n".join(sandbox.search(params["query"]))
        if tool=="find": return True, "\n".join(sandbox.find(params["pattern"]))
        if tool=="tree": return True, "\n".join(sandbox.walk())
        if tool=="write_file": return True, sandbox.write_file(params["path"], params["content"])
        if tool=="mkdir": return True, sandbox.mkdir(params["path"])
        if tool=="move": return True, sandbox.move(params["source"], params["destination"])
        if tool=="copy": return True, sandbox.copy(params["source"], params["destination"])
        if tool=="delete": return True, sandbox.delete(params["path"])
    except Exception as e:
        return False, str(e)
    return False, "Unknown"
