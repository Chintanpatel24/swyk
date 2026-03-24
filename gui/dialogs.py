"""Pop-up dialogs — API keys, new agent, settings."""
import tkinter as tk
from tkinter import ttk, messagebox
from core import config as cfg_mod
from core import api_client

BG = '#1e1e2e'
FG = '#cdd6f4'
ENTRY_BG = '#313244'
BTN_BG = '#89b4fa'
BTN_FG = '#1e1e2e'

PROVIDERS = [
    ("Google AI Studio (Gemini)", "google_ai"),
    ("OpenAI", "openai"),
    ("Anthropic (Claude)", "anthropic"),
    ("Ollama (Local)", "ollama"),
    ("Custom (OpenAI-compatible)", "custom"),
]

ROLES = ["Coder", "Writer", "Researcher", "Analyst", "Designer", "Manager", "General Assistant", "Custom"]

COLORS = ["Blue", "Red", "Green", "Orange", "Purple", "Teal", "Dark Orange", "Light Blue"]


class APIKeyDialog(tk.Toplevel):
    """Dialog for adding/managing API keys."""
    def __init__(self, parent, config):
        super().__init__(parent)
        self.title("SWYK — API Keys")
        self.geometry("500x450")
        self.configure(bg=BG)
        self.config_data = config
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="API Key Management", bg=BG, fg=FG,
            font=('Helvetica', 14, 'bold')).pack(pady=(16, 8))

        tk.Label(self, text="Your keys are stored locally and never sent anywhere\nexcept to the provider you choose.",
            bg=BG, fg='#6c7086', font=('Helvetica', 9)).pack(pady=(0, 12))

        # existing keys
        self.keys_frame = tk.Frame(self, bg=BG)
        self.keys_frame.pack(fill='x', padx=16)
        self._show_existing_keys()

        # separator
        tk.Frame(self, bg='#45475a', height=1).pack(fill='x', padx=16, pady=12)

        # add new key
        tk.Label(self, text="Add / Update Key", bg=BG, fg=FG,
            font=('Helvetica', 11, 'bold')).pack(anchor='w', padx=16)

        form = tk.Frame(self, bg=BG)
        form.pack(fill='x', padx=16, pady=8)

        tk.Label(form, text="Provider:", bg=BG, fg=FG).grid(row=0, column=0, sticky='w', pady=4)
        self.provider_var = tk.StringVar(value=PROVIDERS[0][0])
        prov_menu = ttk.Combobox(form, textvariable=self.provider_var,
            values=[p[0] for p in PROVIDERS], state='readonly', width=30)
        prov_menu.grid(row=0, column=1, padx=8, pady=4)

        tk.Label(form, text="Key / Host:", bg=BG, fg=FG).grid(row=1, column=0, sticky='w', pady=4)
        self.key_var = tk.StringVar()
        self.key_entry = tk.Entry(form, textvariable=self.key_var, bg=ENTRY_BG, fg=FG,
            show='*', width=32, relief='flat', bd=4)
        self.key_entry.grid(row=1, column=1, padx=8, pady=4)

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=8)

        tk.Button(btn_frame, text="Test Connection", bg='#a6e3a1', fg=BTN_FG,
            font=('Helvetica', 10, 'bold'), relief='flat', padx=12,
            command=self._test).pack(side='left', padx=4)

        tk.Button(btn_frame, text="Save Key", bg=BTN_BG, fg=BTN_FG,
            font=('Helvetica', 10, 'bold'), relief='flat', padx=12,
            command=self._save).pack(side='left', padx=4)

        self.status_label = tk.Label(self, text="", bg=BG, fg='#6c7086', wraplength=400)
        self.status_label.pack(pady=4)

    def _get_provider_code(self):
        name = self.provider_var.get()
        for n, c in PROVIDERS:
            if n == name: return c
        return "custom"

    def _show_existing_keys(self):
        for w in self.keys_frame.winfo_children(): w.destroy()
        keys = self.config_data.get("api_keys", {})
        if not keys:
            tk.Label(self.keys_frame, text="No API keys configured yet.", bg=BG, fg='#6c7086').pack()
            return
        for prov, val in keys.items():
            if prov == "ollama_host": continue
            f = tk.Frame(self.keys_frame, bg=BG)
            f.pack(fill='x', pady=1)
            tk.Label(f, text=f"  ✓ {prov}", bg=BG, fg='#a6e3a1',
                font=('Courier', 10)).pack(side='left')
            tk.Button(f, text="✕", bg='#f38ba8', fg='white', relief='flat',
                padx=4, command=lambda p=prov: self._remove(p)).pack(side='right')

    def _test(self):
        prov = self._get_provider_code()
        key = self.key_var.get().strip()
        if not key:
            self.status_label.config(text="Enter a key first", fg='#f38ba8')
            return
        self.status_label.config(text="Testing...", fg='#6c7086')
        self.update()
        ok, msg = api_client.test_connection(prov, key)
        if ok:
            self.status_label.config(text=f"✓ Connected: {msg}", fg='#a6e3a1')
        else:
            self.status_label.config(text=f"✕ Failed: {msg}", fg='#f38ba8')

    def _save(self):
        prov = self._get_provider_code()
        key = self.key_var.get().strip()
        if not key:
            self.status_label.config(text="Enter a key", fg='#f38ba8')
            return
        if prov == "ollama":
            self.config_data.setdefault("api_keys", {})["ollama_host"] = key
            cfg_mod.save(self.config_data)
        else:
            cfg_mod.store_api_key(self.config_data, prov, key)
        self.key_var.set("")
        self._show_existing_keys()
        self.status_label.config(text=f"✓ Saved key for {prov}", fg='#a6e3a1')

    def _remove(self, prov):
        cfg_mod.remove_api_key(self.config_data, prov)
        self._show_existing_keys()


