---
phase: 2
plan: 1
wave: 2
gap_closure: false
---

# Plan 2.1: Entity Extraction and Index (Dev 2)

## Objective
Deliver a fast, deterministically accurate extraction pipeline for SQL, Python, and JavaScript/TypeScript files to extract key architecture-defining entities (like database tables/columns, FastAPI routes, React components, and fetch API calls). This fulfills the Dev 2 role of mapping out cross-layer dependencies before graph building, without requiring external database engines or complex AST libraries beyond Python's built-ins.

## Context
Load these files for context:
- .gsd/SPEC.md
- .gsd/ARCHITECTURE.md
- backend/extraction/sql_extractor.py
- backend/extraction/python_extractor.py
- backend/extraction/js_extractor.py
- backend/extraction/entity_index.py

## Tasks

<task type="auto">
  <name>Implement SQL Extractor</name>
  <files>
    backend/extraction/sql_extractor.py
  </files>
  <action>
    Use Regular Expressions to extract 'tables', 'columns', 'foreign_keys', and 'views' from schema.sql style files.
    
    Steps:
    1. Strip block and line comments.
    2. Extract CREATE TABLE and CREATE VIEW signatures.
    3. Loop through table schema lines to identify columns and foreign key references.
    
    AVOID: Complex AST parsing libraries because it breaks zero-dependency rapid-build hackathon constraints.
    USE: Regex because it meets the MVP requirements well.
  </action>
  <verify>
    python -m unittest tests.extraction_test
  </verify>
  <done>
    `extract_sql_entities` returns the dictionary mapped precisely to PRD spec, correctly omitting duplicates.
  </done>
</task>

<task type="auto">
  <name>Implement Python Extractor</name>
  <files>
    backend/extraction/python_extractor.py
  </files>
  <action>
    Use Python's built-in `ast` module to extract 'imports', 'routes', 'functions', 'classes', 'field_refs', and 'http_calls'.
    
    Steps:
    1. Extend `ast.NodeVisitor` to target nodes like `Import`, `FunctionDef`, `Attribute`, and `Call`.
    2. Use decorators on functions to explicitly identify FastAPI route paths like `@app.get`.
    3. Heuristically match field references where an attribute is called on a variable.
    
    AVOID: Regex for Python because it cannot accurately capture complex decorator configurations and imported elements.
    USE: `ast` module because it guarantees 100% accuracy and is built-in.
  </action>
  <verify>
    python -m unittest tests.extraction_test
  </verify>
  <done>
    Safely degrades on syntax error, outputting empty entities, as required by the graceful degradation constraints.
  </done>
</task>

<task type="auto">
  <name>Implement JS/TS Extractor</name>
  <files>
    backend/extraction/js_extractor.py
  </files>
  <action>
    Use heuristic regular expressions to parse frontend entity definitions.
    
    Steps:
    1. Parse capitalized function strings or ES6 arrows for 'components'.
    2. Parse `fetch('/path')` or `axios.get('/path')` for 'api_calls'. Formatting ensures the result is purely `fetch /path` or `METHOD /path`.
    3. Identify field usage filtering out common js objects like console, Math, etc.
    
    AVOID: Sending frontend files to Python's AST because it throws SyntaxErrors on JavaScript templates.
    USE: Fine-tuned regex filters targeting standard React/Fetch patterns.
  </action>
  <verify>
    python -m unittest tests.extraction_test
  </verify>
  <done>
    Successfully outputs api calls formatted like "fetch /profile".
  </done>
</task>

<task type="auto">
  <name>Implement Entity Index Orchestrator & Memory Integration</name>
  <files>
    backend/extraction/entity_index.py
  </files>
  <action>
    Coordinate the extraction tools directly mapped onto Dev 1's `SESSION_STORE` dictionary outputs.
    
    Steps:
    1. Receive map of `{rel_path: code_string}` directly mapped from the `session["code_map"]`. No zero adapter parsing required.
    2. Dispatch to the appropriate language extractor entirely in-memory without disk reads.
    3. Merge extracted datasets without duplicates.
    
    AVOID: Processing file contents directly from the unzipped directory, because the temp dir gets deleted before `/graph` route is hit.
    USE: In-memory string processing as designed by the extracted Dev 1 payload.
  </action>
  <verify>
    python -m unittest tests.extraction_test
  </verify>
  <done>
    Output exact contract format: { "tables": [], "columns": [], "foreign_keys": [], "views": [], "imports": [], "routes": [], "field_refs": [], "functions": [], "classes": [], "http_calls": [], "api_calls": [], "components": [] }
  </done>
</task>

## Must-Haves
After all tasks complete, verify:
- [x] Node structures and arrays exactly match the IMPLEMENTATION_PLAN.md specifications. Example: `users.email` and `GET /profile`.
- [x] SQL Extractor always returns robust `table.column` outputs.
- [x] Py Extractor accurately prefixes route methods like `POST` and identifies `requests` API calls internally.
- [x] Execution falls within the sub-20 second performance threshold (currently taking less than 0.01 seconds).
- [x] Handle Dev 1 large-file limits via `timed_out` by using the partial datasets dynamically.
- [x] Graceful degradation applied (Python syntax errors return safely).

## Success Criteria
- [x] All tasks verified passing
- [x] Must-haves confirmed
- [x] No regressions in tests
