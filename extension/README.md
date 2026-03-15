# Polyglot Code Analyzer - Production Extension

This robust browser extension extracts Multilingual code architecture configurations from Github repositories recursively and forwards structured JSON graphs to the dependency backend. Completely Manifest-V3 compliant.

## Improvements & Bug Fixes in v1.1.0
1. **Bulletproof GitHub Regex Parsing:** Extracts `owner/repo` globally ignoring nested depth (prevents folder scan breaks).
2. **Persistent Port Communication:** Uses Chrome `runtime.connect()`, which allows asynchronous, streaming preloader updates. Eliminates frontend freezes/hanging preloaders.
3. **Pipelined Fetching Strategies:** Maps full Git recursively via `tree` endpoints, fetching 10 files in parallel (`Promise.all()`) bypassing CORS limitation effectively and scaling. 
4. **Enhanced Error Checking:** Gracefully catches non-existent files, lack of permitted extensions, blank projects, API failures and redirects gracefully to frontend "Try Again" screens safely.

## Component Flow Analysis
- **`contentScript.js`**: Injects securely on `github.com/*`. Matches exact repository signatures immediately to pass payload context natively back to `popup.html`.
- **`popup.js`**: Orchestrates state via the `port.onMessage` interface syncing backend download tasks incrementally to loading UX indicators.
- **`background.js`**: The service-worker brain. 
  1. Requests Repo Config
  2. Queries recursive `/git/trees` resolving standard branches.
  3. Filters targeted nodes (`.ts`, `.py`, `.js`, `.sql`).
  4. Mass downloads files via `raw.githubusercontent` in asynchronous array chunks.
  5. Offloads standard JSON representations directly to `http://localhost:8000/upload_temp`.

## System Requirements
To test e2e, the Python backend code analysis must be listening on:
`http://localhost:8000/upload_temp` ensuring proper JSON payload mapping standards (Expects keys: `repo_name`, `files`).

## How to Test
1. Clone branch `feature/extension`.
2. Open Google Chrome > Navigate to `chrome://extensions/`.
3. Enable **Developer mode** toggle.
4. Click **Load unpacked**, navigate and select this `/extension` folder.
5. Browse onto any target repository on `github.com` (e.g., `https://github.com/microsoft/vscode/tree/main/src`).
6. Click the extension, review mapping metrics, and send test data to local analysis endpoints!