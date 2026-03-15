/**
 * popup.js
 * Controls extension UI and communicates with background scripts over a secure Port connection.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Core DOM Elements
    const repoInfoEl = document.getElementById('repoInfo');
    const repoNameEl = document.getElementById('repoName');
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    // Status Elements
    const statusContainer = document.getElementById('statusContainer');
    const statusMessage = document.getElementById('statusMessage');
    
    // Stats Dashboard
    const statsContainer = document.getElementById('statsContainer');
    const countPyEl = document.getElementById('countPy');
    const countTsEl = document.getElementById('countTs');
    const countSqlEl = document.getElementById('countSql');
  
    // Handling and Success View
    const errorContainer = document.getElementById('errorContainer');
    const errorMessage = document.getElementById('errorMessage');
    const retryBtn = document.getElementById('retryBtn');
  
    const successContainer = document.getElementById('successContainer');
    const viewDetailBtn = document.getElementById('viewDetailBtn');
    const notGithubContainer = document.getElementById('notGithubContainer');
  
    let currentRepoData = null;
    let currentSessionId = null;
    let currentStats = null;
    let port = null; // Background messaging port
  
    // 2. Initial Setup: Check Active Tabs
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const activeTab = tabs[0];
      
      // Determine if a user actually opened this cleanly on GitHub
      if (activeTab && activeTab.url && activeTab.url.includes("github.com")) {
        chrome.tabs.sendMessage(activeTab.id, { action: 'GET_REPO_INFO' }, (response) => {
          // Verify we did not lose runtime connection
          if (!chrome.runtime.lastError && response && response.isGithubRepo) {
            currentRepoData = response;
            repoNameEl.textContent = `${response.owner}/${response.repo}`;
            showView(repoInfoEl);
          } else {
            // Fallback: If content script hasn't loaded (e.g., after extension reload or SPA navigation),
            // parse the activeTab.url directly.
            try {
              const urlObj = new URL(activeTab.url);
              const pathParts = urlObj.pathname.split('/').filter(Boolean);
              
              if (pathParts.length >= 2) {
                currentRepoData = { owner: pathParts[0], repo: pathParts[1], isGithubRepo: true };
                repoNameEl.textContent = `${pathParts[0]}/${pathParts[1]}`;
                showView(repoInfoEl);
                return; // successfully handled via fallback
              }
            } catch (e) {
              console.error("Fallback URL parsing failed", e);
            }
            showView(notGithubContainer);
          }
        });
      } else {
        showView(notGithubContainer);
      }
    });
  
    // 3. User Trigger Flows
    analyzeBtn.addEventListener('click', () => {
      if (!currentRepoData) return;
      startAnalysis();
    });
  
    retryBtn.addEventListener('click', () => {
      showView(repoInfoEl);
    });
  
    viewDetailBtn.addEventListener('click', () => {
      if (currentSessionId) {
        const params = new URLSearchParams({
          session: currentSessionId,
          filesAnalyzed: currentStats?.filesAnalyzed ?? 0,
          filesSkipped: currentStats?.filesSkipped ?? 0
        });
        chrome.tabs.create({ url: `http://localhost:5173/analytics?${params}` });
      } else {
        console.error("Cannot redirect: Session ID is missing.");
      }
    });
  
    // 4. Execution Core
    function startAnalysis() {
      showView(statusContainer);
      statusMessage.textContent = "Booting engine...";
      
      // Open long-lived connection so preloader dynamically syncs
      port = chrome.runtime.connect({ name: 'analyze_repo' });
      
      // Start background command
      port.postMessage({ action: 'START_ANALYSIS', repoData: currentRepoData });
      
      // Listen to real-time events over connection
      port.onMessage.addListener(handleStateUpdate);
    }
  
    // 5. Reactive UI Rendering
    function handleStateUpdate(state) {
      if (!state) return;
      
      switch (state.status) {
        case 'fetching_tree':
        case 'downloading_files':
        case 'uploading_backend':
          showView(statusContainer);
          statusMessage.textContent = state.message;
          break;
  
        case 'complete':
          currentSessionId = state.session_id;
          currentStats = state.stats;
          countPyEl.textContent = state.stats.py;
          countTsEl.textContent = state.stats.jsts;
          countSqlEl.textContent = state.stats.sql;
          
          statusContainer.classList.add('hidden');
          statsContainer.classList.remove('hidden');
          successContainer.classList.remove('hidden');
          port.disconnect(); // Task finished clean up
          break;
  
        case 'error':
          showView(errorContainer);
          errorMessage.textContent = state.message;
          port.disconnect(); // Disconnect listener to avoid resource leaking
          break;
      }
    }
  
    // Abstract Switch function
    function showView(activeElement) {
      [repoInfoEl, statusContainer, errorContainer, successContainer, notGithubContainer, statsContainer].forEach(el => {
        if (el) el.classList.add('hidden');
      });
      if (activeElement) activeElement.classList.remove('hidden');
    }
  });