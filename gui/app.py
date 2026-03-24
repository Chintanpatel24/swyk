"""
Main SWYK application window.
Ties together the pixel office, chat panel, and control bar.
"""
import tkinter as tk
from tkinter import messagebox
import os, sys

from core import config as cfg_mod
from core.agent_engine import AgentRunner
from gui.office_canvas import OfficeCanvas
from gui.chat_panel import ChatPanel
from gui.dialogs import APIKeyDialog, NewAgentDialog, SettingsDialog

BG = '#11111b'
BAR_BG = '#181825'
FG = '#cdd6f4'


class SwykApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SWYK — Secure Workspace You Know")
        self.root.configure(bg=BG)
        self.root.minsize(1050, 600)
        self.root.geometry("1100x650")

        # load persistent config
        self.config = cfg_mod.load()
        self.workspace = os.environ.get("SWYK_WORKSPACE", os.getcwd())

        # agent runner
        self.runner = AgentRunner(self.config)

        # build UI
        self._build_menu()
        self._build_main()
        self._build_toolbar()

        # first-run check
        self.root.after(300, self._first_run_check)

        # handle close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self):
        menu = tk.Menu(self.root, bg=BAR_BG, fg=FG, activebackground='#45475a',
            activeforeground=FG, relief='flat')
        self.root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0, bg=BAR_BG, fg=FG)
        file_menu.add_command(label="API Keys...", command=self._open_api_keys)
        file_menu.add_command(label="New Agent...", command=self._open_new_agent)
        file_menu.add_command(label="Settings...", command=self._open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_close)
        menu.add_cascade(label="SWYK", menu=file_menu)

        help_menu = tk.Menu(menu, tearoff=0, bg=BAR_BG, fg=FG)
        help_menu.add_command(label="About", command=self._show_about)
        menu.add_cascade(label="Help", menu=help_menu)

    def _build_main(self):
        self.main_frame = tk.Frame(self.root, bg=BG)
        self.main_frame.pack(fill='both', expand=True, padx=4, pady=4)

        # left: pixel office
        self.office = OfficeCanvas(self.main_frame, self.runner, self.config)
        self.office.pack(side='left', fill='both', padx=(0, 4))

        # right: chat panel
        self.chat = ChatPanel(self.main_frame, self.runner, self.config)
        self.chat.pack(side='right', fill='both', expand=True)
        self.chat.set_workspace(self.workspace)
        self.chat.refresh_agent_list()

    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=BAR_BG, height=44)
        bar.pack(fill='x', side='bottom', padx=4, pady=(0, 4))
        bar.pack_propagate(False)

        tk.Button(bar, text="+ New Agent", bg='#a6e3a1', fg='#1e1e2e',
            font=('Helvetica', 10, 'bold'), relief='flat', padx=10,
            command=self._open_new_agent).pack(side='left', padx=6, pady=6)

        tk.Button(bar, text="🔑 API Keys", bg='#f9e2af', fg='#1e1e2e',
            font=('Helvetica', 10, 'bold'), relief='flat', padx=10,
            command=self._open_api_keys).pack(side='left', padx=4, pady=6)

        tk.Button(bar, text="⚙ Settings", bg='#89b4fa', fg='#1e1e2e',
            font=('Helvetica', 10, 'bold'), relief='flat', padx=10,
            command=self._open_settings).pack(side='left', padx=4, pady=6)

        # workspace label
        ws_short = self.workspace
        if len(ws_short) > 40:
            ws_short = "..." + ws_short[-37:]
        tk.Label(bar, text=f"📂 {ws_short}", bg=BAR_BG, fg='#6c7086',
            font=('Consolas', 9)).pack(side='right', padx=8)

        # agent count
        n = len(self.config.get("agents", []))
        self.agent_count_label = tk.Label(bar, text=f"Agents: {n}",
            bg=BAR_BG, fg='#cdd6f4', font=('Helvetica', 10)).pack(side='right', padx=8)

    def _first_run_check(self):
        """Show welcome on first run."""
        keys = self.config.get("api_keys", {})
        agents = self.config.get("agents", [])

        if not keys or (len(keys) == 0):
            resp = messagebox.askyesno("Welcome to SWYK!",
                "Welcome! SWYK needs an API key to power your agents.\n\n"
                "Supported providers:\n"
                "• Google AI Studio (free tier available)\n"
                "• OpenAI\n"
                "• Anthropic (Claude)\n"
                "• Ollama (local, free)\n\n"
                "Would you like to add an API key now?",
                parent=self.root)
            if resp:
                self._open_api_keys()

    def _open_api_keys(self):
        APIKeyDialog(self.root, self.config)

    def _open_new_agent(self):
        # reload config to get latest keys
        self.config = cfg_mod.load()
        NewAgentDialog(self.root, self.config, on_create=self._on_agent_created)

    def _on_agent_created(self, agent):
        self.config = cfg_mod.load()
        self.office.refresh_agents()
        self.chat.refresh_agent_list()

    def _open_settings(self):
        SettingsDialog(self.root, self.config)

    def _show_about(self):
        messagebox.showinfo("About SWYK",
            "SWYK — Secure Workspace You Know\n"
            "Version 0.2.0\n\n"
            "Open-source AI agent workspace.\n"
            "Pure Python • Zero dependencies • Fully local\n\n"
            "github.com/AiCodingBattle/swyk",
            parent=self.root)

    def _on_close(self):
        cfg_mod.save(self.config)
        self.root.destroy()

    def run(self):
        self.root.mainloop()
