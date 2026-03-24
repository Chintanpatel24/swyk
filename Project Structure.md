<pre>

 swik/
├── install.sh                      # one-liner curl installer
├── uninstall.sh                    # clean removal
├── bin/
│   └── swik                        # launcher (bash)
├── core/
│   ├── __init__.py
│   ├── main.py                     # entry-point
│   ├── agent.py                    # reasoning loop
│   ├── llm_client.py              # Ollama / open-model HTTP client
│   ├── tools.py                    # every tool the agent can call
│   ├── sandbox.py                  # path-jail + symlink guard
│   ├── permissions.py              # y / n gate for every write
│   ├── config.py                   # ~/.swik/config.json
│   ├── ui.py                       # colours, spinners, banners
│   └── logger.py                   # append-only audit log
├── sandbox-executor/               # optional Rust hardened executor
│   ├── Cargo.toml
│   └── src/
│       └── main.rs
├── README.md
└── LICENSE                         # MIT 
  
</pre>
