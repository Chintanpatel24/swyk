"""
Permission gate — every write/move/delete/exec must pass through here.

Tiers:
  0 READ    -> auto-approved
  1 WRITE   -> needs y/n
  2 MOVE    -> needs y/n
  3 DELETE  -> needs y/n
  4 EXECUTE -> needs y/n
"""

from core import ui
from core.logger import AuditLogger


TIER_READ = 0
TIER_WRITE = 1
TIER_MOVE = 2
TIER_DELETE = 3
TIER_EXECUTE = 4

TOOL_TIERS = {
    "list_files":       TIER_READ,
    "read_file":        TIER_READ,
    "search_files":     TIER_READ,
    "search_content":   TIER_READ,
    "file_info":        TIER_READ,
    "workspace_tree":   TIER_READ,
    "write_file":       TIER_WRITE,
    "append_file":      TIER_WRITE,
    "create_directory": TIER_WRITE,
    "move_file":        TIER_MOVE,
    "copy_file":        TIER_MOVE,
    "delete_file":      TIER_DELETE,
    "run_command":      TIER_EXECUTE,
}


class PermissionGate:
    def __init__(self, auto_reads=True, allow_shell=False, logger=None, workspace=""):
        self.auto_reads = auto_reads
        self.allow_shell = allow_shell
        self._logger = logger
        self._workspace = workspace

    def check(self, tool_name, params):
        """Returns True if action is approved."""
        tier = TOOL_TIERS.get(tool_name, TIER_EXECUTE)

        if tier == TIER_EXECUTE and not self.allow_shell:
            ui.warn("Shell commands disabled (allow_shell_commands=false in config)")
            self._log(tool_name, params, False, "shell_disabled")
            return False

        if tier == TIER_READ and self.auto_reads:
            self._log(tool_name, params, True, "auto_read")
            return True

        desc = self._describe(tool_name, params)
        approved = ui.action_prompt(desc)

        if approved:
            ui.success("Approved")
        else:
            ui.warn("Declined — skipped")

        self._log(tool_name, params, approved)
        return approved

    def _describe(self, tool, params):
        p = params
        if tool == "write_file":
            size = len(p.get("content", ""))
            return "WRITE {} ({} chars)".format(p.get("path", "?"), size)
        if tool == "append_file":
            size = len(p.get("content", ""))
            return "APPEND to {} ({} chars)".format(p.get("path", "?"), size)
        if tool == "move_file":
            return "MOVE {} -> {}".format(p.get("source", "?"), p.get("destination", "?"))
        if tool == "copy_file":
            return "COPY {} -> {}".format(p.get("source", "?"), p.get("destination", "?"))
        if tool == "delete_file":
            return "!! DELETE {} (cannot undo)".format(p.get("path", "?"))
        if tool == "create_directory":
            return "MKDIR {}".format(p.get("path", "?"))
        if tool == "run_command":
            return "!! SHELL: {}".format(p.get("command", "?"))
        return "{}({})".format(tool, p)

    def _log(self, tool, params, approved, result=""):
        if self._logger:
            self._logger.log(tool, params, approved, result, self._workspace)
