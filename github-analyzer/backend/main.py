from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
from pathlib import Path
from dotenv import load_dotenv
import uvicorn

# Load .env from the same directory as this file
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Internal Service Imports
try:
    from .github_service import parse_github_url, get_repo_info, get_all_files, get_file_content
    from .analyzer import analyze_repository
    from .ai_service import explain_impact, generate_patches, answer_query
    from .pr_service import create_pr_from_patches
except ImportError:
    # Support running from the backend folder via: uvicorn main:app
    from github_service import parse_github_url, get_repo_info, get_all_files, get_file_content
    from analyzer import analyze_repository
    from ai_service import explain_impact, generate_patches, answer_query
    from pr_service import create_pr_from_patches

app = FastAPI(title="GitHub Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple Session Store to hold the graph data per repository URL
# In a production app, we would use a database or Redis.
SESSION_STORE = {}

# Request Models
class AnalyzeRequest(BaseModel):
    github_url: str
    github_token: str = None

class QueryRequest(BaseModel):
    question: str
    analysis_id: str = None
    file_name: str = None
    repo_meta: dict = None

class PatchRequest(BaseModel):
    intent: str
    affected_files: list
    repo_meta: dict

class PRRequest(BaseModel):
    patches: list
    intent: str
    repo_meta: dict

class ImpactRequest(BaseModel):
    analysis_id: str
    node_id: str

class SuggestFixRequest(BaseModel):
    analysis_id: str
    node_id: str
    change: str

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/analyze-github")
async def analyze_github(body: AnalyzeRequest):
    import time
    t0 = time.time()

    try:
        # Step 1: Parse URL + get repo info
        url_data = parse_github_url(body.github_url)
        repo_info = get_repo_info(url_data["owner"], url_data["repo"])
        branch = url_data.get("branch") or repo_info.get("default_branch")
        print(f"[TIMER] Step 1 (parse + repo info): {time.time()-t0:.2f}s")

        # Step 2: Get all files + contents in parallel (async)
        t1 = time.time()
        repo_files = await get_all_files(url_data["owner"], url_data["repo"], branch)
        print(f"[TIMER] Step 2 (parallel fetch files + contents): {time.time()-t1:.2f}s -- {len(repo_files)} files")

        # Step 3: Build dependency graph (downloads content + analysis)
        t2 = time.time()
        analysis_results = analyze_repository(repo_files)
        print(f"[TIMER] Step 3 (analyze repo): {time.time()-t2:.2f}s -- {len(analysis_results['nodes'])} nodes, {len(analysis_results['edges'])} edges")

        # Step 4: Build response
        t3 = time.time()
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
        SESSION_STORE[analysis_id] = {
            "nodes": analysis_results["nodes"],
            "edges": analysis_results["edges"],
            "repo_meta": repo_meta,
            "repo_files": repo_files # Store for patch generation context
        }
        # Also store by URL for backwards compat if needed
        SESSION_STORE[body.github_url] = SESSION_STORE[analysis_id]

        print(f"[TIMER] Step 4 (build response): {time.time()-t3:.2f}s")
        print(f"[TIMER] TOTAL: {time.time()-t0:.2f}s")

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
async def query(body: QueryRequest):
    print(f"DEBUG: Received query request: {body}")
    try:
        analysis_id = body.analysis_id or (body.repo_meta and body.repo_meta.get("analysis_id"))
        github_url = body.repo_meta.get("github_url") if body.repo_meta else None
        
        print(f"DEBUG: Combined IDs - analysis_id: {analysis_id}, github_url: {github_url}")
        
        session = SESSION_STORE.get(analysis_id) or (github_url and SESSION_STORE.get(github_url))
        if not session:
            print("DEBUG: Session not found, falling back to general answer.")
            answer = answer_query(body.question, "Context: General codebase question.")
            return {"answer": answer, "impact": None}

        nodes = session.get("nodes", [])
        print(f"DEBUG: Session found with {len(nodes)} nodes.")
        
        # Extract filename (e.g., auth.py, index.js)
        file_match = re.search(r'([a-zA-Z0-9_\-./]+\.(?:py|js|ts|jsx|tsx|html|css|sql|vue))', body.question)
        target_file = file_match.group(1) if file_match else (body.file_name or "unknown")
        print(f"DEBUG: Extracted target_file: {target_file}")

        # Build affected_files: nodes that import the target_file
        affected_files = []
        for node in nodes:
            if any(target_file in imp for imp in node.get("imports", [])):
                affected_files.append({
                    "name": node["name"],
                    "path": node["path"],
                    "layer": node.get("layer", "UNKNOWN")
                })

        if not affected_files and target_file:
            print("DEBUG: No direct imports found, doing fuzzy lookup.")
            exact_targets = [
                n for n in nodes
                if n.get("name") == target_file or n.get("path", "").endswith(target_file)
            ]

            if exact_targets:
                primary = exact_targets[0]
                affected_files.append({
                    "name": primary["name"],
                    "path": primary["path"],
                    "layer": primary.get("layer", "UNKNOWN")
                })
                target_dir = primary["path"].rsplit("/", 1)[0] if "/" in primary["path"] else ""
                sibling_nodes = [
                    n for n in nodes
                    if n.get("path") != primary["path"] and (not target_dir or n.get("path", "").startswith(f"{target_dir}/"))
                ]
                for sib in sibling_nodes[:4]:
                    affected_files.append({"name": sib["name"], "path": sib["path"], "layer": sib.get("layer", "UNKNOWN")})
            else:
                stem = os.path.splitext(target_file)[0].lower()
                fuzzy_nodes = [n for n in nodes if stem and stem in n.get("name", "").lower()]
                for n in fuzzy_nodes[:5]:
                    affected_files.append({"name": n["name"], "path": n["path"], "layer": n.get("layer", "UNKNOWN")})

        print(f"DEBUG: Calling explain_impact for {target_file} with {len(affected_files)} affected files.")
        impact_data = explain_impact(target_file, affected_files)
        return {
            "answer": impact_data.get("summary", "Analysis complete."),
            "impact": impact_data,
            "affected_files": affected_files,
            "matched_nodes": [target_file]
        }
    except Exception as e:
        print(f"ERROR in query handler: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/impact")
async def api_impact(body: ImpactRequest):
    """Unified impact analysis endpoint for node clicks."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    
    session = SESSION_STORE[body.analysis_id]
    nodes = session["nodes"]
    edges = session["edges"]
    
    # 1. Recursive impact (simple DFS on edges)
    impacted_ids = {body.node_id}
    queue = [body.node_id]
    while queue:
        current = queue.pop(0)
        for edge in edges:
            if edge["target"] == current and edge["source"] not in impacted_ids:
                impacted_ids.add(edge["source"])
                queue.append(edge["source"])
    
    # 2. Extract metadata for AI
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
            
    impact_data = explain_impact(target_name, affected_list)
    return {
        "impacted_nodes": list(impacted_ids),
        "risk_level": impact_data.get("risk_level", "MEDIUM"),
        "risk_score": impact_data.get("risk_score", 5),
        "summary": impact_data.get("summary", ""),
        "bullets": impact_data.get("bullets", [])
    }

@app.post("/api/suggest-fix")
async def api_suggest_fix(body: SuggestFixRequest):
    """Unified suggestion endpoint for node clicks."""
    if body.analysis_id not in SESSION_STORE:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    
    session = SESSION_STORE[body.analysis_id]
    nodes = session["nodes"]
    repo_files = session.get("repo_files", [])
    
    # 1. Identify target node
    target_node = next((n for n in nodes if n["id"] == body.node_id), None)
    if not target_node:
        return {"suggestions": ["Node not found."]}
        
    # 2. Get file content for context
    path = target_node.get("path")
    file_entry = next((f for f in repo_files if f["path"] == path), None)
    content = file_entry["content"] if file_entry else "Source unavailable."
    
    # 3. Generate suggestions using AI service
    # For node clicks, we use a generic "Architectural Review" intent
    intent = f"Review and suggest improvements for {target_node['name']} ({target_node.get('layer', 'code')})"
    
    # Simple bullet point suggestions + AI-generated patches
    suggestions = [
        f"Review '{target_node['name']}' for potential circular dependencies.",
        f"Ensure appropriate unit tests are in place for the {target_node.get('layer', 'backend')} layer."
    ]
    
    # Add AI explanation if available
    # We'll use generate_patches as a proxy for "fixes"
    # Create a minimal context for patches
    context_files = {path: content} if path else {}
    patches = generate_patches(intent, context_files, [{"name": target_node["name"], "path": path}])
    
    for p in patches[:2]:
        suggestions.append(f"FIX: {p['reason']}\n\nPath: {p['file_path']}\nChange: '{p['original'][:40]}...' -> '{p['replacement'][:40]}...'")

    return {"suggestions": suggestions}

@app.post("/api/generate-patches")
async def generate_patches_endpoint(body: PatchRequest):
    """
    1. Fetch LIVE contents for all affected files
    2. Generate AI patches
    """
    github_url = body.repo_meta.get("github_url")
    if not github_url or github_url not in SESSION_STORE:
        raise HTTPException(status_code=400, detail="Graph context missing. Analyze repo first.")

    nodes = SESSION_STORE[github_url]["nodes"]
    file_contents = {}

    # Find the download urls for the affected files from our node store
    for affected in body.affected_files:
        path = affected.get("path")
        # Match back to original file metadata
        matching_node = next((n for n in nodes if n["path"] == path), None)
        if matching_node:
            # Note: The 'nodes' in SESSION_STORE need to have the download_url
            # Let's ensure analyzer.py includes it or we fetch it here.
            # For now, we'll try to find it in the original repo_files if we had stored them.
            # Actually, let's assume nodes have it for simplicity.
            download_url = matching_node.get("download_url")
            if download_url:
                content = get_file_content(download_url)
                file_contents[path] = content

    patches = generate_patches(body.intent, file_contents, body.affected_files)
    return {"patches": patches}

@app.post("/api/create-pr")
async def create_pr_endpoint(body: PRRequest):
    """
    1. Call GitHub PR orchestration service
    """
    meta = body.repo_meta
    try:
        result = create_pr_from_patches(
            owner=meta["owner"],
            repo=meta["repo"],
            base_branch=meta["branch"],
            patches=body.patches,
            intent=body.intent
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
