import os
import re

def classify_layer(file_path: str, content: str) -> str:
    """
    Rules:
    DATABASE > API > BACKEND > FRONTEND
    """
    path_lower = file_path.lower()
    content_lower = content.lower()
    ext = os.path.splitext(path_lower)[1]

    # 1. DATABASE
    if ext == ".sql" or \
       any(k in content for k in ["CREATE TABLE", "CREATE INDEX"]) or \
       any(k in content_lower for k in ["sqlite3", "sqlalchemy", "psycopg2"]) or \
       any(k in path_lower for k in ["model", "schema", "migration"]):
        return "database"

    # 2. API
    if any(k in content_lower for k in [
        "@app.get", "@app.post", "@app.put", "@app.delete",
        "@router.get", "@router.post", "@router.put", "@router.delete",
        "apirouter(", "router.", "app.use(", "fetch(", "axios."
    ]):
        return "api"

    # 3. BACKEND
    if ext == ".py" and any(k in content_lower for k in [
        "from fastapi", "import flask", "import django", "import express",
        "@app.route", "def get_", "def post_", "class ", "async def "
    ]):
        return "backend"

    # 4. FRONTEND
    if ext in [".html", ".jsx", ".tsx", ".ts", ".vue", ".css"]:
        return "frontend"
    if ext == ".js" and any(k in path_lower for k in ["frontend", "src", "components", "pages"]):
        return "frontend"

    return "backend"

def extract_imports(file_path: str, content: str) -> list:
    """
    Extract relative imports (starting with . or /)
    """
    imports = []
    ext = os.path.splitext(file_path.lower())[1]

    if ext == ".py":
        # Match 'from . import ...', 'from .module import ...', 'from ..module import ...'
        py_from_pattern = re.compile(r'from\s+((?:\.+|)[a-zA-Z0-9_\.]+)\s+import')
        for match in py_from_pattern.finditer(content):
            imports.append(match.group(1))
            
    elif ext in [".js", ".ts", ".jsx", ".tsx", ".vue"]:
        # Match from "...", import "...", require("...")
        # Handle relative (./, ../), absolute (/), and alias (@/) imports
        js_import_pattern = re.compile(r'(?:import|from|require)\s*\(?\s*["\']((?:\.|\/|@)[^"\']+)["\']')
        for match in js_import_pattern.finditer(content):
            imports.append(match.group(1))

    elif ext == ".html":
        html_src_pattern = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']')
        for match in html_src_pattern.finditer(content):
            src = match.group(1)
            if not src.startswith("http") and not src.startswith("//"):
                imports.append(src)

    return imports

def analyze_repository(files: list) -> dict:
    """
    Uses pre-fetched file['content'] — no HTTP calls needed.
    Step 1: Build nodes from file content
    Step 2: Build edges from imports
    """
    nodes = []
    stats = {
        "total_files": 0,
        "by_layer": {"database": 0, "backend": 0, "api": 0, "frontend": 0}
    }

    # Step 1: Nodes (content is already fetched)
    for file_info in files:
        path = file_info["path"]
        content = file_info.get("content", "")
        layer = classify_layer(path, content)
        line_count = len(content.splitlines()) if content else 0
        
        node = {
            "id": path,
            "name": file_info["name"],
            "path": path,
            "layer": layer,
            "lines": line_count,
            "imports": extract_imports(path, content),
            "download_url": file_info.get("download_url")
        }
        nodes.append(node)
        
        stats["total_files"] += 1
        stats["by_layer"][layer] += 1

    # Step 2: Edges (fuzzy import matching)
    edges = []
    seen_edges = set()

    for node in nodes:
        for imp in node.get("imports", []):
            # Clean the import: strip ./ ../ and get the last segment
            imp_clean = imp.replace('./', '').replace('../', '').split('/')[-1]
            imp_clean = imp_clean.replace('.py', '').replace('.js', '').replace('.ts', '')
            imp_clean = imp_clean.replace('.jsx', '').replace('.tsx', '').replace('.vue', '')

            if not imp_clean:
                continue

            for other_node in nodes:
                if other_node["id"] == node["id"]:
                    continue

                other_name = other_node["name"]
                other_name_clean = other_name.replace('.py', '').replace('.js', '').replace('.ts', '')
                other_name_clean = other_name_clean.replace('.jsx', '').replace('.tsx', '').replace('.vue', '')

                matched = False

                # Exact name match (case-insensitive)
                if imp_clean.lower() == other_name_clean.lower():
                    matched = True
                # Partial path match
                elif imp_clean.lower() in other_node["path"].lower():
                    matched = True

                if matched:
                    edge_key = f"{node['id']}->{other_node['id']}"
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append({
                            "id": edge_key,
                            "source": node["id"],
                            "target": other_node["id"],
                            "type": "IMPORTS"
                        })
                    break

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": stats
    }
