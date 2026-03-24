"""
Filesystem sandbox — pure Python path jail.

Every path is resolved to real absolute form and verified to
live inside the workspace root. Symlink escapes, '..' traversal,
and writes to sensitive files are all blocked.
"""

import os
import shutil
import stat as stat_mod


class SandboxError(Exception):
    """Raised when an operation violates the sandbox boundary."""


class Sandbox:
    SENSITIVE = frozenset({
        ".env", ".env.local", ".env.production", ".env.staging",
        ".npmrc", ".pypirc", "id_rsa", "id_ed25519",
    })

    def __init__(self, root, max_file_size_mb=10):
        real = os.path.realpath(os.path.abspath(root))
        if not os.path.isdir(real):
            raise SandboxError("Not a directory: {}".format(real))
        self.root = real
        self.max_bytes = max_file_size_mb * 1024 * 1024

    # --- path resolution ---

    def resolve(self, user_path):
        """Resolve user_path to an absolute real path inside the sandbox."""
        if os.path.isabs(user_path):
            candidate = user_path
        else:
            candidate = os.path.join(self.root, user_path)

        # for existing paths resolve fully
        if os.path.exists(candidate):
            resolved = os.path.realpath(candidate)
        else:
            # for new paths resolve the parent
            parent = os.path.dirname(candidate)
            if os.path.exists(parent):
                parent = os.path.realpath(parent)
            else:
                parent = os.path.realpath(parent)
            resolved = os.path.join(parent, os.path.basename(candidate))

        resolved = os.path.normpath(resolved)

        if not self._inside(resolved):
            raise SandboxError("Path escapes workspace: {} -> {}".format(user_path, resolved))

        return resolved

    def _inside(self, path):
        # path must equal root or be under root/
        return path == self.root or path.startswith(self.root + os.sep)

    def _relpath(self, abspath):
        return os.path.relpath(abspath, self.root)

    # --- guards ---

    def _guard_read(self, path):
        if not os.path.exists(path):
            raise SandboxError("Does not exist: {}".format(self._relpath(path)))
        if os.path.isfile(path):
            size = os.path.getsize(path)
            if size > self.max_bytes:
                raise SandboxError("File too large: {:.1f}MB (limit {}MB)".format(
                    size / 1048576, self.max_bytes // 1048576))

    def _guard_write(self, path):
        basename = os.path.basename(path)
        if basename in self.SENSITIVE:
            raise SandboxError("Write to sensitive file blocked: {}".format(basename))

    def _guard_delete(self, path):
        self._guard_write(path)
        if os.path.realpath(path) == self.root:
            raise SandboxError("Cannot delete workspace root")

    # --- operations ---

    def list_dir(self, rel="."):
        target = self.resolve(rel)
        self._guard_read(target)
        if not os.path.isdir(target):
            raise SandboxError("Not a directory: {}".format(rel))
        entries = []
        for name in sorted(os.listdir(target)):
            full = os.path.join(target, name)
            if os.path.isdir(full):
                entries.append(name + "/")
            else:
                entries.append(name)
        return entries

    def walk(self, rel=".", max_files=500):
        target = self.resolve(rel)
        self._guard_read(target)
        results = []
        for dirpath, dirnames, filenames in os.walk(target):
            # skip hidden VCS dirs
            dirnames[:] = [d for d in sorted(dirnames) if d not in (".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv", "venv")]
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                results.append(os.path.relpath(full, self.root))
                if len(results) >= max_files:
                    return results
        return results

    def read_file(self, rel):
        path = self.resolve(rel)
        self._guard_read(path)
        if not os.path.isfile(path):
            raise SandboxError("Not a file: {}".format(rel))
        with open(path, "r", errors="replace") as f:
            return f.read()

    def write_file(self, rel, content):
        path = self.resolve(rel)
        self._guard_write(path)
        parent = os.path.dirname(path)
        if not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return "Wrote {} bytes -> {}".format(len(content), self._relpath(path))

    def append_file(self, rel, content):
        path = self.resolve(rel)
        self._guard_write(path)
        with open(path, "a") as f:
            f.write(content)
        return "Appended {} bytes -> {}".format(len(content), self._relpath(path))

    def move_file(self, src_rel, dst_rel):
        src = self.resolve(src_rel)
        dst = self.resolve(dst_rel)
        self._guard_read(src)
        self._guard_write(dst)
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))
            if not self._inside(dst):
                raise SandboxError("Destination escapes workspace")
        parent = os.path.dirname(dst)
        if not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        os.rename(src, dst)
        return "Moved {} -> {}".format(self._relpath(src), self._relpath(dst))

    def copy_file(self, src_rel, dst_rel):
        src = self.resolve(src_rel)
        dst = self.resolve(dst_rel)
        self._guard_read(src)
        self._guard_write(dst)
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))
        parent = os.path.dirname(dst)
        if not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        return "Copied -> {}".format(self._relpath(dst))

    def delete(self, rel):
        path = self.resolve(rel)
        self._guard_delete(path)
        if not os.path.exists(path):
            raise SandboxError("Does not exist: {}".format(rel))
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return "Deleted {}".format(self._relpath(path))

    def mkdir(self, rel):
        path = self.resolve(rel)
        self._guard_write(path)
        os.makedirs(path, exist_ok=True)
        return "Created directory {}".format(self._relpath(path))

    def file_info(self, rel):
        path = self.resolve(rel)
        self._guard_read(path)
        st = os.stat(path)
        return {
            "name": os.path.basename(path),
            "path": self._relpath(path),
            "size": st.st_size,
            "is_dir": os.path.isdir(path),
            "permissions": stat_mod.filemode(st.st_mode),
            "modified": st.st_mtime,
        }

    def search_content(self, query, rel="."):
        target = self.resolve(rel)
        results = []
        q = query.lower()
        for fpath in self.walk(rel, max_files=300):
            full = os.path.join(self.root, fpath)
            if not os.path.isfile(full):
                continue
            try:
                with open(full, "r", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if q in line.lower():
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

    def search_files(self, pattern):
        import fnmatch
        all_files = self.walk(".", max_files=1000)
        return [f for f in all_files if fnmatch.fnmatch(os.path.basename(f).lower(), pattern.lower())
                or fnmatch.fnmatch(f.lower(), pattern.lower())]
