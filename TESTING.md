# End-to-End Test Documentation

## Test Status: ✅ READY FOR TESTING

## Components Implemented

### 1. Main Project Features
- ✅ ZIP upload functionality
- ✅ ReactFlow dependency graph visualization
- ✅ Node impact analysis (click nodes)
- ✅ Blast radius calculation
- ✅ AI-powered suggestions
- ✅ Natural language queries

### 2. GitHub Integration Features
- ✅ GitHub URL input with validation
- ✅ Progressive loading states (4 steps, 2s each)
- ✅ GitHub token support (optional)
- ✅ Repo metadata bar (stars, language, branch)
- ✅ Identical graph rendering (ZIP vs GitHub)

### 3. Consequence Engine (NEW)
- ✅ AI impact analysis interface
- ✅ File extraction from questions
- ✅ Risk badges (CRITICAL/HIGH/MEDIUM/LOW)
- ✅ Affected files list with highlighting
- ✅ Patch generation with diff preview
- ✅ GitHub PR creation (GitHub repos only)
- ✅ Success celebration modal
- ✅ Node highlighting and fitView
- ✅ "Powered by Kimi K2" badge

### 4. Error Handling & Polish
- ✅ 60-second timeouts on all API calls
- ✅ Friendly error messages:
  - 403: "Repository is private. Add a GitHub token..."
  - 404: "Repository not found. Check the URL..."
  - 500: "Analysis failed. Try again..."
  - Timeout: "Taking longer than expected..."
- ✅ Loading states never stuck
- ✅ Error retry buttons

---

## Test Flow 1: ZIP Upload (Existing Feature)

### Steps:
1. Navigate to http://localhost:5173
2. Upload a ZIP file (max 40MB)
3. **Expected:** Graph renders with ReactFlow ✓
4. **Expected:** Nodes colored by layer (database/backend/api/frontend) ✓
5. Click any node
6. **Expected:** Blast radius shows impacted nodes ✓
7. **Expected:** Risk score updates ✓
8. **Expected:** Suggested fixes appear in right panel ✓
9. Scroll to **Consequence Engine** panel (3rd column)
10. **Expected:** Panel is visible ✓
11. **Expected:** "Open GitHub PR" button is HIDDEN ✓
12. **Expected:** Can still analyze impact, but no PR creation ✓

### Success Criteria:
- [ ] Graph renders correctly
- [ ] Node colors match layers
- [ ] Impact analysis works
- [ ] Blast radius calculates
- [ ] Suggestions appear
- [ ] Consequence Engine visible but PR button hidden

---

## Test Flow 2: GitHub URL (New Feature)

### Steps:

#### Part A: Initial Load
1. Navigate to http://localhost:5173
2. Scroll down to "OR" section
3. Enter: `github.com/YOUR_USERNAME/YOUR_REPO`
4. Click "Analyze Repository"
5. **Expected:** Loading steps animate (2s each):
   - "Connecting to GitHub..."
   - "Fetching repository files..."
   - "Analyzing dependencies..."
   - "Building knowledge graph..."
6. **Expected:** Graph renders with ReactFlow ✓
7. **Expected:** Identical to ZIP rendering ✓

#### Part B: Repo Meta Bar
8. **Expected:** Slim bar appears below stats ✓
9. **Expected:** Shows:
   - Repo name (owner/repo)
   - Stars count ⭐
   - Language
   - Branch name
   - "View on GitHub →" link
10. Click "View on GitHub →"
11. **Expected:** Opens GitHub in new tab ✓

#### Part C: Consequence Engine
12. Scroll to **Consequence Engine** panel (3rd column)
13. Type: "What if I delete auth.py?"
14. Click "Analyze Impact"
15. **Expected:** Shows "Kimi K2 analyzing..." ✓
16. **Expected:** Risk badge appears (CRITICAL/HIGH/MEDIUM/LOW) ✓
17. **Expected:** Summary sentence ✓
18. **Expected:** 3 bullet points ✓
19. **Expected:** "X files affected" count ✓
20. **Expected:** List of affected files ✓
21. **Expected:** Affected nodes highlighted RED in graph ✓
22. **Expected:** Graph auto-zooms to affected nodes ✓

#### Part D: Patch Generation
23. Click "Generate Patches"
24. **Expected:** Shows "Kimi K2 generating patches..." ✓
25. **Expected:** Diff preview cards appear ✓
26. **Expected:** Each card shows:
    - Filename header
    - LEFT: original code (red bg)
    - RIGHT: modified code (green bg)
    - Monospace font ✓

#### Part E: GitHub PR Creation
27. **Expected:** "Open GitHub PR" button is VISIBLE ✓
28. Click "Open GitHub PR"
29. **Expected:** Progressive loading:
    - "Creating branch..."
    - "Committing changes..."
    - "Opening Pull Request..."
