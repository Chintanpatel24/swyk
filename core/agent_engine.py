"""Agent task runner — executes agent work in background threads."""
import threading, time, json, re
from core import config as cfg_mod
from core import api_client

class AgentState:
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    ERROR = "error"

class AgentRunner:
    """Manages all agents and their background tasks."""
    def __init__(self, config):
        self.config = config
        self.states = {}       # agent_id -> AgentState
        self.status_text = {}  # agent_id -> short status string
        self.conversations = {}# agent_id -> list of messages
        self._callbacks = []   # (fn) called on state change
        self._lock = threading.Lock()

    def on_change(self, fn):
        self._callbacks.append(fn)

    def _notify(self):
        for fn in self._callbacks:
            try: fn()
            except: pass

    def get_state(self, agent_id):
        return self.states.get(agent_id, AgentState.IDLE)

    def get_status(self, agent_id):
        return self.status_text.get(agent_id, "Idle")

    def get_conversation(self, agent_id):
        if agent_id not in self.conversations:
            self.conversations[agent_id] = cfg_mod.load_conversation(agent_id)
        return self.conversations[agent_id]

    def send_message(self, agent_id, user_text, workspace=""):
        """Send message to agent. Runs API call in background."""
        agent = None
        for a in cfg_mod.get_agents(self.config):
            if a["id"] == agent_id:
                agent = a; break
        if not agent: return

        conv = self.get_conversation(agent_id)
        conv.append({"role": "user", "content": user_text, "time": time.strftime("%H:%M")})

        self.states[agent_id] = AgentState.THINKING
        self.status_text[agent_id] = "Thinking..."
        self._notify()

        t = threading.Thread(target=self._run, args=(agent, conv, workspace), daemon=True)
        t.start()

    def _run(self, agent, conv, workspace):
        aid = agent["id"]
        try:
            provider = agent["provider"]
            key = cfg_mod.get_api_key(self.config, provider)
            if not key and provider != "ollama":
                raise api_client.LLMError(f"No API key for {provider}")

            host_or_key = key if provider != "ollama" else (
                self.config.get("api_keys", {}).get("ollama_host", "http://127.0.0.1:11434")
            )

            # build messages with system prompt
            sys_prompt = agent.get("system_prompt", f"You are {agent['name']}.")
            if workspace:
                sys_prompt += f"\n\nYou are working in directory: {workspace}"
            sys_prompt += "\n\nBe concise and helpful. When you need to perform file operations, describe what you want to do and I'll handle it."

            messages = [{"role": "system", "content": sys_prompt}]
            # add last N messages
            for m in conv[-30:]:
                messages.append({"role": m["role"], "content": m["content"]})

            self.states[aid] = AgentState.WORKING
            self.status_text[aid] = "Working..."
            self._notify()

            response = api_client.chat(provider, host_or_key, agent["model"], messages)

            with self._lock:
                conv.append({"role": "assistant", "content": response, "time": time.strftime("%H:%M")})
                cfg_mod.save_conversation(aid, conv)
                self.states[aid] = AgentState.IDLE
                self.status_text[aid] = "Done"
                self._notify()

        except Exception as e:
            with self._lock:
                conv.append({"role": "assistant", "content": f"[Error: {e}]", "time": time.strftime("%H:%M")})
                self.states[aid] = AgentState.ERROR
                self.status_text[aid] = f"Error"
                self._notify()
