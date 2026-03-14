import os
from .sql_extractor import extract_sql_entities
from .python_extractor import extract_python_entities
from .js_extractor import extract_js_entities

def build_entity_index(files: dict[str, str]) -> dict:
    """
    Coordinates extraction across file contents.
    files: A dictionary mapping relative file paths to their string contents.
    Returns a unified entity dictionary matching the Dev 2 contract.
    """
    index = {
        "tables": set(),
        "columns": set(),
        "foreign_keys": set(),
        "views": set(),
        "imports": set(),
        "routes": set(),
        "field_refs": set(),
        "functions": set(),
        "classes": set(),
        "http_calls": set(),
        "api_calls": set(),
        "components": set()
    }

    for filepath, content in files.items():
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        
        if ext == ".sql":
            res = extract_sql_entities(content)
            index["tables"].update(res.get("tables", []))
            index["columns"].update(res.get("columns", []))
            index["foreign_keys"].update(res.get("foreign_keys", []))
            index["views"].update(res.get("views", []))
            
        elif ext == ".py":
            res = extract_python_entities(content)
            index["imports"].update(res.get("imports", []))
            index["routes"].update(res.get("routes", []))
            index["field_refs"].update(res.get("field_refs", []))
            index["functions"].update(res.get("functions", []))
            index["classes"].update(res.get("classes", []))
            index["http_calls"].update(res.get("http_calls", []))
            
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            res = extract_js_entities(content)
            index["api_calls"].update(res.get("api_calls", []))
            index["components"].update(res.get("components", []))
            index["field_refs"].update(res.get("field_refs", []))

    # Convert sets back to lists for JSON serialization
    return {k: list(v) for k, v in index.items()}
