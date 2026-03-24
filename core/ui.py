"""
Terminal colours, banners, spinners — zero dependencies.
"""

from __future__ import annotations

import sys
import threading
import time
import itertools

# ── ANSI codes ────────────────────────────────────────────────
RST  = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
ITAL = "\033[3m"
ULINE = "\033[4m"

RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
MAGENTA = "\033[35m"
CYAN   = "\033[36m"
WHITE  = "\033[37m"
GRAY   = "\033[90m"


def c(text: str, *codes: str) -> str:
    return "".join(codes) + text + RST


BANNER = rf"""
{c("  ╔═══════════════════════════════════════════╗", BOLD, CYAN)}
{c("  ║", BOLD, CYAN)}  {c("SWIK", BOLD, GREEN)} {c("— Secure Workspace Intelligence Kit", DIM)} {c("║", BOLD, CYAN)}
{c("  ╚═══════════════════════════════════════════╝", BOLD, CYAN)}
"""

HELP_TEXT = f"""
{c("Commands:", BOLD)}
  {c("/help", YELLOW)}       Show this help
  {c("/config", YELLOW)}     Show current configuration
  {c("/model", YELLOW)} name Change LLM model
  {c("/tree", YELLOW)}       Show workspace file tree
  {c("/clear", YELLOW)}      Clear conversation history
  {c("/exit", YELLOW)}       Quit SWIK  ({c("Ctrl-C", DIM)} also works)
"""


def banner() -> None:
    print(BANNER)


def help_msg() -> None:
    print(HELP_TEXT)


def info(msg: str) -> None:
    print(f"{c('[swik]', CYAN)} {msg}")


def warn(msg: str) -> None:
    print(f"{c('[warn]', YELLOW)} {msg}")


def error(msg: str) -> None:
    print(f"{c('[error]', RED)} {msg}")


def success(msg: str) -> None:
    print(f"{c('[  ✓ ]', GREEN)} {msg}")


def action_prompt(description: str) -> bool:
    """Ask user y/n for a destructive action."""
    print()
    print(f"{c('┌─ Action requested ─────────────────────────', YELLOW)}")
    print(f"{c('│', YELLOW)} {description}")
    print(f"{c('└────────────────────────────────────────────', YELLOW)}")
    while True:
        try:
            ans = input(f"{c('Approve? [y/n]: ', BOLD, YELLOW)}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("  Please answer y or n.")


def thinking_msg(text: str = "Thinking") -> "Spinner":
    return Spinner(text)


class Spinner:
    """Braille-dot spinner for long-running ops."""

    _FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, text: str = "Working"):
        self._text = text
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "Spinner":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _spin(self) -> None:
        for frame in itertools.cycle(self._FRAMES):
            if self._stop.is_set():
                break
            sys.stdout.write(f"\r{c(frame, CYAN)} {self._text} ")
            sys.stdout.flush()
            time.sleep(0.08)


def format_file_tree(root: str, files: list[str], max_show: int = 40) -> str:
    """Pretty-print a file list as a tree."""
    lines = [c(f"  {root}/", BOLD, BLUE)]
    for i, f in enumerate(sorted(files)[:max_show]):
        connector = "├── " if i < len(files) - 1 else "└── "
        lines.append(f"  {c(connector, DIM)}{f}")
    if len(files) > max_show:
        lines.append(f"  {c(f'  … and {len(files) - max_show} more', DIM)}")
    return "\n".join(lines)


def format_agent_response(text: str) -> str:
    """Wrap agent prose in a light box."""
    lines = text.strip().split("\n")
    out = [c("┌─ swik ──────────────────────────────────────", GREEN)]
    for line in lines:
        out.append(f"{c('│', GREEN)} {line}")
    out.append(c("└────────────────────────────────────────────", GREEN))
    return "\n".join(out)
