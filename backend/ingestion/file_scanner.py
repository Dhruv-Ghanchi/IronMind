import os
import time

ALLOWED_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.sql', '.html', '.db', '.css', '.json', '.md', '.txt'}
IGNORED_DIRECTORIES = {'node_modules', 'dist', 'build', 'venv', '.git', '__pycache__', '.next', 'coverage', 'out'}
MAX_SCANNED_FILES = 10000
MAX_PARSED_FILES = 5000
SCAN_TIMEOUT_SECONDS = 25   # PRD §8 — graceful cutoff at 25s
SCAN_WARN_SECONDS = 20      # PRD §8 — target analysis time < 20s

DEBUG_LOG_PATH = "debug_log.txt"

def log_debug(msg: str):
    with open(DEBUG_LOG_PATH, "a") as f:
        f.write(f"SCANNER: {msg}\n")


def scan_directory(repo_path: str) -> dict:
    """
    Traverses the extracted repository.
    Filters out ignored directories and unsupported extensions.
    Enforces hard limits: 500 max scanned, 180 max parsed, 25s timeout.

    Returns a dict with:
        files_to_parse  — relative paths of supported files to hand to Dev 2
        skipped         — count of files not included
        supported       — count of files that matched and are within limit
        scanned         — total files inspected (before limit)
        timed_out       — True if the 25s wall-clock limit was hit
    """
    files_to_parse = []
    skipped = 0
    scanned = 0
    supported = 0
    timed_out = False

    start_time = time.time()

    for root, dirs, files in os.walk(repo_path):
        log_debug(f"Walking directory: {root}")
        
        # Log and filter ignored directories
        for d in list(dirs):
            if d in IGNORED_DIRECTORIES:
                log_debug(f"IGNORING DIRECTORY: {d} (in {root})")
                dirs.remove(d)
        
        for file in files:
            log_debug(f"Checking file: {file} in {root}")
            # ── Hard timeout check (PRD §8: graceful cutoff at 25s) ──────────
            elapsed = time.time() - start_time
            if elapsed > SCAN_TIMEOUT_SECONDS:
                timed_out = True
                log_debug("Timeout reached during scan")
                break  # exit inner loop; outer for/else will also break below

            # ── Hard scan limit ───────────────────────────────────────────────
            if scanned >= MAX_SCANNED_FILES:
                skipped += 1
                continue

            scanned += 1
            _, ext = os.path.splitext(file)
            ext = ext.lower()

            if ext in ALLOWED_EXTENSIONS:
                if len(files_to_parse) < MAX_PARSED_FILES:
                    abs_f = os.path.join(root, file)
                    files_to_parse.append(abs_f)
                    supported += 1
                    log_debug(f"ACCEPTED: {file} (ext: {ext})")
                else:
                    skipped += 1
                    log_debug(f"LIMIT SKIPPED: {file} (Max parsed reached)")
            else:
                skipped += 1
                log_debug(f"EXTENSION SKIPPED: {file} (ext: '{ext}' not in ALLOWED)")

        if timed_out:
            break  # exit outer os.walk loop cleanly

    # Convert absolute paths to relative paths for consistent output
    rel_files_to_parse = [os.path.relpath(f, repo_path) for f in files_to_parse]

    return {
        "files_to_parse": rel_files_to_parse,
        "skipped": skipped,
        "supported": supported,
        "scanned": scanned,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.time() - start_time, 2)
    }
