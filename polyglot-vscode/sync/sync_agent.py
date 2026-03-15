#!/usr/bin/env python3
"""
Polyglot Analyzer — Extension Sync Agent
=========================================
Reads the current backend/frontend state and patches the VS Code
extension to stay aligned automatically.

Usage:
  python sync/sync_agent.py                 # apply changes
  python sync/sync_agent.py --check-only    # report only, no writes
  python sync/sync_agent.py --watch         # continuous mode (polls every 5s)
"""

import re
import sys
import json
import time
import os
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — relative to the sync/ folder's parent (polyglot-vscode/)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent.parent  # ByteCamp/
EXT_DIR = ROOT / "polyglot-vscode"

BACKEND_MAIN      = ROOT / "backend" / "main.py"
FILE_SCANNER      = ROOT / "backend" / "ingestion" / "file_scanner.py"
ZIP_HANDLER       = ROOT / "backend" / "ingestion" / "zip_handler.py"
VITE_CONFIG       = ROOT / "frontend" / "vite.config.ts"
VITE_CONFIG_JS    = ROOT / "frontend" / "vite.config.js"

EXT_JS            = EXT_DIR / "extension.js"
PKG_JSON          = EXT_DIR / "package.json"
SYNC_CONFIG       = Path(__file__).parent / "sync_config.json"

DRY_RUN = "--check-only" in sys.argv
WATCH   = "--watch" in sys.argv

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------
def green(s):  return f"\033[92m{s}\033[0m"
def yellow(s): return f"\033[93m{s}\033[0m"
def red(s):    return f"\033[91m{s}\033[0m"
def bold(s):   return f"\033[1m{s}\033[0m"

# ---------------------------------------------------------------------------
# READ BACKEND
# ---------------------------------------------------------------------------
def read_file_scanner():
    src = FILE_SCANNER.read_text(encoding="utf-8")

    # ALLOWED_EXTENSIONS
    m = re.search(r"ALLOWED_EXTENSIONS\s*=\s*\{([^}]+)\}", src)
    exts = []
    if m:
        exts = [e.strip().strip("'\"") for e in m.group(1).split(",") if e.strip()]

    # IGNORED_DIRECTORIES
    m = re.search(r"IGNORED_DIRECTORIES\s*=\s*\{([^}]+)\}", src)
    ignored = []
    if m:
        ignored = [d.strip().strip("'\"") for d in m.group(1).split(",") if d.strip()]

    # MAX_SCANNED_FILES
    m = re.search(r"MAX_SCANNED_FILES\s*=\s*(\d+)", src)
    max_files = int(m.group(1)) if m else 500

    # MAX_ZIP_SIZE (in main.py)
    main_src = BACKEND_MAIN.read_text(encoding="utf-8")
    m = re.search(r"MAX_ZIP_SIZE_BYTES\s*=\s*(\d+)\s*\*\s*1024\s*\*\s*1024", main_src)
    max_zip_mb = int(m.group(1)) if m else 40

    return {
        "extensions": exts,
        "ignored_dirs": ignored,
        "max_files": max_files,
        "max_zip_mb": max_zip_mb,
    }

def read_backend_routes():
    src = BACKEND_MAIN.read_text(encoding="utf-8")
    routes = re.findall(r'@app\.(get|post|put|delete)\("([^"]+)"\)', src)
    return [{"method": m.upper(), "path": p} for m, p in routes]

def read_backend_port():
    """Look for uvicorn calls in any run scripts or comments."""
    # Default per Phase 1 discovery
    return 8001

def read_frontend_port():
    cfg_file = VITE_CONFIG if VITE_CONFIG.exists() else VITE_CONFIG_JS
    if not cfg_file.exists():
        return 5173
    src = cfg_file.read_text(encoding="utf-8")
    m = re.search(r"port\s*:\s*(\d+)", src)
    return int(m.group(1)) if m else 5173

