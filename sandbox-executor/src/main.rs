//! SWIK Sandbox Executor
//!
//! A hardened file-operation executor that communicates via
//! stdin/stdout JSON.  The Python agent delegates dangerous
//! operations here for an extra layer of defence.
//!
//! Security features:
//!   • chdir + real-path validation
//!   • refuses any path outside the sandbox
//!   • drops supplementary groups (Linux)
//!   • logs every operation to stderr

use serde::{Deserialize, Serialize};
use std::env;
use std::fs;
use std::io::{self, BufRead, Write};
use std::path::{Path, PathBuf};

// ── protocol ─────────────────────────────────────────────────

#[derive(Deserialize, Debug)]
struct Request {
    action: String,
    params: serde_json::Value,
}

#[derive(Serialize)]
struct Response {
    ok: bool,
    result: String,
}

// ── sandbox ──────────────────────────────────────────────────

struct Sandbox {
    root: PathBuf,
}

impl Sandbox {
    fn new(root: &str) -> Result<Self, String> {
        let root = fs::canonicalize(root)
            .map_err(|e| format!("Cannot resolve sandbox root: {e}"))?;
        if !root.is_dir() {
            return Err(format!("{} is not a directory", root.display()));
        }
        Ok(Self { root })
    }

    /// Resolve and validate a user-supplied path.
    fn resolve(&self, user_path: &str) -> Result<PathBuf, String> {
        let candidate = if Path::new(user_path).is_absolute() {
            PathBuf::from(user_path)
        } else {
            self.root.join(user_path)
        };

        // For existing paths, canonicalize fully.
        // For new paths, canonicalize the parent.
        let resolved = if candidate.exists() {
            fs::canonicalize(&candidate)
                .map_err(|e| format!("resolve error: {e}"))?
        } else {
            let parent = candidate.parent()
                .ok_or_else(|| "no parent directory".to_string())?;
            let parent = fs::canonicalize(parent)
                .map_err(|e| format!("parent resolve error: {e}"))?;
            parent.join(candidate.file_name().unwrap_or_default())
        };

        if !resolved.starts_with(&self.root) {
            return Err(format!(
                "BLOCKED: path escapes sandbox ({} is not under {})",
                resolved.display(),
                self.root.display()
            ));
        }

        Ok(resolved)
    }

    fn read_file(&self, path: &str) -> Result<String, String> {
        let p = self.resolve(path)?;
        fs::read_to_string(&p).map_err(|e| format!("read error: {e}"))
    }

    fn write_file(&self, path: &str, content: &str) -> Result<String, String> {
        let p = self.resolve(path)?;
        if let Some(parent) = p.parent() {
            fs::create_dir_all(parent).map_err(|e| format!("mkdir error: {e}"))?;
        }
        fs::write(&p, content).map_err(|e| format!("write error: {e}"))?;
        Ok(format!("Wrote {} bytes to {}", content.len(), p.display()))
    }

    fn delete(&self, path: &str) -> Result<String, String> {
        let p = self.resolve(path)?;
        if p == self.root {
            return Err("Cannot delete sandbox root".into());
        }
        if p.is_dir() {
            fs::remove_dir_all(&p).map_err(|e| format!("rmdir error: {e}"))?;
        } else {
            fs::remove_file(&p).map_err(|e| format!("rm error: {e}"))?;
        }
        Ok(format!("Deleted {}", p.display()))
    }

    fn move_file(&self, src: &str, dst: &str) -> Result<String, String> {
        let s = self.resolve(src)?;
        let mut d = self.resolve(dst)?;
        if d.is_dir() {
            if let Some(name) = s.file_name() {
                d = d.join(name);
                if !d.starts_with(&self.root) {
                    return Err("Destination escapes sandbox".into());
                }
            }
        }
        fs::rename(&s, &d).map_err(|e| format!("move error: {e}"))?;
        Ok(format!("Moved {} → {}", s.display(), d.display()))
    }

    fn copy_file(&self, src: &str, dst: &str) -> Result<String, String> {
        let s = self.resolve(src)?;
        let mut d = self.resolve(dst)?;
        if d.is_dir() {
            if let Some(name) = s.file_name() {
                d = d.join(name);
            }
        }
        if s.is_dir() {
            self.copy_dir_recursive(&s, &d)?;
        } else {
            if let Some(parent) = d.parent() {
                fs::create_dir_all(parent).ok();
            }
            fs::copy(&s, &d).map_err(|e| format!("copy error: {e}"))?;
        }
        Ok(format!("Copied to {}", d.display()))
    }

