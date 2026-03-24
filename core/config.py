"""Persistent config stored at ~/.config/swyk/config.json"""
import json, os, base64, time, uuid

DIR = os.path.join(os.path.expanduser("~"), ".config", "swyk")
CONF = os.path.join(DIR, "config.json")
CONV_DIR = os.path.join(DIR, "conversations")

def _ensure():
    os.makedirs(DIR, exist_ok=True)
    os.makedirs(CONV_DIR, exist_ok=True)

def _default():
    return {
        "api_keys": {},
        "agents": [],
        "settings": {
            "max_file_size_mb": 10,
            "allow_shell": False,
            "auto_approve_reads": True,
            "audit_log": True,
            "theme": "dark"
        }
    }

def load():
    _ensure()
    if os.path.isfile(CONF):
        try:
            with open(CONF) as f: return json.load(f)
        except: pass
    return _default()

def save(cfg):
    _ensure()
    with open(CONF, "w") as f: json.dump(cfg, f, indent=2)

# --- API key helpers (base64 obfuscation) ---
def store_api_key(cfg, provider, key):
    cfg.setdefault("api_keys", {})
    cfg["api_keys"][provider] = base64.b64encode(key.encode()).decode()
    save(cfg)

def get_api_key(cfg, provider):
    raw = cfg.get("api_keys", {}).get(provider, "")
    if not raw: return ""
    try: return base64.b64decode(raw.encode()).decode()
    except: return ""

def remove_api_key(cfg, provider):
    cfg.get("api_keys", {}).pop(provider, None)
    save(cfg)

# --- Agent CRUD ---
def add_agent(cfg, name, role, provider, model, color_idx=0, system_prompt=""):
    agent = {
        "id": "agent_" + uuid.uuid4().hex[:8],
        "name": name,
        "role": role,
        "provider": provider,
        "model": model,
        "color_idx": color_idx,
        "system_prompt": system_prompt or f"You are {name}, a helpful {role} assistant.",
        "desk": len(cfg.get("agents", [])),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    cfg.setdefault("agents", []).append(agent)
    save(cfg)
    return agent

def remove_agent(cfg, agent_id):
    cfg["agents"] = [a for a in cfg.get("agents", []) if a["id"] != agent_id]
    save(cfg)
    conv = os.path.join(CONV_DIR, agent_id + ".json")
    if os.path.exists(conv): os.remove(conv)

def get_agents(cfg):
    return cfg.get("agents", [])

# --- Conversation persistence ---
def load_conversation(agent_id):
    p = os.path.join(CONV_DIR, agent_id + ".json")
    if os.path.isfile(p):
        try:
            with open(p) as f: return json.load(f).get("messages", [])
        except: pass
    return []

def save_conversation(agent_id, messages):
    _ensure()
    p = os.path.join(CONV_DIR, agent_id + ".json")
    with open(p, "w") as f:
        json.dump({"messages": messages[-200:]}, f)
