# IMPLEMENTATION_PLAN.md

## Build target
Deliver a stable hackathon MVP in **14 hours or less**.

Primary goal:
- a deterministic working pipeline
- a clean demo
- zero embarrassing crashes

Secondary goal:
- add one or two wow-features after the core path is stable

---

## 1. Team ownership
### Developer 1 — Ingestion + scanner
Owns:
- `backend/ingestion/zip_handler.py`
- `backend/ingestion/file_scanner.py`
- upload endpoint skeleton

Deliverables:
- ZIP upload handling
- temporary extraction
- ignored directory filtering
- extension filtering
- file list output
- clean summary of parsed / skipped files

Output contract:
```json
{
  "files_to_parse": ["backend/user_service.py", "frontend/ProfilePage.tsx", "database/schema.sql"],
  "skipped": 12,
  "supported": 23
}
```

---

### Developer 2 — Entity extraction + entity index
Owns:
- `backend/extraction/python_extractor.py`
- `backend/extraction/js_extractor.py`
- `backend/extraction/sql_extractor.py`
- `backend/extraction/entity_index.py`

Deliverables:
- extract SQL entities
- extract Python entities
- extract JS/TS entities
- merge all extracted entities into a unified index

Output contract:
```json
{
  "tables": [],
  "columns": [],
  "foreign_keys": [],
  "views": [],
  "imports": [],
  "routes": [],
  "field_refs": [],
  "functions": [],
  "classes": [],
  "http_calls": [],
  "api_calls": [],
  "components": []
}
```

---

### Developer 3 — Graph + impact engine
Owns:
- `backend/graph/graph_model.py`
- `backend/graph/node_builder.py`
- `backend/graph/edge_builder.py`
- `backend/impact/traversal.py`
- `backend/impact/scoring.py`

Deliverables:
- structured nodes
- rule-based edges
- graph JSON
- traversal-based impact analysis
- risk score calculation

Output contracts:

#### Graph response
```json
{
  "nodes": [],
  "edges": []
}
```

#### Impact response
```json
{
  "changed_node": "users.email",
  "impacted_nodes": [],
  "risk_score": 8,
  "severity": "HIGH"
}
```

---

### Developer 4 — Frontend + integration
Owns:
- `frontend/src/components/*`
- `frontend/src/graph/*`
- `frontend/src/api/*`
- graph visualization
- upload page
- impact panel
- natural-language query input
- suggested fixes panel

Deliverables:
- upload UI
- analysis summary UI
- React Flow graph page
- impact simulation UI
- risk score display
- NL query UI
- suggested fixes UI

---

## 2. Hard integration contracts
These contracts must be agreed immediately and should not change unless absolutely necessary.

### Endpoint 1 — Upload repo
`POST /upload`

Response:
```json
{
  "analysis_id": "session-001",
  "files_parsed": 31,
  "files_skipped": 9,
  "message": "Analysis initialized"
}
```

### Endpoint 2 — Build graph
`POST /graph`

Response:
```json
{
  "nodes": [],
  "edges": [],
  "summary": {
    "nodes": 28,
    "edges": 21
  }
}
```

### Endpoint 3 — Impact analysis
`POST /impact`

Request:
```json
{
  "analysis_id": "session-001",
  "node_id": "users.email"
}
```

Response:
```json
{
  "changed_node": "users.email",
  "impacted_nodes": [],
  "risk_score": 8,
  "severity": "HIGH",
  "explanation": "..."
}
```

### Endpoint 4 — Natural-language query
`POST /query`

Request:
```json
{
  "analysis_id": "session-001",
  "question": "Where is users.email used?"
}
```

Response:
```json
{
  "answer": "...",
  "matched_nodes": []
}
```

### Endpoint 5 — Suggested fixes
`POST /suggest-fix`

Request:
```json
{
  "analysis_id": "session-001",
  "node_id": "users.email",
  "change": "users.email_address"
}
```

Response:
```json
{
  "suggestions": [
    {
      "target": "user_service.py",
      "suggestion": "Update field reference from user.email to user.email_address"
    }
  ]
}
```

---

## 3. 14-hour execution schedule

### Hour 0–1.0
**All 4 members together**
- create repo
- create folder structure
- create branches
- freeze API contracts
- add sample demo repo
- set up FastAPI + React skeleton

