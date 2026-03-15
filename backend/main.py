from dotenv import load_dotenv
from pathlib import Path
import os
load_dotenv(dotenv_path=Path(__file__).parent / ".env")  # Load backend/.env

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import tempfile
import uuid
import re
import json as _json
import pathlib
import time
from backend.ingestion.zip_handler import extract_zip, read_files_to_dict
from backend.ingestion.file_scanner import scan_directory
from neo4j import GraphDatabase
from . import ai_service
from . import github_service
from . import analyzer
from . import pr_service

app = FastAPI(title="Analysis Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    detail = str(exc)
    if hasattr(exc, "detail"):
        detail = exc.detail
    if not isinstance(detail, str):
        detail = str(detail)
    return JSONResponse(
        status_code=500,
        content={"detail": detail},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    detail = exc.detail
    if not isinstance(detail, str):
        detail = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
    )

# Neo4j configuration (PRD §21: persistence)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    neo4j_driver.verify_connectivity()
    print(f"DEBUG: Connected to Neo4j at {NEO4J_URI}")
except Exception as e:
    print(f"WARNING: Could not connect to Neo4j. Impact analysis will be degraded: {e}")
    neo4j_driver = None

# AI / Featherless AI Configuration handled via ai_service.py

# ---------------------------------------------------------------------------
# Disk-backed session store — survives backend restarts
# Shared between main backend (8000) and github-analyzer (8001)
# ---------------------------------------------------------------------------
_SESSION_DIR = pathlib.Path(__file__).parent.parent / ".polyglot_sessions"
_SESSION_DIR.mkdir(exist_ok=True)

class _DiskSessionStore:
    """Dict-like wrapper that persists each session as a JSON file."""
    def __init__(self, directory: pathlib.Path):
        self._dir = directory

    def _path(self, key: str) -> pathlib.Path:
        # Sanitize key to prevent directory traversal
        safe_key = "".join(c for c in key if c.isalnum() or c in "-_.").rstrip()
        return self._dir / f"{safe_key}.json"

    def __contains__(self, key: str) -> bool:
        return self._path(key).exists()

    def __getitem__(self, key: str):
        p = self._path(key)
        if not p.exists():
            raise KeyError(key)
        return _json.loads(p.read_text(encoding="utf-8"))

    def __setitem__(self, key: str, value):
        self._path(key).write_text(_json.dumps(value), encoding="utf-8")

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        return [p.stem for p in self._dir.glob("*.json")]

    def items(self):
        for p in self._dir.glob("*.json"):
            yield p.stem, _json.loads(p.read_text(encoding="utf-8"))

    def __len__(self):
        return len(list(self._dir.glob("*.json")))

SESSION_STORE = _DiskSessionStore(_SESSION_DIR)

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
    question: str
    analysis_id: str = None
    file_name: str = None
    repo_meta: dict = None

class SuggestFixRequest(BaseModel):
    analysis_id: str
    node_id: str
    change: str

# GitHub-specific models
class AnalyzeRequest(BaseModel):
    github_url: str
    github_token: str = ""

class PatchRequest(BaseModel):
    intent: str
    affected_files: list
    repo_meta: dict

class PRRequest(BaseModel):
    patches: list
    intent: str
    repo_meta: dict


# ---------------------------------------------------------------------------
# Endpoint 1 — Upload repo  (POST /upload)
# ---------------------------------------------------------------------------
def parse_code_symbols(code_map: dict):
    """
    Extracts granular symbols (Classes, Functions, Endpoints) from the code map.
    """
    symbols = []
    symbol_edges = []
    
    # Regex patterns
    CLASS_PATTERN = re.compile(r'(?:class|export\s+class)\s+([a-zA-Z0-9_]+)(?:\(([^)]+)\))?')
    FUNC_PATTERN = re.compile(r'(?:def|async\s+def|function)\s+([a-zA-Z0-9_]+)')
    ENDPOINT_PATTERN = re.compile(r'@app\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')
    HTML_ID_PATTERN = re.compile(r'id=["\']([^"\']+)["\']')
    JS_CONST_PATTERN = re.compile(r'(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=')

    # SQL/DB Markers
    DB_KEYWORDS = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE TABLE', 'DROP TABLE', 'execute(', 'run(', 'commit(']

    for file_path, content in code_map.items():
        norm_path = file_path.replace('\\', '/')
        lines = content.split('\n')
        
        # 1. Classes
        for match in CLASS_PATTERN.finditer(content):
            name = match.group(1)
            bases = match.group(2) or ""
            start_pos = match.start()
            start_line = content[:start_pos].count('\n')
            
            # Simple line count heuristic: find next class or def or end of file
            remaining = content[match.end():]
            next_sym = re.search(r'\n(class|def|async\s+def|export|function|@app)', remaining)
            block = remaining[:next_sym.start()] if next_sym else remaining
            line_count = block.count('\n') + 1

            symbol_id = f"{norm_path}::class::{name}"
            kind = "class"
            if "BaseModel" in bases:
                kind = "pydantic_model"

            symbols.append({
                "id": symbol_id,
                "label": name,
                "type": "symbol",
                "kind": kind,
                "file": norm_path,
                "lines": line_count
            })
            symbol_edges.append({"source": norm_path, "target": symbol_id, "type": "CONTAINS"})

        # 2. Functions
        for match in FUNC_PATTERN.finditer(content):
            name = match.group(1)
            if name in ['main', 'app', 'function']: continue
            start_pos = match.start()
            start_line = content[:start_pos].count('\n')

            # Find decorator context (API detection)
            context_before = content[max(0, start_pos-200):start_pos]
            # Rule: API if has @app.get/post etc or router.
            is_api = any(k in context_before for k in ["@app.get", "@app.post", "@app.put", "@app.delete", "router."])
            
            # Find SQL usage (DB detection)
            remaining = content[match.end():]
            next_sym = re.search(r'\n(class|def|async\s+def|export|function|@app)', remaining)
            block = remaining[:next_sym.start()] if next_sym else remaining
            line_count = block.count('\n') + 1
            
            # Rule: DATABASE if has SELECT/INSERT/CREATE or conn.execute or session.run
            is_db = any(kw.lower() in block.lower() for kw in ["select", "insert", "create table", "conn.execute", "session.run"])

            symbol_id = f"{norm_path}::func::{name}"
            kind = "function"
            if is_api: kind = "api_route"
            elif is_db: kind = "db_function"
            # Rule: BACKEND is default for functions not API/DB in backend files

            symbols.append({
                "id": symbol_id,
                "label": name,
                "type": "symbol",
                "kind": kind,
                "file": norm_path,
                "lines": line_count
            })
            symbol_edges.append({"source": norm_path, "target": symbol_id, "type": "CONTAINS"})

        # 3. HTML Elements (IDs)
        if norm_path.endswith('.html'):
            for match in HTML_ID_PATTERN.finditer(content):
                name = match.group(1)
                symbol_id = f"{norm_path}::element::{name}"
                symbols.append({
                    "id": symbol_id,
                    "label": f"#{name}",
                    "type": "symbol",
                    "kind": "element",
                    "file": norm_path,
                    "lines": 1
                })
                symbol_edges.append({"source": norm_path, "target": symbol_id, "type": "CONTAINS"})

        # 4. JS Objects/Constants
        if norm_path.endswith('.js'):
            for match in JS_CONST_PATTERN.finditer(content):
                name = match.group(1)
                symbol_id = f"{norm_path}::const::{name}"
                symbols.append({
                    "id": symbol_id,
                    "label": name,
                    "type": "symbol",
                    "kind": "constant",
                    "file": norm_path,
                    "lines": 1
                })
                symbol_edges.append({"source": norm_path, "target": symbol_id, "type": "CONTAINS"})

        # 5. API Endpoints
        for match in ENDPOINT_PATTERN.finditer(content):
            path = match.group(1)
            symbol_id = f"{norm_path}::endpoint::{path}"
            symbols.append({
                "id": symbol_id,
                "label": f"API: {path}",
                "type": "endpoint",
                "kind": "route",
                "file": norm_path
            })
            symbol_edges.append({"source": norm_path, "target": symbol_id, "type": "EXPOSES"})

    return symbols, symbol_edges


@app.post("/upload")
async def upload_repository(
    file: UploadFile = File(...),
):
    """
    Accepts a ZIP repository upload.
    Returns: analysis_id, files_parsed, files_skipped, message

    PRD constraints: ZIP ≤ 40 MB, max 500 scanned, max 180 parsed, 25s timeout.
    """

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

        # 6. Deep Analysis: Symbols & Endpoints
        symbols, symbol_edges = parse_code_symbols(code_map)
        
        nodes = []
        edges = []
        
        # File Nodes
        for file_path, content in code_map.items():
            normalized_path = file_path.replace('\\', '/')
            ext = os.path.splitext(normalized_path)[1].lower()
            
            # Multi-Layer Detection (Rule 2 & 3)
            content_lower = content.lower()
            detected_layers = []
            
            # 1. DATABASE
            if any(k in content_lower for k in ["create table", "sqlite3", "sqlalchemy"]) or ext in [".sql", ".db"]:
                detected_layers.append("database")
            
            # 2. BACKEND
            if any(k in content_lower for k in ["from fastapi", "import flask", "import django", "@app.route", "@app.get"]):
                detected_layers.append("backend")
            
            # 3. API
            if any(k in content_lower for k in ["@app.get", "@app.post", "@app.put", "@app.delete", "router."]):
                detected_layers.append("api")
            
            # 4. FRONTEND
            is_in_frontend_src = "frontend/src" in normalized_path.lower()
            if ext in [".html", ".jsx", ".tsx", ".vue", ".css"] or (ext == ".js" and is_in_frontend_src):
                detected_layers.append("frontend")
            
            # Fallback for main.py (Rule: main.py is both BACKEND and API potentially, but forced here if missed)
            if normalized_path.endswith("main.py"):
                if "backend" not in detected_layers: detected_layers.append("backend")
                if "api" in content_lower and "api" not in detected_layers: detected_layers.append("api")

            # Final check: If no layer detected, default to backend or directory name
            if not detected_layers:
                if "frontend" in normalized_path.lower(): detected_layers.append("frontend")
                elif "api" in normalized_path.lower(): detected_layers.append("api")
                elif "database" in normalized_path.lower() or "db" in normalized_path.lower(): detected_layers.append("database")
                else: detected_layers.append("backend")

            # Pick primary layer for layout (DATABASE > BACKEND > API > FRONTEND)
            primary_layer = "backend"
            for p in ["database", "backend", "api", "frontend"]:
                if p in detected_layers:
                    primary_layer = p
                    break

            print(f"FILE FOUND: {normalized_path} | LAYERS: {', '.join(detected_layers)} | PRIMARY: {primary_layer}")
            
            nodes.append({
                "id": normalized_path,
                "type": "fileNode",
                "position": {"x": 0, "y": 0},
                "data": {
                    "label": normalized_path.split('/')[-1],
                    "fullPath": normalized_path,
                    "nodeClass": "code",
                    "layer": primary_layer,
                    "all_layers": detected_layers,
                    "lines": len(content.split('\n'))
                }
            })

        # Symbol & Endpoint Nodes
        for s in symbols:
            # Shift symbols slightly to the right of their files
            parent_file = [n for n in nodes if n["id"] == s["file"]][0]
            
            # Map symbol kind to layer
            s_layer = parent_file["data"]["layer"]
            if s["kind"] == "api_route": s_layer = "api"
            elif s["kind"] == "db_function": s_layer = "database"
            elif s["kind"] == "pydantic_model": s_layer = "backend"
            elif s["kind"] == "element": s_layer = "frontend"

            nodes.append({
                "id": s["id"],
                "type": "fileNode",
                "position": {"x": parent_file["position"]["x"] + 150, "y": 0},
                "data": {
                    "label": s["label"],
                    "fullPath": s["id"],
                    "nodeClass": s["kind"],
                    "layer": s_layer,
                    "lines": s.get("lines", 0)
                }
            })


        # 8. Infer Databases from Code (even if .db file is missing)
        DB_CONNECT_PATTERN = re.compile(r'connect\(["\']([^"\']+\.db|[^"\']+)["\']\)|db\s*=\s*["\']([^"\']+)["\']')
        for file_path, content in code_map.items():
            for match in DB_CONNECT_PATTERN.finditer(content):
                db_name = match.group(1) or match.group(2)
                if db_name and not any(n["id"] == db_name for n in nodes):
                    print(f"Inferred Database from code in {file_path}: {db_name}")
                    db_id = f"inferred::{db_name}"
                    nodes.append({
                        "id": db_id,
                        "type": "fileNode",
                        "position": {"x": 0, "y": 0},
                        "data": {
                            "label": db_name,
                            "fullPath": db_id,
                            "nodeClass": "database",
                            "layer": "database",
                            "lines": 0
                        }
                    })
                    edges.append({
                        "id": f"{file_path}->{db_id}",
                        "source": file_path.replace('\\', '/'),
                        "target": db_id,
                        "type": "smoothstep",
                        "animated": True,
                        "style": {"stroke": "#f59e0b", "strokeWidth": 2}
                    })

        # 9. Calculate Cross-Layer Edges (fetch, src, href, imports)
        API_CALL_PATTERN = re.compile(r'(?:fetch|axios\.\w+)\s*\(\s*["\']([^"\']+)["\']')
        HTML_REF_PATTERN = re.compile(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']')
        IMPORT_PATTERN = re.compile(r'(?:import|from|require).*?["\']([^"\']+)["\']|import\s+([a-zA-Z0-9_]+)')

        # 10. NEW: RE-RUN GRID-IFY TO CATCH INFERRED NODES AND SYMBOLS
        for layer in ["database", "backend", "api", "frontend"]:
            layer_nodes = [n for n in nodes if n["data"].get("layer") == layer]
            for i, n in enumerate(layer_nodes):
                base_x = 0 if layer == "database" else 800 if layer == "backend" else 1600 if layer == "api" else 2400
                col = i % 5
                row = i // 5
                n["position"] = {"x": base_x + (col * 400), "y": row * 200}

        print("Starting comprehensive edge detection...")
        for src_path, src_content in code_map.items():
            norm_src = src_path.replace('\\', '/')
            
            # A. Detect API Calls (Frontend -> Backend)
            for match in API_CALL_PATTERN.finditer(src_content):
                endpoint = match.group(1)
                # Find which backend file exposes this endpoint
                for target_node in nodes:
                    if target_node["data"].get("nodeClass") == "route" and endpoint in target_node["id"]:
                        edges.append({
                            "id": f"{norm_src}->{target_node['id']}",
                            "source": norm_src,
                            "target": target_node["id"],
                            "type": "smoothstep",
                            "animated": True,
                            "label": "API Call",
                            "kind": "DEPENDS_ON",
                            "style": {"stroke": "#10b981", "strokeWidth": 2}
                        })
                        print(f"Link: {norm_src} calls API {target_node['id']}")

            # B. Detect Local File References (HTML -> JS, etc)
            for match in HTML_REF_PATTERN.finditer(src_content):
                ref = match.group(1).split('/')[-1]
                for tgt_path in code_map.keys():
                    if ref in tgt_path:
                        norm_tgt = tgt_path.replace('\\', '/')
                        edges.append({
                            "id": f"{norm_src}->{norm_tgt}",
                            "source": norm_src,
                            "target": norm_tgt,
                            "type": "smoothstep",
                            "animated": True,
                            "kind": "DEPENDS_ON",
                            "style": {"stroke": "#3b82f6", "strokeWidth": 2}
                        })
                        print(f"Link: {norm_src} references {norm_tgt}")

            # C. Detect Imports (Standard)
            for match in IMPORT_PATTERN.finditer(src_content):
                ref = match.group(1) or match.group(2)
                if not ref: continue
                for tgt_path in code_map.keys():
                    norm_tgt = tgt_path.replace('\\', '/')
                    tgt_name = norm_tgt.split('/')[-1].split('.')[0]
                    if ref == tgt_name or ref in norm_tgt:
                        edges.append({
                            "id": f"{norm_src}->{norm_tgt}",
                            "source": norm_src,
                            "target": norm_tgt,
                            "type": "smoothstep",
                            "animated": True,
                            "kind": "DEPENDS_ON",
                            "style": {"stroke": "#475569", "strokeWidth": 2}
                        })
                        print(f"Link: {norm_src} imports {norm_tgt}")

        # Add Symbol Edges
        for se in symbol_edges:
            edges.append({
                "id": f"{se['source']}->{se['target']}",
                "source": se["source"],
                "target": se["target"],
                "type": "smoothstep",
                "animated": False,
                "kind": "CONTAINS",
                "style": {"stroke": "#94a3b8", "strokeWidth": 1, "strokeDasharray": "5,5"}
            })

        # Persist to Neo4j IF available
        if neo4j_driver:
            try:
                with neo4j_driver.session() as session:
                    session.run("MATCH (n) DETACH DELETE n")
                    for node in nodes:
                        session.run(
                            "MERGE (f:Node {id: $id, label: $label, layer: $layer, kind: $kind})",
                            id=node["id"], label=node["data"]["label"], 
                            layer=node["data"]["layer"], kind=node["data"]["nodeClass"]
                        )
                    for edge in edges:
                        session.run(
                            "MATCH (a:Node {id: $src}), (b:Node {id: $tgt}) "
                            "MERGE (a)-[r:REL {type: $type}]->(b)",
                            src=edge["source"], tgt=edge["target"], type=edge.get("type", "DEPENDS_ON")
                        )
            except Exception as e:
                print(f"DEBUG: Neo4j persistence failed: {e}")

        # Store results in SESSION_STORE
        analysis_id = f"session-{uuid.uuid4().hex[:8]}"
        SESSION_STORE[analysis_id] = {
            "analysis_id": analysis_id,
            "code_map": code_map,
            "nodes": nodes,
            "edges": edges,
            "scan_summary": scan_results,
            "repo_files": [{"path": p, "content": c} for p, c in code_map.items()] # Compatibility
        }

        return {
            "analysis_id": analysis_id,
            "files_parsed": len(code_map),
            "files_skipped": scan_results["skipped"],
            "message": "Deep Analysis complete"
        }

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
    """Structured graph building from uploaded code using Hybrid Engine (Neo4j or In-Memory)."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")

    session_data = SESSION_STORE[body.analysis_id]
    
    # Try getting from Neo4j first for most accurate/persisted state
    if neo4j_driver:
        try:
            nodes = []
            edges = []
            with neo4j_driver.session() as session:
                result = session.run("MATCH (n:Node) RETURN n")
                for record in result:
                    n = record["n"]
                    layer = n["layer"]
                    nodes.append({
                        "id": n["id"], "type": "fileNode", 
                        "position": {"x": 0, "y": 0}, # Will grid next
                        "data": {"label": n["label"], "fullPath": n["id"], "nodeClass": n["kind"], "layer": layer, "lines": 0}
                    })
                
                # Grid-ify Neo4j nodes
                for layer in ["database", "backend", "api", "frontend"]:
                    layer_nodes = [node for node in nodes if node["data"]["layer"] == layer]
                    for i, node in enumerate(layer_nodes):
                        base_x = 0 if layer == "database" else 600 if layer == "backend" else 1200 if layer == "api" else 1800
                        col = i % 3
                        row = i // 3
                        node["position"] = {"x": base_x + (col * 300), "y": row * 150}

                result = session.run("MATCH (a:Node)-[r]->(b:Node) RETURN a.id, b.id, type(r) as rel_type")
                for record in result:
                    edges.append({
                        "id": f"{record['a.id']}->{record['b.id']}", "source": record["a.id"], "target": record["b.id"],
                        "type": "smoothstep", "animated": record["rel_type"] != "CONTAINS", 
                        "style": {"stroke": "#475569" if record["rel_type"] != "CONTAINS" else "#94a3b8", "strokeWidth": 2 if record["rel_type"] != "CONTAINS" else 1}
                    })
            if nodes: # If Neo4j gave us something, use it
                return {"nodes": nodes, "edges": edges, "summary": {"nodes": len(nodes), "edges": len(edges)}}
        except Exception as e:
            print(f"DEBUG: Neo4j retrieval failed, falling back to memory: {e}")

    # Fallback to in-memory stored results
    return {
        "nodes": session_data.get("nodes", []),
        "edges": session_data.get("edges", []),
        "summary": {"nodes": len(session_data.get("nodes", [])), "edges": len(session_data.get("edges", []))}
    }


# ---------------------------------------------------------------------------
# Endpoint 3 — Impact analysis  (POST /impact)  [skeleton for Dev 3]
# ---------------------------------------------------------------------------
@app.post("/impact")
async def analyze_impact(body: ImpactRequest):
    """Recursive impact analysis using Neo4j OR Depth-First-Search in memory."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")

    session_data = SESSION_STORE[body.analysis_id]
    impacted_nodes = [body.node_id]

    # Try Neo4j Recursive Query
    if neo4j_driver:
        try:
            with neo4j_driver.session() as session:
                # Use generic Node label and follow all relationship types
                query = "MATCH (target:Node {id: $node_id})<-[:REL*]-(impacted) RETURN DISTINCT impacted.id"
                result = session.run(query, node_id=body.node_id)
                for record in result:
                    if record["impacted.id"] not in impacted_nodes:
                        impacted_nodes.append(record["impacted.id"])
                if len(impacted_nodes) > 1:
                    return {"impacted_nodes": impacted_nodes, "risk_score": len(impacted_nodes) * 1.5, "severity": "HIGH" if len(impacted_nodes) > 5 else "MEDIUM", "explanation": f"Recursive analysis found {len(impacted_nodes)} nodes (files, functions, classes) that may be impacted."}
        except Exception as e:
            print(f"DEBUG: Neo4j impact analysis failed: {e}")

    # Fallback: Bi-directional In-memory Search
    edges = session_data.get("edges", [])
    queue = [body.node_id]
    while queue:
        current = queue.pop(0)
        for edge in edges:
            # 1. Incoming Dependencies (If target is current, source is impacted)
            if edge["target"] == current and edge["source"] not in impacted_nodes:
                impacted_nodes.append(edge["source"])
                queue.append(edge["source"])
            
            # 2. Outgoing Containment (If source is current and it's a CONTAINS edge, target is impacted)
            if edge["source"] == current and edge.get("kind") == "CONTAINS" and edge["target"] not in impacted_nodes:
                impacted_nodes.append(edge["target"])
                queue.append(edge["target"])

    return {
        "impacted_nodes": impacted_nodes,
        "risk_score": len(impacted_nodes) * 1.5,
        "severity": "HIGH" if len(impacted_nodes) > 5 else "MEDIUM",
        "explanation": f"Architectural analysis found {len(impacted_nodes)} nodes (files, functions, symbols) that will be lost or broken by this change."
    }


# ---------------------------------------------------------------------------
# Endpoint 4 — NL query  (POST /query)  [basic implementation]
# ---------------------------------------------------------------------------
@app.post("/query")
async def natural_language_query(body: QueryRequest):
    print(f"DEBUG: Received query request: {body}")
    analysis_id = body.analysis_id or (body.repo_meta and body.repo_meta.get("analysis_id"))
    
    if analysis_id not in SESSION_STORE:
        # Fallback to general AI answer if no graph context exists
        answer = ai_service.answer_query(body.question, "Context: General codebase question.")
        return {"answer": answer, "impact": None}

    session_data = SESSION_STORE[body.analysis_id]
    code_map = session_data["code_map"]
    question = body.question.lower()

    matched_nodes = []
    answer_parts = []
    
    # 1. Structural Query with Neo4j
    if neo4j_driver:
        with neo4j_driver.session() as session:
            # Search for symbols, endpoints or files matching keywords
            query_terms = [word for word in question.split() if len(word) > 3]
            for term in query_terms:
                result = session.run(
                    "MATCH (n:Node) WHERE n.label CONTAINS $term RETURN n.id, n.label, n.kind LIMIT 5",
                    term=term
                )
                for record in result:
                    if record["n.id"] not in matched_nodes:
                        matched_nodes.append(record["n.id"])
                        if record["n.kind"] in ["function", "class", "route"]:
                            answer_parts.append(f"I found a {record['n.kind']} named '{record['n.label']}'.")

            # Dependency/Impact logic
            if "depend" in question or "use" in question or "impact" in question:
                for n_id in list(matched_nodes):
                    res = session.run(
                        "MATCH (target:Node {id: $id})<-[:REL*]-(impacted) RETURN impacted.id LIMIT 5",
                        id=n_id
                    )
                    impact_list = [r["impacted.id"] for r in res]
                    if impact_list:
                        answer_parts.append(f"Nodes that use/depend on this: {', '.join([i.split('/')[-1] for i in impact_list[:3]])}.")

    # 2. Direct File Name Matching
    for file_path in code_map.keys():
        basename = file_path.split('/')[-1].lower()
        if basename in question or (len(basename.split('.')) > 1 and basename.split('.')[0] in question):
            if file_path not in matched_nodes:
                matched_nodes.append(file_path)
            
    # 3. Keyword Content Search
    keywords = [word for word in question.split() if len(word) > 3]
    for file_path, content in code_map.items():
        if any(kw in content.lower() for kw in keywords):
            if file_path not in matched_nodes and len(matched_nodes) < 15:
                matched_nodes.append(file_path)
    
    # 4. Final Answer Assembly
    if "remove" in question or "delete" in question:
        for node in matched_nodes:
            # Look for nodes that depend on or are contained by this
            impact_res = await analyze_impact(ImpactRequest(analysis_id=body.analysis_id, node_id=node))
            count = len(impact_res["impacted_nodes"])
            if count > 1:
                answer_parts.insert(0, f"⚠️ WARNING: Removing '{node.split('/')[-1]}' is a high-risk action. It has a blast radius of {count} nodes (internal symbols and external dependencies).")

    if not answer_parts:
        if "auth" in question or "login" in question or "user" in question:
            auth_files = [f for f in matched_nodes if any(k in f.lower() for k in ["auth", "login", "user", "session"])]
            if auth_files:
                answer_parts.append(f"I found {len(auth_files)} files related to authentication: {', '.join([f.split('/')[-1] for f in auth_files[:3]])}.")
        elif "database" in question or "db" in question or "sql" in question:
            db_files = [f for f in matched_nodes if f.endswith('.sql') or "db" in f.lower() or "schema" in f.lower()]
            if db_files:
                answer_parts.append(f"Database logic seems to be in: {', '.join([f.split('/')[-1] for f in db_files[:3]])}.")

    # Neural Search using ai_service
    graph_context = f"Matched files: {', '.join(matched_nodes[:10])}. Files analyzed: {len(code_map)}."
    ai_answer = ai_service.answer_query(body.question, graph_context)
    if ai_answer:
        answer_parts.insert(0, f"🤖 ARCHITECT BRAIN:\n{ai_answer}")

    return {
        "answer": "\n\n".join(answer_parts) if answer_parts else "I found some relevant files. Check them out in the graph!",
        "matched_nodes": matched_nodes[:15]
    }

# ===========================================================================
# GITHUB ANALYZER ENDPOINTS (Unified Port 8000)
# ===========================================================================

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/analyze-github")
async def analyze_github(body: AnalyzeRequest):
    t0 = time.time()
    try:
        # Step 1: Parse URL + get repo info
        url_data = github_service.parse_github_url(body.github_url)
        repo_info = github_service.get_repo_info(url_data["owner"], url_data["repo"], body.github_token)
        branch = url_data.get("branch") or repo_info.get("default_branch")
        
        # Step 2: Get all files + contents in parallel
        repo_files = await github_service.get_all_files(url_data["owner"], url_data["repo"], branch, body.github_token)
        
        # Step 3: Build dependency graph
        analysis_results = analyzer.analyze_repository(repo_files)
        
        # Step 4: Build response & store session
        repo_meta = {
            "owner": url_data["owner"],
            "repo": url_data["repo"],
            "branch": branch,
            "full_name": repo_info["full_name"],
            "github_url": body.github_url,
            "stars": repo_info["stargazers_count"],
            "language": repo_info["language"],
            "description": repo_info["description"]
        }

        analysis_id = f"gh-{os.urandom(4).hex()}"
        session_data = {
            "analysis_id": analysis_id,
            "nodes": analysis_results["nodes"],
            "edges": analysis_results["edges"],
            "repo_meta": repo_meta,
            "repo_files": repo_files,
            "code_map": {f["path"]: f.get("content", "") for f in repo_files}
        }
        SESSION_STORE[analysis_id] = session_data
        
        # Backwards compat for URL-based lookup
        safe_url = body.github_url.replace("https://", "").replace("/", "-").replace(".", "-")
        SESSION_STORE[safe_url] = session_data

        return {
            "analysis_id": analysis_id,
            "repo_meta": repo_meta,
            "nodes": analysis_results["nodes"],
            "edges": analysis_results["edges"],
            "stats": analysis_results["stats"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def api_query(body: QueryRequest):
    try:
        analysis_id = body.analysis_id or (body.repo_meta and body.repo_meta.get("analysis_id"))
        github_url = body.repo_meta.get("github_url") if body.repo_meta else None
        
        session = SESSION_STORE.get(analysis_id) or (github_url and SESSION_STORE.get(github_url))
        if not session:
            answer = ai_service.gh_answer_query(body.question, "Context: General codebase question.")
            return {"answer": answer, "impact": None}

        nodes = session.get("nodes", [])
        
        # Extract filename
        file_match = re.search(r'([a-zA-Z0-9_\-./]+\.(?:py|js|ts|jsx|tsx|html|css|sql|vue))', body.question)
        target_file = file_match.group(1) if file_match else (body.file_name or "unknown")

        # Build affected_files
        affected_files = []
        for node in nodes:
            if any(target_file in imp for imp in node.get("imports", [])):
                affected_files.append({
                    "name": node["name"],
                    "path": node["path"],
                    "layer": node.get("layer", "UNKNOWN")
                })

        if not affected_files and target_file:
            exact_targets = [n for n in nodes if n.get("name") == target_file or n.get("path", "").endswith(target_file)]
            if exact_targets:
                primary = exact_targets[0]
                affected_files.append({"name": primary["name"], "path": primary["path"], "layer": primary.get("layer", "UNKNOWN")})
                target_dir = primary["path"].rsplit("/", 1)[0] if "/" in primary["path"] else ""
                sibling_nodes = [n for n in nodes if n.get("path") != primary["path"] and (not target_dir or n.get("path", "").startswith(f"{target_dir}/"))]
                for sib in sibling_nodes[:4]:
                    affected_files.append({"name": sib["name"], "path": sib["path"], "layer": sib.get("layer", "UNKNOWN")})
            else:
                stem = os.path.splitext(target_file)[0].lower()
                fuzzy_nodes = [n for n in nodes if stem and stem in n.get("name", "").lower()]
                for n in fuzzy_nodes[:5]:
                    affected_files.append({"name": n["name"], "path": n["path"], "layer": n.get("layer", "UNKNOWN")})

        impact_data = ai_service.gh_explain_impact(target_file, affected_files)
        return {
            "answer": impact_data.get("summary", "Analysis complete."),
            "impact": impact_data,
            "affected_files": affected_files,
            "matched_nodes": [target_file]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/impact")
async def api_impact(body: ImpactRequest):
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    
    session = SESSION_STORE[body.analysis_id]
    nodes = session["nodes"]
    edges = session["edges"]
    
    impacted_ids = {body.node_id}
    queue = [body.node_id]
    while queue:
        current = queue.pop(0)
        for edge in edges:
            if edge["target"] == current and edge["source"] not in impacted_ids:
                impacted_ids.add(edge["source"])
                queue.append(edge["source"])
    
    target_node = next((n for n in nodes if n["id"] == body.node_id), None)
    target_name = target_node["name"] if target_node else body.node_id
    
    affected_list = []
    for node in nodes:
        if node["id"] in impacted_ids and node["id"] != body.node_id:
            affected_list.append({
                "name": node["name"],
                "path": node["path"],
                "layer": node.get("layer", "UNKNOWN")
            })
            
    impact_data = ai_service.gh_explain_impact(target_name, affected_list)
    return {
        "impacted_nodes": list(impacted_ids),
        "risk_level": impact_data.get("risk_level", "MEDIUM"),
        "risk_score": impact_data.get("risk_score", 5),
        "summary": impact_data.get("summary", ""),
        "bullets": impact_data.get("bullets", [])
    }

@app.post("/api/suggest-fix")
async def api_suggest_fix(body: SuggestFixRequest):
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    
    session = SESSION_STORE[body.analysis_id]
    nodes = session["nodes"]
    repo_files = session.get("repo_files", [])
    
    target_node = next((n for n in nodes if n["id"] == body.node_id), None)
    if not target_node:
        return {"suggestions": ["Node not found."]}
        
    path = target_node.get("path")
    file_entry = next((f for f in repo_files if f["path"] == path), None)
    content = file_entry["content"] if file_entry else "Source unavailable."
    
    intent = f"Review and suggest improvements for {target_node['name']} ({target_node.get('layer', 'code')})"
    suggestions = [
        f"Review '{target_node['name']}' for potential circular dependencies.",
        f"Ensure appropriate unit tests are in place for the {target_node.get('layer', 'backend')} layer."
    ]
    
    context_files = {path: content} if path else {}
    patches = ai_service.gh_generate_patches(intent, context_files, [{"name": target_node["name"], "path": path}])
    
    for p in patches[:2]:
        suggestions.append(f"FIX: {p['reason']}\n\nPath: {p['file_path']}\nChange: '{p['original'][:40]}...' -> '{p['replacement'][:40]}...'")

    return {"suggestions": suggestions}

@app.post("/api/generate-patches")
async def generate_patches_endpoint(body: PatchRequest):
    github_url = body.repo_meta.get("github_url")
    if not github_url or github_url not in SESSION_STORE:
        raise HTTPException(status_code=400, detail="Graph context missing. Analyze repo first.")

    nodes = SESSION_STORE[github_url]["nodes"]
    file_contents = {}

    for affected in body.affected_files:
        path = affected.get("path")
        matching_node = next((n for n in nodes if n["path"] == path), None)
        if matching_node:
            download_url = matching_node.get("download_url")
            if download_url:
                content = github_service.get_file_content(download_url)
                file_contents[path] = content

    patches = ai_service.gh_generate_patches(body.intent, file_contents, body.affected_files)
    return {"patches": patches}

@app.post("/api/create-pr")
async def create_pr_endpoint(body: PRRequest):
    meta = body.repo_meta
    try:
        result = pr_service.create_pr_from_patches(
            owner=meta["owner"],
            repo=meta["repo"],
            base_branch=meta["branch"],
            patches=body.patches,
            intent=body.intent
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Endpoint 5 — Suggested fixes  (POST /suggest-fix)  [skeleton for Dev 2/3]
# ---------------------------------------------------------------------------
@app.post("/suggest-fix")
async def suggest_fixes(body: SuggestFixRequest):
    """Provides context-aware architectural fixes based on node impact."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")
    
    session_data = SESSION_STORE[body.analysis_id]
    nodes = session_data.get("nodes", [])
    
    # Find the target node
    target_node = next((n for n in nodes if n["id"] == body.node_id), None)
    if not target_node:
        return {"suggestions": ["Node not found in current analysis."]}

    # Performance impact analysis for suggestion context
    impact_res = await analyze_impact(ImpactRequest(analysis_id=body.analysis_id, node_id=body.node_id))
    blast_radius = len(impact_res.get("impacted_nodes", []))
    
    node_class = target_node["data"].get("nodeClass", "code")
    node_layer = target_node["data"].get("layer", "backend")
    node_name = target_node["data"].get("label", "entity")

    suggestions = []

    # 1. Structural / Layer Suggestions
    if blast_radius > 10:
        suggestions.append(f"⚠️ HIGH RISK:\n{node_name} is a central hub. Consider decoupling into smaller sub-modules to reduce blast radius.")
    
    if node_layer == "database":
        suggestions.append(f"🛠️ DB OPTIMIZATION:\nEnsure '{node_name}' has appropriate indexing to handle cross-layer queries from {blast_radius} dependent nodes.")
        suggestions.append("🔍 INTEGRITY:\nVerify that foreign key constraints reflect the relationships shown in the dependency graph.")
    
    elif node_class == "route":
        suggestions.append(f"🌐 API DESIGN:\nAdd request throttling to '{node_name}' as it exposes your system to multiple entry points.")
        suggestions.append("🛡️ SECURITY:\nImplement strict JWT or Session validation before processing logic for this endpoint.")

    elif node_class == "function":
        suggestions.append(f"⚡ COMPOSITION:\nThis function affects {blast_radius} nodes. Consider using the 'Strategy Pattern' to make the logic more modular.")
        suggestions.append("🧪 TESTING:\nSince this is a core logic node, ensure unit tests cover at least 90% of its internal branches.")

    else:
        suggestions.append(f"📦 REFACTORING:\nReview '{node_name}' for circular dependencies. It currently sits in a chain of {blast_radius} connected objects.")

    # AI-Powered Architectural Explanations and Patches (ai_service)
    affected_files = impact_res.get("impacted_nodes", [])
    
    # 1. Impact Explanation
    explanation = ai_service.explain_impact(node_name, affected_files)
    if explanation:
        suggestions.append(f"🔍 ARCHITECT IMPACT:\n{explanation}")

    # 2. Suggested Patches
    intent = f"Refactor or fix {node_name} considering it affects {len(affected_files)} components."
    # Pass first 1-2 lines of content for context
    file_path = target_node["id"]
    content_snippet = session_data["code_map"].get(file_path, "Content not available")[:500]
    
    patches = ai_service.generate_patches(intent, content_snippet, affected_files)
    if patches:
        for p in patches[:1]: # Limit to 1 patch for readability in suggestions for now
            suggestions.append(f"🛠️ SUGGESTED PATCH in {p.get('file_path')}:\n\nReplace: '{p.get('original')[:50]}...' with '{p.get('replacement')[:50]}...'\nReason: {p.get('reason')}")

    return {
        "suggestions": suggestions
    }