30. **Expected:** Success modal appears ✓
31. **Expected:** Modal shows:
    - ✓ checkmark icon
    - "Pull Request Created!"
    - PR title
    - "X files changed"
    - "View PR on GitHub →" button
32. **Expected:** Affected nodes turn GREEN with pulse ✓
33. Click "View PR on GitHub →"
34. **Expected:** Opens actual PR in new tab ✓

### Success Criteria:
- [ ] GitHub URL validation works
- [ ] Loading steps animate correctly
- [ ] Graph renders identically to ZIP
- [ ] Repo meta bar shows all info
- [ ] Consequence Engine analyzes correctly
- [ ] Risk assessment displays properly
- [ ] Nodes highlight in graph
- [ ] Patch generation works
- [ ] Diff preview renders correctly
- [ ] PR creation succeeds
- [ ] Nodes turn green after PR
- [ ] PR link works

---

## Test Flow 3: Error Handling

### Timeout Test:
1. Enter a very large repository URL
2. Wait 60 seconds
3. **Expected:** Shows "Taking longer than expected... Try a smaller repository."

### Private Repo Test:
1. Enter a private repository URL without token
2. **Expected:** Shows "Repository is private. Add a GitHub token with repo access."

### Invalid URL Test:
1. Enter: `github.com/invalid/nonexistent`
2. **Expected:** Shows "Repository not found. Check the URL and try again."

### Success Criteria:
- [ ] Timeout message appears after 60s
- [ ] 403 error shows friendly message
- [ ] 404 error shows friendly message
- [ ] Retry buttons work

---

## Backend Requirements

Before testing, ensure both backends are running:

### Terminal 1: Main Backend (Port 8000)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Terminal 2: GitHub Analyzer Backend (Port 8001)
```bash
cd github-analyzer/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### Terminal 3: Frontend (Port 5173)
```bash
cd frontend
npm install
npm run dev
```

---

## API Endpoints Used

### Main Backend (8000)
- POST `/upload` - ZIP upload
- GET `/graph/{id}` - Get graph data
- POST `/impact/{id}` - Analyze impact
- POST `/query/{id}` - Natural language query
- POST `/suggest-fix/{id}` - Get suggestions

### GitHub Analyzer Backend (8001)
- POST `/api/analyze-github` - Analyze GitHub repo
- POST `/api/query` - Consequence analysis
- POST `/api/generate-patches` - Generate code patches
- POST `/api/create-pr` - Create GitHub PR

---

## Visual Verification Checklist

### Layout (3-Column Grid on Large Screens)
- [ ] Left: Action Center (blue theme)
- [ ] Middle: Suggested Fixes (indigo theme)
- [ ] Right: Consequence Engine (purple theme)

### Colors & Styling
- [ ] Glass morphism cards
- [ ] Dark theme (#1a1a2e backgrounds)
- [ ] Brand colors (blue #6366f1, purple #a855f7)
- [ ] Lucide icons throughout

### Consequence Engine Panel
- [ ] Purple glow effect (top-right)
- [ ] Zap icon in header
- [ ] "Powered by Kimi K2" badge (bottom-right, 11px, gray)
- [ ] Risk badges colored correctly
- [ ] Yellow "Generate Patches" button
- [ ] Purple "Open GitHub PR" button (GitHub repos only)

### Repo Meta Bar (GitHub only)
- [ ] Dark background #1a1a2e
- [ ] 13px font size
- [ ] 8px vertical / 20px horizontal padding
- [ ] GitBranch, Star, Code icons
- [ ] "View on GitHub →" link on right

---

## Known Limitations

1. **GitHub PR Creation requires:**
   - Valid GitHub token with `repo` scope
   - Write access to the repository
   - Backend must have GitHub API access

2. **Analysis works best with:**
   - Repositories under 100 files
   - Standard project structures
   - Supported languages (Python, JS/TS, SQL)

3. **Timeout behavior:**
   - All API calls timeout after 60 seconds
   - Large repos may exceed this limit
   - User should try smaller repos if timeout occurs

---

## Final Confirmation

After completing all tests, confirm:

✅ Both ZIP and GitHub URL flows working
✅ Error handling friendly and helpful
✅ Loading states never stuck
✅ Graph visualization identical for both flows
✅ Consequence Engine panel functional
✅ PR creation works (with valid token)
✅ Timeouts prevent infinite loading
✅ Documentation complete (README.md)

---

## Troubleshooting

### If graph doesn't render:
- Check browser console for errors
- Verify both backends are running
- Check network tab for failed API calls

### If PR creation fails:
- Verify GitHub token has `repo` scope
- Check token has write access
- Verify backend can reach GitHub API
- Check backend logs for detailed error

### If analysis times out:
- Try a smaller repository
- Check backend logs for processing errors
- Verify backend has sufficient resources

---

## Documentation

See `README.md` for:
- Architecture overview
- Installation instructions
- Port configuration
- Usage guide for both ZIP and GitHub flows