### Hour 1.0–3.0
**Dev 1**
- ZIP upload
- temp extraction
- scanner rules

**Dev 2**
- SQL extractor
- Python extractor skeleton
- JS extractor skeleton

**Dev 3**
- graph node/edge schema
- graph builder skeleton
- traversal skeleton

**Dev 4**
- upload page
- basic layout
- graph page shell

### Hour 3.0–5.0
**Dev 1**
- scanner summary
- graceful skip logic

**Dev 2**
- finish extraction logic for all 3 languages
- build entity index

**Dev 3**
- implement rule-based edge generation
- implement impact traversal
- start scoring

**Dev 4**
- React Flow setup
- API client functions
- analysis summary panel

### Hour 5.0–7.0
**Integration checkpoint #1**
Goal:
```text
upload → scan → extract → build graph
```

Mandatory output by end of this block:
- graph JSON generated from demo repo
- graph visible in UI

If this is not working by hour 7, kill all non-core ambitions.

### Hour 7.0–9.0
**Dev 1**
- harden scanner
- enforce performance limits

**Dev 2**
- fix extractor bugs
- improve field-reference extraction

**Dev 3**
- finalize scoring model
- create impact response format

**Dev 4**
- impact simulation UI
- node click handling
- risk score display

### Hour 9.0–10.5
**Integration checkpoint #2**
Goal:
```text
click node → impact result → risk score
```

Mandatory output:
- select node
- impacted nodes highlighted
- risk score shown

### Hour 10.5–12.0
Build wow features only after core path is stable.

**Dev 2 + Dev 3**
- wire NL query backend
- wire suggestion backend

**Dev 4**
- NL query input
- suggested fixes panel

**Dev 1**
- hidden debug mode
- cleanup and reliability hardening

### Hour 12.0–13.0
**Integration checkpoint #3**
Goal:
- full demo path stable
- no user-visible crashes
- partial-analysis mode works

### Hour 13.0–14.0
Only do:
- bug fixing
- UI cleanup
- demo rehearsal
- judge pitch prep

Do not add new features in the final hour.

---

## 4. Git workflow
### Branch strategy
- `main` → stable only
- `dev` → integration branch
- `feature/ingestion`
- `feature/extraction`
- `feature/graph-impact`
- `feature/frontend`

### Rules
- never push directly to `main`
- merge into `dev` frequently
- integration check every 2–3 hours
- each developer commits in small chunks
- breakages are fixed immediately, not postponed

---

## 5. MVP freeze rules
The following are **must-have**:
- upload repo
- scan files
- extract entities
- build graph
- display graph
- impact simulation
- risk score
- graceful degradation

The following are **only after MVP is stable**:
- natural language query
- suggested fixes
- debug panel

The following are **deferred backlog only**:
- code patch generation
- GitHub repo link primary mode
- PR analyzer
- deep semantic graph enrichment

---

## 6. Demo repo requirements
Your prepared demo repo must include:
- one SQL schema file
- 2–3 Python backend files
- at least 1 API route
- 1–2 frontend components
- one obvious field chain such as:

```text
users.email
→ user_service.py
→ GET /profile
→ ProfilePage.tsx
```

This demo chain must work flawlessly.

---

## 7. Demo script sequence
1. Upload demo repo
2. Show analysis summary
3. Render dependency graph
4. Click `users.email`
5. Run change simulation
6. Show impacted nodes
7. Show risk score
8. Ask: `Where is users.email used?`
9. Show suggested fixes
10. Mention optional ZIP upload for other repos

---

## 8. Emergency fallback plan
If things start failing, use this fallback order.

### Keep at all costs
- graph generation
- impact traversal
- risk score
- stable UI

### Drop if needed
- natural-language query
- suggested fixes
- debug UI polish

### Never sacrifice
- demo stability
- graceful degradation
- clean output

---

## 9. Definition of done
The project is ready when all of the following are true:
- demo repo analysis works end-to-end
- graph renders correctly
- selecting a node highlights impacted downstream nodes
- risk score appears
- unsupported files do not crash analysis
- output remains clean for user-uploaded partial repos
- team can demo the full story in under 3 minutes
