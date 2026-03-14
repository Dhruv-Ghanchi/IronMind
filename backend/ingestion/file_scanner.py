import os
import time

ALLOWED_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.sql'}
IGNORED_DIRECTORIES = {'node_modules', 'dist', 'build', 'venv', '.git', '__pycache__', '.next', 'coverage', 'out'}
MAX_SCANNED_FILES = 500
MAX_PARSED_FILES = 180
SCAN_TIMEOUT_SECONDS = 25   # PRD §8 — graceful cutoff at 25s
SCAN_WARN_SECONDS = 20      # PRD §8 — target analysis time < 20s


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
        # Filter ignored directories in-place — they are never traversed
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]

        for file in files:
            # ── Hard timeout check (PRD §8: graceful cutoff at 25s) ──────────
            elapsed = time.time() - start_time
            if elapsed > SCAN_TIMEOUT_SECONDS:
                timed_out = True
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
                    files_to_parse.append(os.path.join(root, file))
                    supported += 1
                else:
                    skipped += 1
            else:
                skipped += 1

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
