from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import tempfile
import os
import uuid
import re
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
# Debug endpoint to check session store
# ---------------------------------------------------------------------------
@app.get("/debug/sessions")
async def debug_sessions():
    """Debug endpoint to see what's in session store"""
    return {
        "session_count": len(SESSION_STORE),
        "session_ids": list(SESSION_STORE.keys()),
        "sessions": {
            session_id: {
                "files_count": len(data.get("code_map", {})),
                "files": list(data.get("code_map", {}).keys())[:10],  # First 10 file names
                "scan_summary": data.get("scan_summary", {})
            }
            for session_id, data in SESSION_STORE.items()
        }
    }


# ---------------------------------------------------------------------------
# Endpoint 2 — Build graph  (POST /graph)   [basic implementation]
# ---------------------------------------------------------------------------
@app.post("/graph")
async def build_graph(body: GraphRequest):
    """Structured graph building from uploaded code."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")

    session_data = SESSION_STORE[body.analysis_id]
    code_map = session_data["code_map"]

    nodes = []
    edges = []

    # Create a node for each file
    for file_path, content in code_map.items():
        normalized_path = file_path.replace('\\', '/')
        # Determine layer and base X position
        layer = "backend"
        base_x = 600
        if "frontend" in normalized_path.lower():
            layer = "frontend"
            base_x = 1800
        elif "backend" in normalized_path.lower():
            layer = "backend"
            base_x = 600
        elif "api" in normalized_path.lower():
            layer = "api"
            base_x = 1200
        elif file_path.endswith('.sql'):
            layer = "database"
            base_x = 0
            
        node_class = "code"
        if file_path.endswith('.sql'):
            node_class = "database"
        elif file_path.endswith(('.yml', '.yaml', '.json', '.env')):
            node_class = "config"

        # Calculate Grid Position within Layer (2 columns to keep it compact but readable)
        layer_nodes_count = len([n for n in nodes if n["data"].get("layer") == layer])
        col = layer_nodes_count % 2
        row = layer_nodes_count // 2
        
        x = base_x + (col * 350)
        y = row * 180

        nodes.append({
            "id": normalized_path,
            "type": "fileNode",
            "position": {"x": x, "y": y},
            "data": {
                "label": normalized_path.split('/')[-1],
                "fullPath": normalized_path,
                "nodeClass": node_class,
                "layer": layer,
                "lines": len(content.split('\n'))
            }
        })

    # Simple dependency detection
    import re
    for source_file, source_content in code_map.items():
        norm_source = source_file.replace('\\', '/')
        for target_file in code_map.keys():
            if source_file != target_file:
                norm_target = target_file.replace('\\', '/')
                target_basename = norm_target.split('/')[-1]
                target_name = target_basename.split('.')[0]

                patterns = [
                    rf'import.*{re.escape(target_name)}',
                    rf'from.*{re.escape(target_name)}',
                    rf'require.*{re.escape(target_name)}',
                    rf'import.*{re.escape(target_basename)}',
                ]

                for pattern in patterns:
                    if re.search(pattern, source_content, re.IGNORECASE):
                        edges.append({
                            "id": f"{norm_source}->{norm_target}",
                            "source": norm_source,
                            "target": norm_target,
                            "type": "smoothstep",
                            "animated": True,
                            "style": {"stroke": "#475569", "strokeWidth": 2}
                        })
                        break

    print(f"DEBUG: Generated {len(nodes)} nodes and {len(edges)} edges")
    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {"nodes": len(nodes), "edges": len(edges)}
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
# Endpoint 4 — NL query  (POST /query)  [basic implementation]
# ---------------------------------------------------------------------------
@app.post("/query")
async def natural_language_query(body: QueryRequest):
    """Smarter query handling with content-aware search."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")

    session_data = SESSION_STORE[body.analysis_id]
    code_map = session_data["code_map"]
    question = body.question.lower()

    matched_nodes = []
    answer_parts = []
    
    # 1. Direct File Name Matching
    for file_path in code_map.keys():
        basename = file_path.split('/')[-1].lower()
        if basename in question or (len(basename.split('.')) > 1 and basename.split('.')[0] in question):
            matched_nodes.append(file_path)
            
    # 2. Keyword/Content Search
    keywords = [word for word in question.split() if len(word) > 3]
    content_matches = []
    for file_path, content in code_map.items():
        if any(kw in content.lower() for kw in keywords):
            if file_path not in matched_nodes:
                content_matches.append(file_path)
    
    # Prioritize direct matches, then content matches
    matched_nodes.extend(content_matches[:5])
    
    # 3. Heuristic Logic for answering
    if "auth" in question or "login" in question or "user" in question:
        auth_files = [f for f in matched_nodes if any(k in f.lower() for k in ["auth", "login", "user", "session"])]
        if auth_files:
            answer_parts.append(f"I found {len(auth_files)} files related to authentication: {', '.join([f.split('/')[-1] for f in auth_files[:3]])}.")
        else:
            answer_parts.append("I couldn't find explicit authentication logic, but you might want to check the API or Backend layers.")
            
    if "database" in question or "db" in question or "sql" in question:
        db_files = [f for f in matched_nodes if f.endswith('.sql') or "db" in f.lower() or "schema" in f.lower()]
        if db_files:
            answer_parts.append(f"Database logic seems to be in: {', '.join([f.split('/')[-1] for f in db_files[:3]])}.")

    if "how many" in question or "count" in question:
        answer_parts.append(f"This repository has {len(code_map)} files total.")

    if not answer_parts:
        if matched_nodes:
            answer_parts.append(f"I found {len(matched_nodes)} relevant files: {', '.join([f.split('/')[-1] for f in matched_nodes[:5]])}. Check them out in the graph!")
        else:
            answer_parts.append("I've searched the code but couldn't find a direct answer. Try asking about specific keywords, file types, or layers.")

    return {
        "answer": " ".join(answer_parts),
        "matched_nodes": matched_nodes[:15] # Don't overwhelm the UI
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

