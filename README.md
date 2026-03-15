# Polyglot Dependency Impact Analyzer

## One-line pitch
A GenAI-assisted developer intelligence tool that analyzes polyglot repositories, maps cross-layer dependencies across **SQL → Python → API → JS/TS**, and simulates **change impact** before deployment.

---

## Getting Started

### Architecture
This application consists of three components:
- **Main Backend** (FastAPI) - Port 8000
- **GitHub Analyzer Backend** (FastAPI) - Port 8001
- **Frontend** (React + Vite) - Port 5173

### Installation

#### 1. Main Backend (Port 8000)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### 2. GitHub Analyzer Backend (Port 8001)
```bash
cd github-analyzer/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

#### 3. Frontend (Port 5173)
```bash
cd frontend
npm install
npm run dev
```

The application will be available at `http://localhost:5173`

### Usage

#### Option 1: ZIP Upload
1. Navigate to `http://localhost:5173`
2. Upload a repository ZIP file (max 40MB)
3. View the dependency graph, impact analysis, and AI suggestions

#### Option 2: GitHub URL
1. Navigate to `http://localhost:5173`
2. Enter a GitHub repository URL (e.g., `github.com/owner/repo`)
3. Optionally provide a GitHub token for private repos and PR creation
4. Use the **Consequence Engine** panel to:
   - Analyze impact of changes
   - Generate patches with AI assistance
   - Create Pull Requests directly to GitHub

---

## Hackathon objective
Build a stable MVP in **14 hours** that can:
- accept a ZIP repository upload
- scan supported files only
- extract entities from SQL, Python, and JS/TS
- build a dependency graph
- simulate change impact
- calculate a risk score
- answer natural-language dependency questions
- provide textual suggested fixes

---

## Supported stack
### Languages
- Python
- JavaScript / TypeScript
- SQL

### Primary dependency flow
- Database → Backend
- Backend → Backend
- Backend → API
- API → Frontend

### Input mode
- Primary: ZIP upload
- Demo mode: prepared sample repo
- Stretch: GitHub repo link

---

## Core features
### MVP
1. ZIP repo upload
2. File scanner with ignore rules
3. Entity extraction
4. Entity index
5. Rule-based graph generation
6. React Flow graph visualization
7. Change impact simulation
8. Risk score
9. Clean analysis summary

### Post-MVP planned features
1. Natural language query engine
2. Suggested textual fixes
3. Hidden debug panel
4. Graceful partial analysis for unsupported repos

### Deferred backlog
- patch / diff generation
- PR analyzer
- GitHub URL ingestion as primary mode
- frontend → frontend dependency graph
- full function call graph
- full class inheritance graph
- stored procedures / triggers
- graph database support

---

## High-level architecture
```text
ZIP Upload
↓
File Scanner
↓
Entity Extraction
↓
Entity Index
↓
Rule-Based Dependency Builder
↓
Graph (JSON nodes + edges)
↓
Impact Analysis (Traversal + Scoring)
↓
LLM Layer (Explanation / NL Query / Suggestions)
↓
React Flow Visualization
```

---

## Tech stack
### Frontend
- React + Vite
- React Flow
- Axios or Fetch

### Backend
- Python
- FastAPI
- Uvicorn
- Pydantic

### LLM usage
Used only for:
- impact explanation
- natural language query interpretation and explanation
- textual suggested fixes

Not used for:
- parsing
- graph construction
- node generation
- edge generation

---

## Performance limits
- ZIP size limit: **40 MB**
- Max files scanned: **500**
- Max supported files parsed: **180**
- Max parse timeout per file: **2 seconds**
- Target total analysis time: **under 20 seconds**
- Hard graceful cutoff: **25 seconds**

---

## Supported file extensions
- `.py`
- `.js`
- `.ts`
- `.jsx`
- `.tsx`
- `.sql`

### Ignored directories
- `node_modules`
- `dist`
- `build`
- `venv`
- `.git`
- `__pycache__`
- `.next`
- `coverage`
- `out`

---

## Required user-facing behavior
The app must never expose raw parser failures.

If unsupported or broken files exist:
- skip them
- continue analysis
- show a clean partial-analysis summary

Example:
```text
Analysis Completed
Supported files analyzed: 42
Unsupported/skipped files: 16
Graph nodes generated: 28
Graph edges generated: 24
```

---

## Team model (4 members)
### Dev 1
Repo ingestion + file scanner

### Dev 2
Entity extraction + entity index

### Dev 3
Graph builder + impact engine

### Dev 4
Frontend + visualization + API integration

---

## Demo flow
1. Use prepared demo repo
2. Generate graph
3. Click critical node (example: `users.email`)
4. Simulate change
5. Show impacted nodes
6. Show risk score
7. Ask one natural-language question
8. Show suggested fixes
9. Mention optional ZIP upload for judge repo

---

## Success criteria
A successful build must demonstrate:
- cross-language dependency mapping
- deterministic impact analysis
- clean graph UI
- visible but controlled GenAI usage
- graceful handling of real-world repo noise
