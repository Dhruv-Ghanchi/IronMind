# Product Requirements Document (PRD)

## Polyglot Dependency Impact Analyzer

Version: 1.0\
Purpose: Hackathon Implementation Blueprint\
Audience: Developers, AI coding agents, and engineering teams
implementing the system.

------------------------------------------------------------------------

# 1. Executive Summary

Modern software systems are built using multiple programming languages
across layers such as database, backend services, APIs, and frontend
applications. When developers modify a database column, API endpoint, or
variable, it is difficult to determine what other parts of the system
will break.

Traditional static analysis tools typically work within a single
language. They fail to trace dependencies across different system layers
or languages.

The **Polyglot Dependency Impact Analyzer** solves this by:

1.  Parsing repositories containing multiple languages
2.  Extracting entities from each layer
3.  Building a cross-language dependency graph
4.  Simulating change propagation
5.  Providing risk analysis and developer recommendations

The system is designed to be built within a hackathon timeframe (\~14
hours) while maintaining architectural clarity.

------------------------------------------------------------------------

# 2. Problem Statement

In distributed software architectures:

-   Database changes may silently break backend services.
-   Backend changes may break API responses.
-   API changes may break frontend UI components.

Developers currently rely on manual code search and guesswork to
identify impact.

This leads to:

-   Production bugs
-   Slow debugging
-   Fear of refactoring
-   Fragile systems

The tool must automatically analyze repositories and answer:

• What depends on this field?\
• What will break if this changes?\
• Where is this entity used?

------------------------------------------------------------------------

# 3. Product Goals

Primary Goals

1.  Build a cross-language dependency graph.
2.  Visualize architecture relationships clearly.
3.  Simulate change impact across layers.
4.  Allow natural language dependency queries.

Secondary Goals

1.  Provide risk scoring for modifications.
2.  Suggest fixes developers should apply.

------------------------------------------------------------------------

# 4. Target Users

Primary Users

• Backend developers\
• Full-stack developers\
• Software architects

Secondary Users

• DevOps engineers\
• Technical leads\
• Code reviewers

------------------------------------------------------------------------

# 5. System Scope

Supported Languages

• Python (backend) • JavaScript / TypeScript (frontend) • SQL (database)

Unsupported languages must be skipped safely.

The system must never crash when encountering unknown files.

------------------------------------------------------------------------

# 6. High-Level Architecture

System Layers

Database Layer Backend Layer API Layer Frontend Layer

Visualization Layout

Database → Backend → API → Frontend

Technology Stack

Frontend: React + Vite React Flow

Backend: Python + FastAPI

Graph Representation: JSON nodes + edges

Processing Model: In-memory graph processing

LLM usage: Explanation, natural language queries, suggested fixes

LLM must NOT build the dependency graph.

------------------------------------------------------------------------

# 7. Repository Processing Pipeline

Pipeline Steps

1.  Repository Upload
2.  ZIP Extraction
3.  File Scanner
4.  Entity Extraction
5.  Entity Index Construction
6.  Dependency Graph Builder
7.  Impact Analysis Engine
8.  Visualization Layer

------------------------------------------------------------------------

# 8. File Scanner

Allowed Extensions

.py .js .ts .jsx .tsx .sql

Ignored Directories

node_modules dist build venv .git **pycache** .next coverage out

Performance Limits

ZIP size: 40MB\
Max scanned files: 500\
Max parsed files: 180\
Parse timeout per file: 2s\
Target analysis time: \<20s\
Graceful cutoff: 25s

------------------------------------------------------------------------

# 9. Entity Extraction

SQL Entities

Tables Columns Views Foreign keys

Python Entities

Imports Function definitions Class definitions API routes Field
references HTTP client calls

JavaScript / TypeScript Entities

API calls Component names Field usage

Example Output

{ "tables": \["users"\], "columns": \["users.email"\], "routes": \["GET
/profile"\], "components": \["ProfilePage"\] }

------------------------------------------------------------------------

# 10. Graph Model

Nodes

{ "id": "users.email", "label": "users.email", "type": "column",
"layer": "database" }

Edges

{ "source": "users.email", "target": "user_service.py", "type":
"db_to_backend" }

Graph Layers

database backend api frontend

------------------------------------------------------------------------

# 11. Dependency Detection

Edges are created using rule-based logic.

Examples

SQL column referenced in backend → Database → Backend

Python import → Backend → Backend

Python route definition → Backend → API

Frontend fetch call → API → Frontend

------------------------------------------------------------------------

# 12. Impact Analysis Engine

Impact analysis uses graph traversal.

Algorithm

Breadth First Search (BFS)

Process

1.  Select node
2.  Traverse outgoing edges
3.  Collect reachable nodes
4.  Mark impacted components

------------------------------------------------------------------------

# 13. Risk Scoring

Risk is determined using simple heuristics.

Scoring Factors

+1 per impacted node\
+2 if API layer affected\
+2 if frontend layer affected\
+1 if multiple backend services affected\
+1 if database schema changed

Severity Scale

0--3 Low\
4--6 Medium\
7--10 High

------------------------------------------------------------------------

# 14. Natural Language Queries

Example Queries

Where is users.email used?\
Which services depend on users table?\
Which pages call /profile?

Architecture

LLM interprets question → Backend executes graph query → LLM explains
answer

------------------------------------------------------------------------

# 15. Suggested Fixes

The system produces textual recommendations.

Example

user_service.py

Change field reference user.email → user.email_address

ProfilePage.tsx

Update frontend mapping for email field.

Automatic code rewriting is out of scope.

------------------------------------------------------------------------

# 16. Fault Tolerance

Graceful Degradation

If unsupported files exist

• Skip file • Continue parsing • Build partial graph

User sees summary instead of errors.

------------------------------------------------------------------------

# 17. Debug Mode

Hidden developer mode exposes

• Parsed files count • Skipped files • Parse failures • Node count •
Edge count • Pipeline logs

Debug mode must not appear in demo UI.

------------------------------------------------------------------------

# 18. Demo Repository

Example Dependency Chain

users.email → user_service.py → GET /profile → ProfilePage.tsx

Demo Steps

1.  Generate graph
2.  Click node
3.  Simulate change
4.  Show impacted nodes
5.  Show risk score
6.  Ask natural language question
7.  Show suggested fixes

------------------------------------------------------------------------

# 19. Out of Scope

Not included in hackathon version

• Automatic code refactoring • Multi-language parsing beyond supported
set • Large monorepo support • Full static analysis engine • Persistent
graph storage

------------------------------------------------------------------------

# 20. Success Criteria

The system succeeds if it can

• Parse repository files • Extract entities • Build dependency graph •
Visualize architecture layers • Simulate change impact • Provide risk
scoring • Answer dependency queries • Suggest fixes

within defined performance constraints.