# ---------------------------------------------------------------------------
# READ EXTENSION
# ---------------------------------------------------------------------------
def read_extension():
    src = EXT_JS.read_text(encoding="utf-8")

    m = re.search(r"const SUPPORTED_EXTENSIONS\s*=\s*\[([^\]]+)\]", src)
    ext_raw = m.group(1) if m else ""
    exts = [e.strip().strip("'\"") for e in ext_raw.split(",") if e.strip()]

    m = re.search(r"const IGNORED_DIRS\s*=\s*\[([^\]]+)\]", src, re.DOTALL)
    dirs_raw = m.group(1) if m else ""
    dirs = [d.strip().strip("'\"") for d in dirs_raw.split(",") if d.strip()]

    m = re.search(r"const MAX_FILES\s*=\s*(\d+)", src)
    max_files = int(m.group(1)) if m else 500

    return {"extensions": exts, "ignored_dirs": dirs, "max_files": max_files}

def read_pkg_defaults():
    pkg = json.loads(PKG_JSON.read_text(encoding="utf-8"))
    props = pkg.get("contributes", {}).get("configuration", {}).get("properties", {})
    backend_url  = props.get("polyglot.backendUrl",  {}).get("default", "http://localhost:8001")
    frontend_url = props.get("polyglot.frontendUrl", {}).get("default", "http://localhost:5173")
    return {"backend_url": backend_url, "frontend_url": frontend_url}

# ---------------------------------------------------------------------------
# APPLY PATCHES
# ---------------------------------------------------------------------------
class Change:
    def __init__(self, file, type_, key, old, new, reason):
        self.file   = file
        self.type_  = type_
        self.key    = key
        self.old    = old
        self.new    = new
        self.reason = reason
        self.applied = False
        self.warning = False

changes = []

def detect_changes(scanner, ext, backend_port, frontend_port, pkg_defaults):
    # 1. SUPPORTED_EXTENSIONS
    if set(scanner["extensions"]) != set(ext["extensions"]):
        changes.append(Change(
            "extension.js", "constant_update", "SUPPORTED_EXTENSIONS",
            ext["extensions"], scanner["extensions"],
            f"file_scanner.py changed: {scanner['extensions']}"
        ))

    # 2. IGNORED_DIRS
    if set(scanner["ignored_dirs"]) != set(ext["ignored_dirs"]):
        changes.append(Change(
            "extension.js", "constant_update", "IGNORED_DIRS",
            ext["ignored_dirs"], scanner["ignored_dirs"],
            f"file_scanner.py changed: {scanner['ignored_dirs']}"
        ))

    # 3. MAX_FILES
    if scanner["max_files"] != ext["max_files"]:
        changes.append(Change(
            "extension.js", "constant_update", "MAX_FILES",
            ext["max_files"], scanner["max_files"],
            f"file_scanner.py MAX_SCANNED_FILES changed to {scanner['max_files']}"
        ))

    # 4. Backend port
    expected_backend = f"http://localhost:{backend_port}"
    if pkg_defaults["backend_url"] != expected_backend:
        changes.append(Change(
            "package.json", "url_update", "polyglot.backendUrl",
            pkg_defaults["backend_url"], expected_backend,
            f"Backend port changed to {backend_port}"
        ))

    # 5. Frontend port
    expected_frontend = f"http://localhost:{frontend_port}"
    if pkg_defaults["frontend_url"] != expected_frontend:
        changes.append(Change(
            "package.json", "url_update", "polyglot.frontendUrl",
            pkg_defaults["frontend_url"], expected_frontend,
            f"Vite dev server port changed to {frontend_port}"
        ))

def patch_extension_js(change):
    src = EXT_JS.read_text(encoding="utf-8")

    if change.key == "SUPPORTED_EXTENSIONS":
        new_val = "['" + "', '".join(change.new) + "']"
        src = re.sub(
            r"const SUPPORTED_EXTENSIONS\s*=\s*\[[^\]]+\]",
            f"const SUPPORTED_EXTENSIONS = {new_val}",
            src
        )
        # Also patch glob include pattern
        exts_no_dot = [e.lstrip('.') for e in change.new]
        new_glob = f"`**/*.{{{','.join(exts_no_dot)}}}`"
        src = re.sub(
            r"`\*\*/\*\.\{[^}]+\}`",
            new_glob,
            src
        )

    elif change.key == "IGNORED_DIRS":
        new_val = "[\n  '" + "', '".join(change.new) + "'\n]"
        src = re.sub(
            r"const IGNORED_DIRS\s*=\s*\[[^\]]+\]",
            f"const IGNORED_DIRS = {new_val}",
            src,
            flags=re.DOTALL
        )

    elif change.key == "MAX_FILES":
        src = re.sub(
            r"const MAX_FILES\s*=\s*\d+",
            f"const MAX_FILES = {change.new}",
            src
        )
        # Also patch findFiles maxResults
        src = re.sub(
            r"(findFiles\([^,]+,\s*[^,]+,\s*)(\d+)(\s*\))",
            lambda m: f"{m.group(1)}{change.new}{m.group(3)}",
            src
        )

    EXT_JS.write_text(src, encoding="utf-8")

