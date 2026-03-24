"""Filesystem sandbox — path jail. Pure stdlib."""
import os, shutil, stat as smod, fnmatch

class SandboxError(Exception): pass

class Sandbox:
    SENSITIVE = frozenset({".env",".env.local",".env.production",".npmrc",".pypirc","id_rsa","id_ed25519"})

    def __init__(self, root, max_mb=10):
        self.root = os.path.realpath(os.path.abspath(root))
        if not os.path.isdir(self.root): raise SandboxError(f"Not a dir: {self.root}")
        self.max_bytes = max_mb * 1048576

    def resolve(self, p):
        c = p if os.path.isabs(p) else os.path.join(self.root, p)
        r = os.path.realpath(c) if os.path.exists(c) else os.path.join(os.path.realpath(os.path.dirname(c)), os.path.basename(c))
        r = os.path.normpath(r)
        if r != self.root and not r.startswith(self.root + os.sep):
            raise SandboxError(f"Escapes sandbox: {p}")
        return r

    def list_dir(self, rel="."):
        t = self.resolve(rel)
        return sorted(n+("/" if os.path.isdir(os.path.join(t,n)) else "") for n in os.listdir(t))

    def walk(self, rel=".", mx=500):
        t = self.resolve(rel)
        out = []
        skip = {".git",".svn","__pycache__","node_modules",".venv","venv"}
        for dp, dn, fn in os.walk(t):
            dn[:] = [d for d in sorted(dn) if d not in skip]
            for f in sorted(fn):
                out.append(os.path.relpath(os.path.join(dp,f), self.root))
                if len(out)>=mx: return out
        return out

    def read_file(self, rel):
        p = self.resolve(rel)
        if os.path.getsize(p)>self.max_bytes: raise SandboxError("File too large")
        with open(p,"r",errors="replace") as f: return f.read()

    def write_file(self, rel, content):
        p = self.resolve(rel)
        if os.path.basename(p) in self.SENSITIVE: raise SandboxError("Sensitive file")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p,"w") as f: f.write(content)
        return f"Wrote {len(content)}B -> {os.path.relpath(p,self.root)}"

    def move(self, s, d):
        sp,dp = self.resolve(s), self.resolve(d)
        if os.path.isdir(dp): dp = os.path.join(dp, os.path.basename(sp))
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        os.rename(sp, dp)
        return f"Moved -> {os.path.relpath(dp,self.root)}"

    def copy(self, s, d):
        sp,dp = self.resolve(s), self.resolve(d)
        if os.path.isdir(dp): dp = os.path.join(dp, os.path.basename(sp))
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        (shutil.copytree if os.path.isdir(sp) else shutil.copy2)(sp, dp)
        return f"Copied -> {os.path.relpath(dp,self.root)}"

    def delete(self, rel):
        p = self.resolve(rel)
        if p == self.root: raise SandboxError("Cannot delete root")
        (shutil.rmtree if os.path.isdir(p) else os.remove)(p)
        return f"Deleted {os.path.relpath(p,self.root)}"

    def mkdir(self, rel):
        p = self.resolve(rel)
        os.makedirs(p, exist_ok=True)
        return f"Created {os.path.relpath(p,self.root)}"

    def search(self, q, rel="."):
        results = []
        for fp in self.walk(rel, 300):
            full = os.path.join(self.root, fp)
            try:
                with open(full,"r",errors="replace") as f:
                    for i,ln in enumerate(f,1):
                        if q.lower() in ln.lower():
                            results.append(f"{fp}:{i}: {ln.rstrip()[:200]}")
                            if len(results)>=50: return results
            except: pass
        return results

    def find(self, pat):
        return [f for f in self.walk(".",1000)
                if fnmatch.fnmatch(os.path.basename(f).lower(), pat.lower())]
