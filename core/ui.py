"""
Terminal UI — colours, banners, prompts.
Pure stdlib — zero dependencies.
"""

import sys
import threading
import time
import itertools


# --- ansi ---
RST = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
GRAY = "\033[90m"
WHITE = "\033[97m"
BG_RED = "\033[41m"


def c(text, *codes):
    """Wrap text in ANSI codes."""
    return "".join(codes) + str(text) + RST


BANNER = r"""
{top}
{mid}  {name} {dash} {tag} {mid2}
{bot}
""".format(
    top=c("  +=========================================+", BOLD, CYAN),
    mid=c("  |", BOLD, CYAN),
    name=c("SWYK", BOLD, GREEN),
    dash=c("—", DIM),
    tag=c("Secure Workspace You Know", DIM, WHITE),
    mid2=c("|", BOLD, CYAN),
    bot=c("  +=========================================+", BOLD, CYAN),
)

HELP_TEXT = """
{hdr}
  {h} {d1}
  {t} {d2}
  {m} {d3}
  {cf} {d4}
  {cl} {d5}
  {ex} {d6}
""".format(
    hdr=c("Commands:", BOLD, WHITE),
    h=c("/help", YELLOW), d1="Show this help",
    t=c("/tree", YELLOW), d2="Show workspace file tree",
    m=c("/model <name>", YELLOW), d3="Switch LLM model",
    cf=c("/config", YELLOW), d4="Show configuration",
    cl=c("/clear", YELLOW), d5="Clear conversation history",
    ex=c("/exit", YELLOW), d6="Quit  (Ctrl+C also works)",
)


def banner():
    sys.stdout.write(BANNER)
    sys.stdout.flush()


def help_msg():
    sys.stdout.write(HELP_TEXT + "\n")
    sys.stdout.flush()


def info(msg):
    print("{}  {}".format(c("[swyk]", CYAN), msg))


def warn(msg):
    print("{}  {}".format(c("[warn]", YELLOW), msg))


def error(msg):
    print("{}  {}".format(c("[err]", RED, BOLD), msg))


def success(msg):
    print("{}  {}".format(c("[ ok ]", GREEN), msg))


def thought(msg):
    print("{}  {}".format(c("  >", DIM), c(msg, DIM, GRAY)))


def tool_call(name, params_str):
    info("Tool: {}({})".format(c(name, BOLD, YELLOW), params_str))


def tool_result(ok, msg):
    sym = c("  +", GREEN) if ok else c("  x", RED)
    # cap display
    lines = msg.split("\n")
    if len(lines) > 15:
        display = "\n".join(lines[:15]) + "\n  ... ({} more lines)".format(len(lines) - 15)
    else:
        display = msg
    print("{} {}".format(sym, display))


def agent_response(text):
    print()
    print(c("  +--- swyk ---------------------------------", GREEN))
    for line in text.strip().split("\n"):
        print("{}  {}".format(c("  |", GREEN), line))
    print(c("  +-----------------------------------------", GREEN))
    print()


def action_prompt(description):
    """Ask user y/n. Returns True if approved."""
    print()
    print(c("  +--- Permission Required ------------------", YELLOW))
    print("{}  {}".format(c("  |", YELLOW), description))
    print(c("  +-----------------------------------------", YELLOW))
    while True:
        try:
            ans = input("{}  ".format(c("  Approve? [y/n]:", BOLD, YELLOW))).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("  Type y or n.")


class Spinner:
    """Braille spinner for thinking indicator."""
    _FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, text="Thinking"):
        self._text = text
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *a):
        self.stop()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _run(self):
        for frame in itertools.cycle(self._FRAMES):
            if self._stop.is_set():
                break
            sys.stdout.write("\r{} {} ".format(c(frame, CYAN), self._text))
            sys.stdout.flush()
            time.sleep(0.08)
