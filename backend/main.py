from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import tempfile
import os
import uuid
from typing import Optional
from backend.ingestion.zip_handler import extract_zip, read_files_to_dict
from backend.ingestion.file_scanner import scan_directory

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory session store
# Key: analysis_id
# Value: {
#     "code_map":     { rel_path: source_code }  ← consumed by Dev 2
#     "scan_summary": { supported, skipped, scanned, timed_out, elapsed_seconds }
# }
# repo_path is NOT stored — extracted dir is deleted immediately after reading.
# ---------------------------------------------------------------------------
SESSION_STORE: dict = {}

# PRD §8 hard limit
MAX_ZIP_SIZE_BYTES = 40 * 1024 * 1024  # 40 MB


# ---------------------------------------------------------------------------
# Request models — match IMPLEMENTATION_PLAN.md contracts exactly
# ---------------------------------------------------------------------------
class GraphRequest(BaseModel):
    analysis_id: str

class ImpactRequest(BaseModel):
    analysis_id: str
    node_id: str

class QueryRequest(BaseModel):
    analysis_id: str
    question: str

class SuggestFixRequest(BaseModel):
    analysis_id: str
    node_id: str
    change: str


# ---------------------------------------------------------------------------
# Endpoint 1 — Upload repo  (POST /upload)
# ---------------------------------------------------------------------------
@app.post("/upload")
async def upload_repo(
    file: UploadFile = File(...),
    x_debug_mode: Optional[str] = Header(default=None, alias="X-Debug-Mode"),
):
    """
    Accepts a ZIP repository upload.
    Returns: analysis_id, files_parsed, files_skipped, message

    Hidden debug mode: send header  X-Debug-Mode: true
    PRD constraints: ZIP ≤ 40 MB, max 500 scanned, max 180 parsed, 25s timeout.
    """
    debug = (x_debug_mode or "").lower() == "true"

    # 1. Save upload to a temp file
    temp_zip_fd, temp_zip_path = tempfile.mkstemp(suffix=".zip", prefix="upload_")
    os.close(temp_zip_fd)

    with open(temp_zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 2. Enforce 40 MB ZIP size limit (PRD §8)
        zip_size = os.path.getsize(temp_zip_path)
        if zip_size > MAX_ZIP_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"ZIP file too large ({zip_size // (1024 * 1024)} MB). Maximum allowed is 40 MB."
            )

        # 3. Extract ZIP — ValueError raised for corrupted/bad ZIPs (no raw 500)
        try:
            extracted_repo_path = extract_zip(temp_zip_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 4. Scan directory — apply filters, limits, and 25s timeout
        scan_results = scan_directory(extracted_repo_path)

        # 5. Read file contents into {path: code} dict for Dev 2, then delete
        #    extracted dir immediately — fixes storage leak and provides adapter
        code_map = read_files_to_dict(extracted_repo_path, scan_results["files_to_parse"])

        # 6. Assign analysis_id and persist session (no disk paths stored)
        analysis_id = f"session-{uuid.uuid4().hex[:8]}"
        SESSION_STORE[analysis_id] = {
            "code_map": code_map,          # {rel_path: source_code}  → for Dev 2
            "scan_summary": {
                "supported":       scan_results["supported"],
                "skipped":         scan_results["skipped"],
                "scanned":         scan_results["scanned"],
                "timed_out":       scan_results["timed_out"],
                "elapsed_seconds": scan_results["elapsed_seconds"],
            }
        }

        # 7. Build standard response (IMPLEMENTATION_PLAN.md Endpoint 1 contract)
        response = {
            "analysis_id": analysis_id,
            "files_parsed": scan_results["supported"],
            "files_skipped": scan_results["skipped"],
            "message": "Analysis initialized"
        }

        # Warn if scan was time-cut (partial analysis is still returned)
        if scan_results["timed_out"]:
            response["warning"] = "Scan timed out after 25s — partial analysis returned."

        # Hidden debug mode — only when X-Debug-Mode: true header is sent (PRD §17)
        if debug:
            response["debug_info"] = {
                "scanned_files":   scan_results["scanned"],
                "skipped_files":   scan_results["skipped"],
                "files_to_parse":  list(code_map.keys()),
                "elapsed_seconds": scan_results["elapsed_seconds"],
                "timed_out":       scan_results["timed_out"],
                "node_count":      0,
                "edge_count":      0,
                "pipeline_log":    ["upload ✓", "extract ✓", "scan ✓", "code_map ✓"]
            }

        return response

    finally:
        # Always clean up the raw upload zip, regardless of success/failure
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)


# ---------------------------------------------------------------------------
# Endpoint 2 — Build graph  (POST /graph)   [skeleton for Dev 3]
# ---------------------------------------------------------------------------
@app.post("/graph")
async def build_graph(body: GraphRequest):
    """Skeleton. Dev 3 owns full implementation."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")
    return {
        "nodes": [],
        "edges": [],
        "summary": {"nodes": 0, "edges": 0}
    }


# ---------------------------------------------------------------------------
# Endpoint 3 — Impact analysis  (POST /impact)  [skeleton for Dev 3]
# ---------------------------------------------------------------------------
@app.post("/impact")
async def impact_analysis(body: ImpactRequest):
    """Skeleton. Dev 3 owns full implementation."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")
    return {
        "changed_node": body.node_id,
        "impacted_nodes": [],
        "risk_score": 0,
        "severity": "LOW",
        "explanation": ""
    }


# ---------------------------------------------------------------------------
# Endpoint 4 — NL query  (POST /query)  [skeleton for Dev 2/3]
# ---------------------------------------------------------------------------
@app.post("/query")
async def natural_language_query(body: QueryRequest):
    """Skeleton. Dev 2 + Dev 3 own full implementation."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")
    return {
        "answer": "",
        "matched_nodes": []
    }


# ---------------------------------------------------------------------------
# Endpoint 5 — Suggested fixes  (POST /suggest-fix)  [skeleton for Dev 2/3]
# ---------------------------------------------------------------------------
@app.post("/suggest-fix")
async def suggest_fixes(body: SuggestFixRequest):
    """Skeleton. Dev 2 + Dev 3 own full implementation."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")
    return {
        "suggestions": []
    }

