---
phase: 1
plan: 1
wave: 1
gap_closure: false
---

# Plan 1.1: Ingestion & File Scanner (Dev 1)

## Objective
Implement the full repository ingestion pipeline for the Polyglot Dependency Analyzer. This plan covers ZIP upload handling, secure temporary extraction, and file scanning with directory/extension filtering and hard performance limits. The output of this plan is a clean `files_to_parse` list consumed by Dev 2's entity extractors.

## Context
Load these files for context:
- `IMPLEMENTATION_PLAN.md`
- `Polyglot_Dependency_Analyzer_PRD.md`
- `backend/main.py`
- `backend/ingestion/zip_handler.py`
- `backend/ingestion/file_scanner.py`

---

## Tasks

<task type="auto">
  <name>Setup FastAPI skeleton and backend structure</name>
  <files>
    backend/__init__.py
    backend/ingestion/__init__.py
    backend/requirements.txt
    backend/main.py
  </files>
  <action>
    Initialize FastAPI application with CORS middleware.
    Define skeleton endpoints matching the agreed integration contracts.

    Steps:
    1. Create `backend/__init__.py` and `backend/ingestion/__init__.py` (empty).
    2. Create `backend/requirements.txt` with: fastapi, uvicorn, python-multipart.
    3. In `backend/main.py`:
       - Instantiate FastAPI app.
       - Add CORSMiddleware allowing all origins.
       - Define skeleton `POST /upload`, `POST /graph`, `POST /impact`, `POST /query`, `POST /suggest-fix`.

    AVOID: Putting business logic in main.py — keep it as a thin router layer.
    USE: Separate ingestion module imports to keep main.py clean.
  </action>
  <verify>
    cd c:\Users\Yash\Desktop\ByteCamp
    python -c "from backend.main import app; print('FastAPI app loaded OK')"
  </verify>
  <done>
    - FastAPI app can be imported without errors.
    - All 5 endpoints exist and return JSON.
  </done>
</task>

<task type="auto">
  <name>Implement ZIP upload handler</name>
  <files>
    backend/ingestion/zip_handler.py
  </files>
  <action>
    Handle secure extraction of uploaded ZIP files to a temporary directory.

    Steps:
    1. Accept the path to a saved ZIP file as input.
    2. Use `tempfile.mkdtemp()` to create an isolated temp directory.
    3. Use `zipfile.ZipFile.extractall()` to extract contents.
    4. Return the path to the extracted folder.

    AVOID: Path traversal vulnerabilities — only extract to the designated temp dir.
    USE: `uuid` prefix on temp dir names to prevent collisions.
  </action>
  <verify>
    python -m backend.test_ingestion
  </verify>
  <done>
    - Uploaded ZIP is extracted to a transient temp folder.
    - Returned path exists and contains extracted repo files.
  </done>
</task>

<task type="auto">
  <name>Implement file scanner with filtering and performance limits</name>
  <files>
    backend/ingestion/file_scanner.py
  </files>
  <action>
    Traverse the extracted repo and filter files according to PRD constraints.

    Steps:
    1. Walk directory tree using `os.walk()`.
    2. In-place filter `dirs[:]` to skip ignored directories:
       node_modules, dist, build, venv, .git, __pycache__, .next, coverage, out
    3. For each file:
       a. If total scanned count >= 500 → skip and increment skipped counter.
       b. If extension not in {.py, .js, .ts, .jsx, .tsx, .sql} → skip.
       c. If total parsed count >= 180 → skip.
       d. Otherwise → append to files_to_parse.
    4. Return relative paths (relative to repo root).

    AVOID: Storing absolute temp paths in output — always use relative paths.
    USE: `os.path.relpath(file, repo_path)` for consistent output.
  </action>
  <verify>
    python -m backend.test_ingestion
  </verify>
  <done>
    Output contract satisfied:
    {
      "files_to_parse": ["backend/user_service.py", ...],
      "skipped": N,
      "supported": N,
      "scanned": N
    }
    Ignored dirs are never traversed. Limits enforced without crashes.
  </done>
</task>

<task type="auto">
  <name>Wire POST /upload endpoint with debug mode</name>
  <files>
    backend/main.py
  </files>
  <action>
    Connect the upload endpoint to zip_handler and file_scanner. Add hidden debug mode.

    Steps:
    1. Accept `UploadFile` and optional `debug: bool = False` query param.
    2. Save upload to a temp file using `tempfile.mkstemp()`.
    3. Call `extract_zip(temp_zip_path)` → get repo path.
    4. Call `scan_directory(repo_path)` → get scan results.
    5. Build and return the standard response:
       { analysis_id, files_parsed, files_skipped, message }
    6. If `debug=True`, append debug_info block with scanned counts and file list.
    7. In `finally` block: delete the temp zip file regardless of success/failure.

    AVOID: Leaking temp files on exceptions — always clean up in finally.
    USE: `uuid.uuid4().hex[:8]` for short, unique analysis_id values.
  </action>
  <verify>
    # Start server:
    uvicorn backend.main:app --reload
    # Test upload (in another terminal):
    curl -X POST http://localhost:8000/upload -F "file=@demo_repo.zip"
    # Test debug mode:
    curl -X POST "http://localhost:8000/upload?debug=true" -F "file=@demo_repo.zip"
  </verify>
  <done>
    Standard response:
    { "analysis_id": "session-XXXXXXXX", "files_parsed": N, "files_skipped": N, "message": "Analysis initialized" }
    Debug response includes debug_info block.
    No temp files leaked on success or failure.
  </done>
</task>

<task type="auto">
  <name>Write and pass ingestion unit test</name>
  <files>
    backend/test_ingestion.py
  </files>
  <action>
    Create a self-contained test that validates the full ingestion path.

    Steps:
    1. Build a synthetic directory with:
       - src/main.py (allowed)
       - src/components/App.tsx (allowed)
       - node_modules/react/index.js (ignored dir)
       - .git/config (ignored dir)
       - README.md (unsupported extension)
    2. Zip to a temp file.
    3. Call `extract_zip()` → verify path exists.
    4. Call `scan_directory()` → assert:
       - supported == 2
       - len(files_to_parse) == 2
       - main.py and App.tsx are in the list
    5. Clean up all temp files.

    AVOID: Leaving temp files behind on test failure — use try/finally for cleanup.
    USE: `shutil.rmtree()` for recursive cleanup of temp dirs.
  </action>
  <verify>
    python -m backend.test_ingestion
  </verify>
  <done>
    Output: "Ingestion test passed!"
    No AssertionError. No temp files remain after test run.
  </done>
</task>

---

## Must-Haves
After all tasks complete, verify:
- [ ] `POST /upload` returns valid JSON matching the contract when given a ZIP file
- [ ] Ignored directories (`node_modules`, `.git`, etc.) are never traversed
- [ ] Max 500 files scanned, max 180 files parsed — enforced without crashing
- [ ] All relative paths in `files_to_parse` output — no absolute temp paths
- [ ] Temp ZIP file always cleaned up (even on exceptions)
- [ ] Debug mode not visible in normal API response (only when `?debug=true`)

## Success Criteria
- [ ] All tasks verified passing
- [ ] Must-haves confirmed
- [ ] `python -m backend.test_ingestion` outputs "Ingestion test passed!" ✓
- [ ] No regressions in tests
