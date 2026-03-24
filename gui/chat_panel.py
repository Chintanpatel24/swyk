"""Chat panel — conversation with selected agent."""
import tkinter as tk
import tkinter.scrolledtext as st

class ChatPanel(tk.Frame):
    def __init__(self, parent, agent_runner, config, **kw):
        super().__init__(parent, bg='#1e1e2e', **kw)
        self.runner = agent_runner
        self.config = config
        self.selected_agent_id = None
        self.workspace = ""

        # header
        self.header = tk.Label(self, text="Select an agent to chat",
            bg='#1e1e2e', fg='#cdd6f4', font=('Helvetica', 11, 'bold'),
            anchor='w', padx=8, pady=4)
        self.header.pack(fill='x')

        # agent selector frame
        self.selector_frame = tk.Frame(self, bg='#1e1e2e')
        self.selector_frame.pack(fill='x', padx=4, pady=2)
        self.agent_buttons = []

        # chat display
        self.chat_display = st.ScrolledText(self, wrap='word',
            bg='#11111b', fg='#cdd6f4', font=('Consolas', 10),
            insertbackground='#cdd6f4', relief='flat', padx=8, pady=8,
            state='disabled', height=20)
        self.chat_display.pack(fill='both', expand=True, padx=4, pady=4)

        # configure tags
        self.chat_display.tag_configure('user', foreground='#89b4fa', font=('Consolas', 10, 'bold'))
        self.chat_display.tag_configure('agent', foreground='#a6e3a1', font=('Consolas', 10))
        self.chat_display.tag_configure('system', foreground='#6c7086', font=('Consolas', 9, 'italic'))
        self.chat_display.tag_configure('error', foreground='#f38ba8')
        self.chat_display.tag_configure('time', foreground='#585b70', font=('Consolas', 8))

        # input frame
        input_frame = tk.Frame(self, bg='#1e1e2e')
        input_frame.pack(fill='x', padx=4, pady=(0, 8))

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(input_frame, textvariable=self.input_var,
            bg='#313244', fg='#cdd6f4', font=('Consolas', 11),
            insertbackground='#cdd6f4', relief='flat', bd=8)
        self.input_entry.pack(fill='x', side='left', expand=True)
        self.input_entry.bind('<Return>', self._on_send)

        self.send_btn = tk.Button(input_frame, text="Send", bg='#89b4fa',
            fg='#1e1e2e', font=('Helvetica', 10, 'bold'), relief='flat',
            padx=12, command=self._on_send)
        self.send_btn.pack(side='right', padx=(4, 0))

        # listen for runner updates
        self.runner.on_change(self._on_agent_update)

    def set_workspace(self, ws):
        self.workspace = ws

    def refresh_agent_list(self):
        """Rebuild agent selector buttons."""
        for b in self.agent_buttons:
            b.destroy()
        self.agent_buttons.clear()

        agents = self.config.get("agents", [])
        for agent in agents:
            aid = agent["id"]
            ci = agent.get("color_idx", 0) % len([
                '#4a90d9','#e74c3c','#2ecc71','#f39c12','#9b59b6','#1abc9c','#e67e22','#3498db'
            ])
            color = ['#4a90d9','#e74c3c','#2ecc71','#f39c12','#9b59b6','#1abc9c','#e67e22','#3498db'][ci]
            btn = tk.Button(self.selector_frame, text=agent["name"][:10],
                bg=color, fg='white', font=('Helvetica', 9, 'bold'),
                relief='flat', padx=6, pady=2,
                command=lambda a=aid: self._select_agent(a))
            btn.pack(side='left', padx=2)
            self.agent_buttons.append(btn)

    def _select_agent(self, agent_id):
        self.selected_agent_id = agent_id
        agent = None
        for a in self.config.get("agents", []):
            if a["id"] == agent_id: agent = a; break
        if agent:
            self.header.config(text=f"Chat with {agent['name']} ({agent['role']})")
        self._reload_chat()

    def _reload_chat(self):
        """Load conversation history into display."""
        self.chat_display.config(state='normal')
        self.chat_display.delete('1.0', 'end')

        if not self.selected_agent_id:
            self.chat_display.insert('end', 'Select an agent to start chatting.\n', 'system')
            self.chat_display.config(state='disabled')
            return

        conv = self.runner.get_conversation(self.selected_agent_id)
        for msg in conv[-50:]:
            t = msg.get("time", "")
            if msg["role"] == "user":
                self.chat_display.insert('end', f'[{t}] You: ', 'time')
                self.chat_display.insert('end', msg["content"] + '\n', 'user')
            else:
                tag = 'error' if msg["content"].startswith("[Error") else 'agent'
                self.chat_display.insert('end', f'[{t}] Agent: ', 'time')
                self.chat_display.insert('end', msg["content"] + '\n', tag)
            self.chat_display.insert('end', '\n')

        self.chat_display.config(state='disabled')
        self.chat_display.see('end')

    def _on_send(self, event=None):
        text = self.input_var.get().strip()
        if not text or not self.selected_agent_id:
            return
        self.input_var.set("")

        # show user message immediately
        self.chat_display.config(state='normal')
        import time
        t = time.strftime("%H:%M")
        self.chat_display.insert('end', f'[{t}] You: ', 'time')
        self.chat_display.insert('end', text + '\n\n', 'user')
        self.chat_display.config(state='disabled')
        self.chat_display.see('end')

        # send to agent
        self.runner.send_message(self.selected_agent_id, text, self.workspace)

    def _on_agent_update(self):
        """Called from background thread when agent state changes."""
        try:
            self.after(50, self._reload_chat)
        except: pass