def patch_package_json(change):
    pkg = json.loads(PKG_JSON.read_text(encoding="utf-8"))
    if change.key == "polyglot.backendUrl":
        pkg["contributes"]["configuration"]["properties"]["polyglot.backendUrl"]["default"] = change.new
    elif change.key == "polyglot.frontendUrl":
        pkg["contributes"]["configuration"]["properties"]["polyglot.frontendUrl"]["default"] = change.new
    PKG_JSON.write_text(json.dumps(pkg, indent=2), encoding="utf-8")

def apply_changes():
    for c in changes:
        if c.warning:
            continue
        try:
            if c.file == "extension.js":
                patch_extension_js(c)
            elif c.file == "package.json":
                patch_package_json(c)
            c.applied = True
        except Exception as e:
            print(red(f"  ERROR patching {c.file}: {e}"))

# ---------------------------------------------------------------------------
# SYNC CONFIG
# ---------------------------------------------------------------------------
def write_sync_config(scanner, backend_port, frontend_port, routes):
    cfg = {
        "last_sync": datetime.utcnow().isoformat() + "Z",
        "backend_url": f"http://localhost:{backend_port}",
        "frontend_url": f"http://localhost:{frontend_port}",
        "supported_extensions": scanner["extensions"],
        "ignored_dirs": scanner["ignored_dirs"],
        "max_files": scanner["max_files"],
        "endpoints": [f"{r['method']} {r['path']}" for r in routes],
        "graph_route": "/"   # Single-page React app, no sub-route
    }
    SYNC_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SYNC_CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------
def print_report(routes):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(bold(f"\nSYNC REPORT — {ts}"))
    print(f"Files read: main.py, file_scanner.py, zip_handler.py, vite.config.ts")
    print("─" * 65)
    print(f"{'STATUS':<10} {'FILE':<16} {'WHAT CHANGED'}")
    print("─" * 65)

    if not changes:
        print(green("  SYNC COMPLETE — No changes needed."))
        print("  Extension is fully aligned with the current backend and frontend.")
    else:
        for c in changes:
            if c.warning:
                status = yellow("WARNING ")
            elif c.applied:
                status = green("APPLIED ")
            else:
                status = red("FAILED  ")
            print(f"  {status} {c.file:<16} {c.reason}")

    print("─" * 65)
    applied  = sum(1 for c in changes if c.applied)
    warnings = sum(1 for c in changes if c.warning)
    print(f"Total changes applied: {applied}")
    print(f"Warnings requiring manual action: {warnings}")
    print()

    print(bold("Endpoints in backend:"))
    for r in routes:
        print(f"  {r['method']:<6} {r['path']}")
    print()

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run_sync():
    global changes
    changes = []

    scanner       = read_file_scanner()
    backend_port  = read_backend_port()
    frontend_port = read_frontend_port()
    routes        = read_backend_routes()
    ext           = read_extension()
    pkg_defaults  = read_pkg_defaults()

    detect_changes(scanner, ext, backend_port, frontend_port, pkg_defaults)

    if not DRY_RUN:
        apply_changes()
        write_sync_config(scanner, backend_port, frontend_port, routes)

    print_report(routes)


def main():
    if WATCH:
        print("Watching for changes... (Ctrl+C to stop)")
        watched = [BACKEND_MAIN, FILE_SCANNER, ZIP_HANDLER, VITE_CONFIG, VITE_CONFIG_JS]
        last_mtimes = {f: f.stat().st_mtime if f.exists() else 0 for f in watched}
        while True:
            time.sleep(5)
            for f in watched:
                if not f.exists():
                    continue
                mtime = f.stat().st_mtime
                if mtime != last_mtimes[f]:
                    last_mtimes[f] = mtime
                    print(f"\n[{datetime.now():%H:%M:%S}] Change detected in {f.name} — re-syncing...")
                    run_sync()
    else:
        run_sync()


if __name__ == "__main__":
    main()
