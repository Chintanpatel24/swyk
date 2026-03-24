"""
Permission gate.

Actions are classified into tiers:

  TIER 0 – READ     → auto-approved  (list, read, search, info)
  TIER 1 – WRITE    → requires y/n   (write, create dir)
  TIER 2 – MOVE     → requires y/n   (move, copy, rename)
  TIER 3 – DELETE   → requires y/n + confirmation text
  TIER 4 – EXECUTE  → requires y/n   (shell commands)
"""

from __future__ import annotations

from enum import IntEnum
from typing import Dict, Optional

from . import ui
from .logger import AuditLogger


class Tier(IntEnum):
    READ = 0
    WRITE = 1
    MOVE = 2
    DELETE = 3
    EXECUTE = 4


# map tool names → tiers
TOOL_TIERS: Dict[str, Tier] = {
    "list_files":      Tier.READ,
    "read_file":       Tier.READ,
    "search_files":    Tier.READ,
    "search_content":  Tier.READ,
    "file_info":       Tier.READ,
    "workspace_tree":  Tier.READ,
    "write_file":      Tier.WRITE,
    "create_directory": Tier.WRITE,
    "move_file":       Tier.MOVE,
    "copy_file":       Tier.MOVE,
    "delete_file":     Tier.DELETE,
    "run_command":     Tier.EXECUTE,
}


class PermissionGate:
    """Asks the human for approval before write / move / delete / exec."""

    def __init__(
        self,
        auto_approve_reads: bool = True,
        allow_shell: bool = False,
        logger: Optional[AuditLogger] = None,
        workspace: str = "",
    ):
        self.auto_approve_reads = auto_approve_reads
        self.allow_shell = allow_shell
        self._logger = logger
        self._workspace = workspace

    def check(self, tool_name: str, params: dict) -> bool:
        """
        Returns True if the action is approved (auto or by user).
        Returns False if the user declines.
        """
        tier = TOOL_TIERS.get(tool_name, Tier.EXECUTE)

        # shell commands globally disabled?
        if tier == Tier.EXECUTE and not self.allow_shell:
            ui.warn("Shell commands are disabled in config (allow_shell_commands=false).")
            self._log(tool_name, params, approved=False, result="shell disabled")
            return False

        # auto-approve reads
        if tier == Tier.READ and self.auto_approve_reads:
            self._log(tool_name, params, approved=True, result="auto-read")
            return True

        # build description
        desc = self._describe(tool_name, params, tier)
        approved = ui.action_prompt(desc)

        if approved:
            ui.success("Approved.")
        else:
            ui.warn("Declined — action skipped.")

        self._log(tool_name, params, approved=approved)
        return approved

    # ── helpers ───────────────────────────────────────────────

    @staticmethod
    def _describe(tool: str, params: dict, tier: Tier) -> str:
        p = params
        if tool == "write_file":
            size = len(p.get("content", ""))
            return f"WRITE {p.get('path','?')}  ({size} chars)"
        if tool == "move_file":
            return f"MOVE {p.get('source','?')} → {p.get('destination','?')}"
        if tool == "copy_file":
            return f"COPY {p.get('source','?')} → {p.get('destination','?')}"
        if tool == "delete_file":
            return f"⚠  DELETE {p.get('path','?')}  (cannot be undone)"
        if tool == "create_directory":
            return f"MKDIR {p.get('path','?')}"
        if tool == "run_command":
            return f"⚠  RUN SHELL COMMAND:  {p.get('command','?')}"
        return f"{tool}({p})"

    def _log(self, tool: str, params: dict, approved: bool, result: str = "") -> None:
        if self._logger:
            self._logger.log(
                action=tool,
                params=params,
                approved=approved,
                result=result,
                workspace=self._workspace,
            )
