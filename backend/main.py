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
from neo4j import GraphDatabase

app = FastAPI()

DEBUG_LOG_PATH = "debug_log.txt"

def log_debug(msg: str):
    with open(DEBUG_LOG_PATH, "a") as f:
        f.write(f"{msg}\n")
    print(msg) # Still print to terminal

# Clear log on startup
with open(DEBUG_LOG_PATH, "w") as f:
    f.write("=== Analysis Backend Debug Log ===\n")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
def parse_code_symbols(code_map: dict):
    """
    Extracts granular symbols (Classes, Functions, Endpoints) from the code map.
    """
    symbols = []
    symbol_edges = []
    
    # Regex patterns
    CLASS_PATTERN = re.compile(r'(?:class|export\s+class)\s+([a-zA-Z0-9_]+)')
    FUNC_PATTERN = re.compile(r'(?:def|async\s+def|function)\s+([a-zA-Z0-9_]+)')
    ENDPOINT_PATTERN = re.compile(r'@app\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')
    # HTML IDs and JS Constants/Variables for Vanilla JS
    HTML_ID_PATTERN = re.compile(r'id=["\']([^"\']+)["\']')
    JS_CONST_PATTERN = re.compile(r'(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=')

    for file_path, content in code_map.items():
        norm_path = file_path.replace('\\', '/')
        
        # 1. Classes
        for match in CLASS_PATTERN.finditer(content):
            name = match.group(1)
            symbol_id = f"{norm_path}::class::{name}"
            symbols.append({
                "id": symbol_id,
                "label": name,
                "type": "symbol",
                "kind": "class",
                "file": norm_path
            })
            symbol_edges.append({"source": norm_path, "target": symbol_id, "type": "CONTAINS"})

        # 2. Functions
        for match in FUNC_PATTERN.finditer(content):
            name = match.group(1)
            if name in ['main', 'app', 'function']: continue
            symbol_id = f"{norm_path}::func::{name}"
            symbols.append({
                "id": symbol_id,
                "label": name,
                "type": "symbol",
                "kind": "function",
                "file": norm_path
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
                    "file": norm_path
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
                    "file": norm_path
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
    x_debug_mode: Optional[str] = Header(None, alias="X-Debug-Mode"),
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

        # 6. Deep Analysis: Symbols & Endpoints
        symbols, symbol_edges = parse_code_symbols(code_map)
        
        nodes = []
        edges = []
        
        # File Nodes
        for file_path, content in code_map.items():
            normalized_path = file_path.replace('\\', '/')
            ext = os.path.splitext(normalized_path)[1].lower()
            
            # Smart Layer Assignment
            content_lower = content.lower()
            layer = "backend" 
            
            # Rule 1: API Layer (FastAPI takes precedence over DB)
            if 'from fastapi' in content_lower or 'import fastapi' in content_lower or '@app.' in content_lower:
                layer = "api"
            # Rule 2: Database Layer
            elif 'create table' in content_lower or 'sqlite3' in content_lower or ext == '.db' or ext == '.sql':
                layer = "database"
            # Rule 3: Frontend Layer
            elif ext == '.html' and '<script' in content_lower:
                layer = "frontend"
            elif ext in {'.py', '.js', '.ts', '.jsx', '.tsx', '.sql', '.html', '.db', '.css', '.json', '.md', '.txt'}:
                # If it's JS/TS but not in API/DB, and not explicitly backend-named, it's frontend
                if not any(k in normalized_path.lower() for k in ["backend", "server", "api"]):
                    layer = "frontend"
                else:
                    layer = "backend"
            
            # Default directory-based overrides
            if "frontend" in normalized_path.lower(): layer = "frontend"
            elif "api" in normalized_path.lower(): layer = "api"
            elif "database" in normalized_path.lower() or "db" in normalized_path.lower(): 
                if layer != "api": layer = "database"
            
            log_debug(f"Assigning {normalized_path} to layer: {layer}")
            
            nodes.append({
                "id": normalized_path,
                "type": "fileNode",
                "position": {"x": 0, "y": 0},
                "data": {
                    "label": normalized_path.split('/')[-1],
                    "fullPath": normalized_path,
                    "nodeClass": "database" if layer == "database" else "code",
                    "layer": layer,
                    "lines": len(content.split('\n'))
                }
            })

        # Symbol & Endpoint Nodes
        for s in symbols:
            # Shift symbols slightly to the right of their files
            parent_file = [n for n in nodes if n["id"] == s["file"]][0]
            nodes.append({
                "id": s["id"],
                "type": "fileNode",
                "position": {"x": parent_file["position"]["x"] + 150, "y": 0},
                "data": {
                    "label": s["label"],
                    "fullPath": s["id"],
                    "nodeClass": s["kind"],
                    "layer": parent_file["data"]["layer"],
                    "lines": 0
                }
            })


        # 8. Infer Databases from Code (even if .db file is missing)
        DB_CONNECT_PATTERN = re.compile(r'connect\(["\']([^"\']+\.db|[^"\']+)["\']\)|db\s*=\s*["\']([^"\']+)["\']')
        for file_path, content in code_map.items():
            for match in DB_CONNECT_PATTERN.finditer(content):
                db_name = match.group(1) or match.group(2)
                if db_name and not any(n["id"] == db_name for n in nodes):
                    log_debug(f"Inferred Database from code in {file_path}: {db_name}")
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

        log_debug("Starting comprehensive edge detection...")
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
                        log_debug(f"Link: {norm_src} calls API {target_node['id']}")

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
                        log_debug(f"Link: {norm_src} references {norm_tgt}")

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
                        log_debug(f"Link: {norm_src} imports {norm_tgt}")

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
            "code_map": code_map,
            "nodes": nodes,
            "edges": edges,
            "scan_summary": scan_results
        }

        return {
            "analysis_id": analysis_id,
            "files_parsed": scan_results["supported"],
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
    """Smarter query handling with Neo4j and content-aware search."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found. Upload a repo first.")

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

    if not answer_parts:
        if matched_nodes:
            answer_parts.append(f"I found {len(matched_nodes)} relevant files. Check them out in the graph!")
        else:
            answer_parts.append("I've searched the code and graph but couldn't find a direct answer. Try asking about specific keywords or dependencies.")

    return {
        "answer": " ".join(answer_parts),
        "matched_nodes": matched_nodes[:15]
    }


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
        suggestions.append(f"⚠️ HIGH RISK: '{node_name}' is a central hub. Consider decoupling into smaller sub-modules to reduce blast radius.")
    
    if node_layer == "database":
        suggestions.append(f"🛠️ DB OPTIMIZATION: Ensure '{node_name}' has appropriate indexing to handle cross-layer queries from {blast_radius} dependent nodes.")
        suggestions.append("🔍 INTEGRITY: Verify that foreign key constraints reflect the relationships shown in the dependency graph.")
    
    elif node_class == "route":
        suggestions.append(f"🌐 API DESIGN: Add request throttling to '{node_name}' as it exposes your system to multiple entry points.")
        suggestions.append("🛡️ SECURITY: Implement strict JWT or Session validation before processing logic for this endpoint.")

    elif node_class == "function":
        suggestions.append(f"⚡ COMPOSITION: This function affects {blast_radius} nodes. Consider using the 'Strategy Pattern' to make the logic more modular.")
        suggestions.append("🧪 TESTING: Since this is a core logic node, ensure unit tests cover at least 90% of its internal branches.")

    else:
        suggestions.append(f"📦 REFACTORING: Review '{node_name}' for circular dependencies. It currently sits in a chain of {blast_radius} connected objects.")

    return {
        "suggestions": suggestions
    }

