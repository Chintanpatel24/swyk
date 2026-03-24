"""Multi-provider LLM client — pure urllib, zero dependencies."""
import json, urllib.request, urllib.error

class LLMError(Exception): pass

def chat(provider, host_or_key, model, messages, temperature=0.4):
    """Route to correct provider. Returns response text."""
    p = provider.lower()
    if p in ("google", "google_ai", "gemini"):
        return _google(host_or_key, model, messages, temperature)
    elif p in ("openai", "openai_compatible"):
        return _openai(host_or_key, model, messages, temperature)
    elif p == "ollama":
        return _ollama(host_or_key, model, messages, temperature)
    elif p in ("anthropic", "claude"):
        return _anthropic(host_or_key, model, messages, temperature)
    else:
        # treat as openai-compatible with host_or_key as base URL
        return _openai_custom(host_or_key, model, messages, temperature)

def _post(url, data, headers=None, timeout=180):
    h = {"Content-Type": "application/json"}
    if headers: h.update(headers)
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        raise LLMError(f"HTTP {e.code}: {err_body[:500]}")
    except urllib.error.URLError as e:
        raise LLMError(f"Connection failed: {e}")
    except Exception as e:
        raise LLMError(str(e))

# --- Google AI Studio (Gemini) ---
def _google(api_key, model, messages, temp):
    model = model or "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    contents = []
    for m in messages:
        role = "user" if m["role"] in ("user","system") else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    data = {
        "contents": contents,
        "generationConfig": {"temperature": temp, "maxOutputTokens": 4096}
    }
    resp = _post(url, data)
    try:
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise LLMError(f"Unexpected response: {json.dumps(resp)[:300]}")

# --- OpenAI ---
def _openai(api_key, model, messages, temp):
    model = model or "gpt-4o-mini"
    url = "https://api.openai.com/v1/chat/completions"
    data = {"model": model, "messages": messages, "temperature": temp, "max_tokens": 4096}
    resp = _post(url, data, {"Authorization": f"Bearer {api_key}"})
    try: return resp["choices"][0]["message"]["content"]
    except (KeyError, IndexError): raise LLMError(f"Unexpected: {json.dumps(resp)[:300]}")

# --- OpenAI compatible (custom host) ---
def _openai_custom(host, model, messages, temp):
    url = host.rstrip("/") + "/v1/chat/completions"
    data = {"model": model or "default", "messages": messages, "temperature": temp}
    resp = _post(url, data)
    try: return resp["choices"][0]["message"]["content"]
    except: raise LLMError(f"Unexpected: {json.dumps(resp)[:300]}")

# --- Ollama ---
def _ollama(host, model, messages, temp):
    host = host or "http://127.0.0.1:11434"
    url = host.rstrip("/") + "/api/chat"
    data = {"model": model or "mistral", "messages": messages, "stream": False,
            "options": {"temperature": temp}}
    resp = _post(url, data)
    return resp.get("message", {}).get("content", "")

# --- Anthropic ---
def _anthropic(api_key, model, messages, temp):
    model = model or "claude-sonnet-4-20250514"
    url = "https://api.anthropic.com/v1/messages"
    # separate system from messages
    system = ""
    msgs = []
    for m in messages:
        if m["role"] == "system": system += m["content"] + "\n"
        else: msgs.append({"role": m["role"], "content": m["content"]})
    if not msgs: msgs = [{"role": "user", "content": "Hello"}]
    data = {"model": model, "max_tokens": 4096, "temperature": temp, "messages": msgs}
    if system: data["system"] = system.strip()
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    resp = _post(url, data, headers)
    try: return resp["content"][0]["text"]
    except: raise LLMError(f"Unexpected: {json.dumps(resp)[:300]}")

def test_connection(provider, key_or_host, model=""):
    """Quick test. Returns (ok, message)."""
    try:
        msgs = [{"role": "user", "content": "Say 'hello' in one word."}]
        r = chat(provider, key_or_host, model, msgs)
        return True, f"OK: {r[:60]}"
    except LLMError as e:
        return False, str(e)[:200]
    except Exception as e:
        return False, str(e)[:200]
