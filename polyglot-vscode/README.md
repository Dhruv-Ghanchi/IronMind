# Polyglot Analyzer
Cross-language dependency mapper — trace how changes propagate across SQL, Python, APIs, and React.

*(Screenshot goes here)*

## Requirements
- VS Code ^1.74.0
- Polyglot Backend running on `http://localhost:8001` (FastAPI)

## Installation
1. Install this extension.
2. Clone and start the Polyglot backend service.
3. Configure backend URL in settings if not using localhost.

## Usage
1. Click the Polyglot Analyzer icon in the Activity Bar.
2. Click **Scan Project** to parse your current workspace.
3. Click **Open Graph** or ask questions in the dashboard.
4. Click on any node in the graph to simulate cross-layer impact.

## Configuration
| Setting | Default | Description |
| --- | --- | --- |
| `polyglot.backendUrl` | `http://localhost:8001` | URL for the Polyglot FastAPI backend. |
| `polyglot.frontendUrl`| `http://localhost:5173` | Optional React web client URL. |

## Troubleshooting
- **Connection Refused**: Make sure your backend API is running on `http://localhost:8001`.
- **Scan Failed**: Check `pipeline logs` in the sidebar and ensure you don't exceed the max file count (500 files).
- **Blank Graph**: Reload the window and scan again. Make sure CSP allows `unpkg.com` if developing locally.

## Demo
Scan a project -> Graph displays Python backend files relying on SQL database -> Click a Python file -> See React pages light up as impacted!