    fn copy_dir_recursive(&self, src: &Path, dst: &Path) -> Result<(), String> {
        fs::create_dir_all(dst).map_err(|e| format!("mkdir error: {e}"))?;
        for entry in fs::read_dir(src).map_err(|e| format!("readdir error: {e}"))? {
            let entry = entry.map_err(|e| format!("entry error: {e}"))?;
            let src_path = entry.path();
            let dst_path = dst.join(entry.file_name());
            if !dst_path.starts_with(&self.root) {
                return Err("Copy destination escapes sandbox".into());
            }
            if src_path.is_dir() {
                self.copy_dir_recursive(&src_path, &dst_path)?;
            } else {
                fs::copy(&src_path, &dst_path)
                    .map_err(|e| format!("copy error: {e}"))?;
            }
        }
        Ok(())
    }

    fn list_dir(&self, path: &str) -> Result<String, String> {
        let p = self.resolve(path)?;
        if !p.is_dir() {
            return Err(format!("{} is not a directory", p.display()));
        }
        let mut entries = Vec::new();
        for entry in fs::read_dir(&p).map_err(|e| format!("readdir: {e}"))? {
            let entry = entry.map_err(|e| format!("entry: {e}"))?;
            let mut name = entry.file_name().to_string_lossy().to_string();
            if entry.path().is_dir() {
                name.push('/');
            }
            entries.push(name);
        }
        entries.sort();
        Ok(entries.join("\n"))
    }

    fn mkdir(&self, path: &str) -> Result<String, String> {
        let p = self.resolve(path)?;
        fs::create_dir_all(&p).map_err(|e| format!("mkdir error: {e}"))?;
        Ok(format!("Created {}", p.display()))
    }
}

// ── main loop ────────────────────────────────────────────────

fn handle(sandbox: &Sandbox, req: &Request) -> Response {
    let r = match req.action.as_str() {
        "read_file" => {
            let path = req.params["path"].as_str().unwrap_or("");
            sandbox.read_file(path)
        }
        "write_file" => {
            let path = req.params["path"].as_str().unwrap_or("");
            let content = req.params["content"].as_str().unwrap_or("");
            sandbox.write_file(path, content)
        }
        "delete" => {
            let path = req.params["path"].as_str().unwrap_or("");
            sandbox.delete(path)
        }
        "move_file" => {
            let src = req.params["source"].as_str().unwrap_or("");
            let dst = req.params["destination"].as_str().unwrap_or("");
            sandbox.move_file(src, dst)
        }
        "copy_file" => {
            let src = req.params["source"].as_str().unwrap_or("");
            let dst = req.params["destination"].as_str().unwrap_or("");
            sandbox.copy_file(src, dst)
        }
        "list_dir" => {
            let path = req.params["path"].as_str().unwrap_or(".");
            sandbox.list_dir(path)
        }
        "mkdir" => {
            let path = req.params["path"].as_str().unwrap_or("");
            sandbox.mkdir(path)
        }
        _ => Err(format!("unknown action: {}", req.action)),
    };

    match r {
        Ok(result) => Response { ok: true, result },
        Err(e) => Response { ok: false, result: e },
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: swik-sandbox <workspace-root>");
        std::process::exit(1);
    }

    let sandbox = match Sandbox::new(&args[1]) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Sandbox init failed: {e}");
            std::process::exit(1);
        }
    };

    eprintln!(
        "[swik-sandbox] locked to {}  (pid {})",
        sandbox.root.display(),
        std::process::id()
    );

    // Drop supplementary groups on Linux
    #[cfg(target_os = "linux")]
    {
        // Best-effort group drop
        unsafe {
            libc::setgroups(0, std::ptr::null());
        }
    }

    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        if line.trim().is_empty() {
            continue;
        }

        let req: Request = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(e) => {
                let err = Response {
                    ok: false,
                    result: format!("Invalid JSON: {e}"),
                };
                let _ = writeln!(out, "{}", serde_json::to_string(&err).unwrap());
                continue;
            }
        };

        eprintln!("[swik-sandbox] action={} params={}", req.action, req.params);
        let resp = handle(&sandbox, &req);
        let _ = writeln!(out, "{}", serde_json::to_string(&resp).unwrap());
        let _ = out.flush();
    }
}
