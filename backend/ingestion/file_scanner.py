import os
import time

ALLOWED_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.sql', '.html', '.db', '.css', '.json', '.md', '.txt', '.java', '.go', '.c', '.cpp', '.h', '.cs', '.php', '.rb'}
IGNORED_DIRECTORIES = {'node_modules', 'dist', 'build', 'venv', '.git', '__pycache__', '.next', 'coverage', 'out', 'target', 'bin'}
MAX_SCANNED_FILES = 1000
MAX_PARSED_FILES = 200
SCAN_TIMEOUT_SECONDS = 25

def scan_directory(repo_path: str) -> dict:
    """
    Traverses the repository.
    Filters out ignored directories and unsupported extensions.
    Returns:
        files_to_parse  — relative paths of supported files
        skipped         — count of files not included
        supported       — count of files matched
        scanned         — total files inspected
        timed_out       — True if limit hit
    """
    files_to_parse = []
    skipped = 0
    scanned = 0
    supported = 0
    timed_out = False

    start_time = time.time()

    for root, dirs, files in os.walk(repo_path):
        # 1. Filter ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]
        
        for file in files:
            # 2. Hard timeout check
            if time.time() - start_time > SCAN_TIMEOUT_SECONDS:
                timed_out = True
                break

            # 3. Hard scan limit
            if scanned >= MAX_SCANNED_FILES:
                skipped += 1
                continue

            scanned += 1
            _, ext = os.path.splitext(file)
            ext = ext.lower()

            # 4. Filter by extension
            if ext in ALLOWED_EXTENSIONS:
                if len(files_to_parse) < MAX_PARSED_FILES:
                    abs_f = os.path.join(root, file)
                    files_to_parse.append(abs_f)
                    supported += 1
                else:
                    skipped += 1
            else:
                skipped += 1

        if timed_out:
            break

    # Convert to relative paths
    rel_files_to_parse = [os.path.relpath(f, repo_path) for f in files_to_parse]

    return {
        "files_to_parse": rel_files_to_parse,
        "skipped": skipped,
        "supported": supported,
        "scanned": scanned,
        "timed_out": timed_out,
        "elapsed_seconds": round(time.time() - start_time, 2)
    }
