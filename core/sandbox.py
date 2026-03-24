"""
Filesystem sandbox.

Rules
─────
1.  Every path is resolved to an absolute real-path *before* any I/O.
2.  The real-path must start with the sandbox root.
3.  Symlinks that escape the sandbox are blocked.
4.  Files above max_file_size_mb are refused.
5.  Hidden config files (.env, .git/config, etc.) are readable but
    not writable unless explicitly unlocked.

This module never calls os.system / subprocess.  Shell execution
is handled separately in tools.py with its own gate.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import List, Optional


class SandboxError(Exception):
    """Raised when an operation violates the sandbox."""


class Sandbox:
    """Jails all file operations to *root* and its descendants."""

    # files that may contain secrets — block writes by default
    SENSITIVE_NAMES = frozenset({
        ".env", ".env.local", ".env.production",
        ".git/config", ".npmrc", ".pypirc",
        "id_rsa", "id_ed25519", ".ssh",
    })

    def __init__(self, root: str, max_file_size_mb: int = 10):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise SandboxError(f"Sandbox root is not a directory: {self.root}")
        self.max_bytes = max_file_size_mb * 1024 * 1024

    # ── path validation ───────────────────────────────────────

    def resolve(self, user_path: str) -> Path:
        """
        Resolve *user_path* (may be relative) to an absolute path
        that is guaranteed to live inside the sandbox.
        Raises SandboxError on escape attempts.
        """
        # join with root if relative
        candidate = Path(user_path)
        if not candidate.is_absolute():
            candidate = self.root / candidate

        # resolve symlinks, "..", etc.
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            # for new files the parent must exist & be inside sandbox
            parent = candidate.parent.resolve()
            if not self._inside(parent):
                raise SandboxError(
                    f"Path escapes sandbox: {user_path}"
                ) from exc
            resolved = parent / candidate.name

        if not self._inside(resolved):
            raise SandboxError(f"Path escapes sandbox: {user_path} → {resolved}")

        return resolved

    def _inside(self, path: Path) -> bool:
        """True if *path* is the root or a child of it."""
        try:
            path.relative_to(self.root)
            return True
        except ValueError:
            return False

    # ── guards ────────────────────────────────────────────────

    def guard_read(self, path: Path) -> None:
        if not path.exists():
            raise SandboxError(f"File does not exist: {path}")
        if path.is_file() and path.stat().st_size > self.max_bytes:
            mb = path.stat().st_size / (1024 * 1024)
            raise SandboxError(
                f"File too large ({mb:.1f} MB > {self.max_bytes // (1024*1024)} MB limit)"
            )

    def guard_write(self, path: Path) -> None:
        # block writes to sensitive files
        rel = str(path.relative_to(self.root))
        for s in self.SENSITIVE_NAMES:
            if rel == s or rel.endswith(f"/{s}"):
                raise SandboxError(
                    f"Write to sensitive file blocked: {rel}  "
                    f"(unlock with /config allow_sensitive_write)"
                )

    def guard_delete(self, path: Path) -> None:
        self.guard_write(path)
        if path == self.root:
            raise SandboxError("Cannot delete the sandbox root.")

    # ── high-level queries ────────────────────────────────────

    def list_dir(self, rel: str = ".") -> List[str]:
        target = self.resolve(rel)
        self.guard_read(target)
        if not target.is_dir():
            raise SandboxError(f"Not a directory: {target}")
        entries = []
        for child in sorted(target.iterdir()):
            name = child.name
            if child.is_dir():
                name += "/"
            entries.append(name)
        return entries

    def walk(self, rel: str = ".", max_files: int = 500) -> List[str]:
        """Return a flat list of relative paths under *rel*."""
        target = self.resolve(rel)
        self.guard_read(target)
        results: List[str] = []
        for dirpath, dirnames, filenames in os.walk(target):
            # skip hidden version-control dirs
            dirnames[:] = [d for d in dirnames if not d.startswith(".git")]
            for fn in filenames:
                full = Path(dirpath) / fn
                results.append(str(full.relative_to(self.root)))
                if len(results) >= max_files:
                    return results
        return results

    def read_file(self, rel: str) -> str:
        path = self.resolve(rel)
        self.guard_read(path)
        with open(path, "r", errors="replace") as f:
            return f.read()

    def write_file(self, rel: str, content: str) -> str:
        path = self.resolve(rel)
        self.guard_write(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Wrote {len(content)} bytes → {path.relative_to(self.root)}"

    def move_file(self, src_rel: str, dst_rel: str) -> str:
        src = self.resolve(src_rel)
        dst = self.resolve(dst_rel)
        self.guard_read(src)
        self.guard_write(dst)
        if dst.is_dir():
            dst = dst / src.name
            if not self._inside(dst):
                raise SandboxError("Destination escapes sandbox after join.")
        src.rename(dst)
        return f"Moved {src.relative_to(self.root)} → {dst.relative_to(self.root)}"

    def copy_file(self, src_rel: str, dst_rel: str) -> str:
        import shutil
        src = self.resolve(src_rel)
        dst = self.resolve(dst_rel)
        self.guard_read(src)
        self.guard_write(dst)
        if dst.is_dir():
            dst = dst / src.name
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))
        return f"Copied → {dst.relative_to(self.root)}"

    def delete_file(self, rel: str) -> str:
        import shutil
        path = self.resolve(rel)
        self.guard_delete(path)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        return f"Deleted {path.relative_to(self.root)}"

    def mkdir(self, rel: str) -> str:
        path = self.resolve(rel)
        self.guard_write(path)
        path.mkdir(parents=True, exist_ok=True)
        return f"Created directory {path.relative_to(self.root)}"

    def file_info(self, rel: str) -> dict:
        path = self.resolve(rel)
        self.guard_read(path)
        st = path.stat()
        return {
            "name": path.name,
            "path": str(path.relative_to(self.root)),
            "size": st.st_size,
            "is_dir": path.is_dir(),
            "permissions": stat.filemode(st.st_mode),
            "modified": st.st_mtime,
        }

    def search_content(self, query: str, rel: str = ".") -> List[dict]:
        """Grep-like search across files."""
        target = self.resolve(rel)
        results = []
        for fpath in self.walk(rel, max_files=200):
            full = self.root / fpath
            if not full.is_file():
                continue
            try:
                with open(full, "r", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if query.lower() in line.lower():
                            results.append({
                                "file": fpath,
                                "line": i,
                                "text": line.rstrip()[:200],
                            })
                            if len(results) >= 50:
                                return results
            except (OSError, UnicodeDecodeError):
                continue
        return results

    def search_files(self, pattern: str) -> List[str]:
        """Glob search."""
        import fnmatch
        all_files = self.walk(".", max_files=1000)
        return [f for f in all_files if fnmatch.fnmatch(f.lower(), pattern.lower())]
