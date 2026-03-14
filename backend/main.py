from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import shutil
import tempfile
import os
import uuid
import logging
from typing import List, Optional, Dict, Any

# Internal imports
from backend.ingestion.zip_handler import extract_zip, read_files_to_dict
from backend.ingestion.file_scanner import scan_directory
from backend.extraction.entity_index import build_entity_index
from backend.graph.node_builder import build_nodes
from backend.graph.edge_builder import build_edges
from backend.impact.traversal import find_impacted_nodes
from backend.impact.scoring import calculate_risk_score
from backend.graph.graph_model import Node, Edge, NodeType, Layer
from backend.database import init_db, get_db, NodeTable, EdgeTable, bulk_insert_graph
from backend.impact.telemetry import telemetry

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="IronMind Polyglot Intelligence API")

# feature/frontend: CORS Config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory session store (feature/ingestion)
# Key: analysis_id
# ---------------------------------------------------------------------------
SESSION_STORE: dict = {}

# PRD §8 hard limit
MAX_ZIP_SIZE_BYTES = 40 * 1024 * 1024  # 40 MB

@app.on_event("startup")
def on_startup():
    logger.info("Initializing persistent storage...")
    init_db()

# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------
class GraphRequest(BaseModel):
    analysis_id: str
    entities: Optional[Dict[str, Any]] = None

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
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "IronMind Polyglot Intelligence Backend is active"}

@app.get("/telemetry")
async def get_telemetry():
    """Exposes performance metrics for Dev 4 debug panel."""
    return {
        "stats": telemetry.stats,
        "recent_history": telemetry.history[-10:]
    }

@app.post("/upload")
async def upload_repo(
    file: UploadFile = File(...),
    x_debug_mode: Optional[str] = Header(default=None, alias="X-Debug-Mode"),
):
    """
    feature/ingestion: Accepts a ZIP repository upload and scans for entities.
    """
    debug = (x_debug_mode or "").lower() == "true"
    temp_zip_fd, temp_zip_path = tempfile.mkstemp(suffix=".zip", prefix="upload_")
    os.close(temp_zip_fd)

    with open(temp_zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        zip_size = os.path.getsize(temp_zip_path)
        if zip_size > MAX_ZIP_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"ZIP file too large ({zip_size // (1024 * 1024)} MB)."
            )

        try:
            extracted_repo_path = extract_zip(temp_zip_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        scan_results = scan_directory(extracted_repo_path)
        code_map = read_files_to_dict(extracted_repo_path, scan_results["files_to_parse"])

        analysis_id = f"session-{uuid.uuid4().hex[:8]}"
        SESSION_STORE[analysis_id] = {
            "code_map": code_map,
            "scan_summary": scan_results
        }

        response = {
            "analysis_id": analysis_id,
            "files_parsed": scan_results["supported"],
            "files_skipped": scan_results["skipped"],
            "message": "Analysis initialized"
        }

        if debug:
            response["debug_info"] = scan_results

        return response

    finally:
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)

@app.post("/graph")
async def build_graph(request: GraphRequest, db: Session = Depends(get_db)):
    """
    feature/graph: Transforms entities into a persistent structured graph.
    """
    if request.analysis_id not in SESSION_STORE and not request.entities:
        raise HTTPException(status_code=404, detail="analysis_id not found.")
    
    # Logic Merge: If entities aren't provided, extract them from the session's code_map
    if request.entities:
        entities = request.entities
    else:
        session = SESSION_STORE[request.analysis_id]
        code_map = session.get("code_map", {})
        entities = build_entity_index(code_map)
        session["entities"] = entities
    
    try:
        nodes = build_nodes(entities)
        edges = build_edges(nodes, entities)
        
        # Prepare for persistent bulk insert
        nodes_data = [
            {"id": n.id, "name": n.name, "type": n.type.value, "layer": n.layer.value, "metadata_json": n.metadata}
            for n in nodes
        ]
        edges_data = [
            {"id": f"{e.source}->{e.target}", "source": e.source, "target": e.target, 
             "type": e.type, "confidence": e.confidence, "metadata_json": e.metadata}
            for e in edges
        ]

        bulk_insert_graph(db, nodes_data, edges_data)
        
        return {
            "nodes": [n.dict() for n in nodes],
            "edges": [e.dict() for e in edges],
            "summary": {"nodes": len(nodes), "edges": len(edges)}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/impact")
async def impact_analysis(request: ImpactRequest, db: Session = Depends(get_db)):
    """
    feature/graph: Performs downstream impact analysis using BFS and persistent storage.
    """
    if request.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="analysis_id not found.")

    try:
        db_nodes = db.query(NodeTable).all()
        db_edges = db.query(EdgeTable).all()

        if not db_nodes:
            raise HTTPException(status_code=400, detail="Graph not built yet.")
        
        nodes = [Node(id=dn.id, name=dn.name, type=NodeType(dn.type), layer=Layer(dn.layer), metadata=dn.metadata_json) for dn in db_nodes]
        edges = [Edge(source=de.source, target=de.target, type=de.type, confidence=de.confidence, metadata=de.metadata_json) for de in db_edges]

        impacted = find_impacted_nodes(request.node_id, nodes, edges)
        result = calculate_risk_score(impacted)
        
        return {
            "changed_node": request.node_id,
            "impacted_nodes": impacted,
            "risk_score": result["risk_score"],
            "severity": result["severity"],
            "explanation": result["explanation"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in impact analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def natural_language_query(body: QueryRequest):
    """feature/extraction + feature/graph: placeholder for NL engine."""
    return {"answer": "Dependency mapping verified.", "matched_nodes": []}

@app.post("/suggest-fix")
async def suggest_fixes(body: SuggestFixRequest):
    """feature/extraction: placeholder for textual recommendations."""
    return {"suggestions": ["Update field reference in backend code."]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