class NewAgentDialog(tk.Toplevel):
    """Dialog for creating a new agent."""
    def __init__(self, parent, config, on_create=None):
        super().__init__(parent)
        self.title("SWYK — New Agent")
        self.geometry("450x500")
        self.configure(bg=BG)
        self.config_data = config
        self.on_create = on_create
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="Create New Agent", bg=BG, fg=FG,
            font=('Helvetica', 14, 'bold')).pack(pady=(16, 12))

        form = tk.Frame(self, bg=BG)
        form.pack(fill='x', padx=24)

        # Name
        tk.Label(form, text="Name:", bg=BG, fg=FG, font=('Helvetica', 10)).grid(row=0, column=0, sticky='w', pady=6)
        self.name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.name_var, bg=ENTRY_BG, fg=FG,
            relief='flat', bd=6, width=25).grid(row=0, column=1, padx=8, pady=6)

        # Role
        tk.Label(form, text="Role:", bg=BG, fg=FG, font=('Helvetica', 10)).grid(row=1, column=0, sticky='w', pady=6)
        self.role_var = tk.StringVar(value=ROLES[0])
        ttk.Combobox(form, textvariable=self.role_var, values=ROLES,
            width=23).grid(row=1, column=1, padx=8, pady=6)

        # Provider
        tk.Label(form, text="API Provider:", bg=BG, fg=FG, font=('Helvetica', 10)).grid(row=2, column=0, sticky='w', pady=6)
        avail_providers = list(self.config_data.get("api_keys", {}).keys())
        avail_providers = [p for p in avail_providers if p != "ollama_host"]
        if "ollama_host" in self.config_data.get("api_keys", {}):
            avail_providers.append("ollama")
        prov_names = avail_providers if avail_providers else ["(add API key first)"]
        self.prov_var = tk.StringVar(value=prov_names[0] if prov_names else "")
        ttk.Combobox(form, textvariable=self.prov_var, values=prov_names,
            width=23).grid(row=2, column=1, padx=8, pady=6)

        # Model
        tk.Label(form, text="Model:", bg=BG, fg=FG, font=('Helvetica', 10)).grid(row=3, column=0, sticky='w', pady=6)
        self.model_var = tk.StringVar(value="gemini-2.0-flash")
        tk.Entry(form, textvariable=self.model_var, bg=ENTRY_BG, fg=FG,
            relief='flat', bd=6, width=25).grid(row=3, column=1, padx=8, pady=6)

        # Color
        tk.Label(form, text="Appearance:", bg=BG, fg=FG, font=('Helvetica', 10)).grid(row=4, column=0, sticky='w', pady=6)
        self.color_var = tk.StringVar(value=COLORS[0])
        ttk.Combobox(form, textvariable=self.color_var, values=COLORS,
            state='readonly', width=23).grid(row=4, column=1, padx=8, pady=6)

        # System prompt
        tk.Label(form, text="System Prompt:", bg=BG, fg=FG, font=('Helvetica', 10)).grid(row=5, column=0, sticky='nw', pady=6)
        self.prompt_text = tk.Text(form, bg=ENTRY_BG, fg=FG, height=4, width=25,
            relief='flat', bd=6, wrap='word')
        self.prompt_text.grid(row=5, column=1, padx=8, pady=6)

        # buttons
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=16)

        tk.Button(btn_frame, text="Cancel", bg='#45475a', fg=FG,
            relief='flat', padx=16, pady=4, command=self.destroy).pack(side='left', padx=8)

        tk.Button(btn_frame, text="Create Agent", bg=BTN_BG, fg=BTN_FG,
            font=('Helvetica', 11, 'bold'), relief='flat', padx=16, pady=4,
            command=self._create).pack(side='left', padx=8)

    def _create(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Agent name is required", parent=self)
            return
        role = self.role_var.get()
        provider = self.prov_var.get()
        if provider.startswith("("):
            messagebox.showwarning("Missing", "Add an API key first", parent=self)
            return
        model = self.model_var.get().strip()
        color_idx = COLORS.index(self.color_var.get()) if self.color_var.get() in COLORS else 0
        prompt = self.prompt_text.get("1.0", "end").strip()

        agent = cfg_mod.add_agent(self.config_data, name, role, provider, model, color_idx, prompt)

        if self.on_create:
            self.on_create(agent)
        self.destroy()


class SettingsDialog(tk.Toplevel):
    """General settings dialog."""
    def __init__(self, parent, config):
        super().__init__(parent)
        self.title("SWYK — Settings")
        self.geometry("400x350")
        self.configure(bg=BG)
        self.config_data = config
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="Settings", bg=BG, fg=FG,
            font=('Helvetica', 14, 'bold')).pack(pady=(16, 12))

        s = config.get("settings", {})

        form = tk.Frame(self, bg=BG)
        form.pack(fill='x', padx=24)

        # Max file size
        tk.Label(form, text="Max file size (MB):", bg=BG, fg=FG).grid(row=0, column=0, sticky='w', pady=6)
        self.maxfile_var = tk.StringVar(value=str(s.get("max_file_size_mb", 10)))
        tk.Entry(form, textvariable=self.maxfile_var, bg=ENTRY_BG, fg=FG,
            width=10, relief='flat', bd=4).grid(row=0, column=1, pady=6)

        # Allow shell
        self.shell_var = tk.BooleanVar(value=s.get("allow_shell", False))
        tk.Checkbutton(form, text="Allow shell commands", variable=self.shell_var,
            bg=BG, fg=FG, selectcolor=ENTRY_BG, activebackground=BG,
            activeforeground=FG).grid(row=1, column=0, columnspan=2, sticky='w', pady=6)

        # Auto approve reads
        self.reads_var = tk.BooleanVar(value=s.get("auto_approve_reads", True))
        tk.Checkbutton(form, text="Auto-approve read operations", variable=self.reads_var,
            bg=BG, fg=FG, selectcolor=ENTRY_BG, activebackground=BG,
            activeforeground=FG).grid(row=2, column=0, columnspan=2, sticky='w', pady=6)

        # Audit log
        self.audit_var = tk.BooleanVar(value=s.get("audit_log", True))
        tk.Checkbutton(form, text="Enable audit log", variable=self.audit_var,
            bg=BG, fg=FG, selectcolor=ENTRY_BG, activebackground=BG,
            activeforeground=FG).grid(row=3, column=0, columnspan=2, sticky='w', pady=6)

        # save button
        tk.Button(self, text="Save Settings", bg=BTN_BG, fg=BTN_FG,
            font=('Helvetica', 11, 'bold'), relief='flat', padx=16, pady=4,
            command=self._save).pack(pady=16)

    def _save(self):
        try: mf = int(self.maxfile_var.get())
        except: mf = 10
        self.config_data["settings"] = {
            "max_file_size_mb": mf,
            "allow_shell": self.shell_var.get(),
            "auto_approve_reads": self.reads_var.get(),
            "audit_log": self.audit_var.get(),
        }
        cfg_mod.save(self.config_data)
        messagebox.showinfo("Saved", "Settings updated", parent=self)
        self.destroy()
