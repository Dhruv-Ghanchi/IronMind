/**
 * contentScript.js
 * Runs on github.com pages.
 * Accurately extracts repository owner and repo name from the URL, 
 * even if deeply nested.
 */

function extractRepoInfo() {
  const pathParts = window.location.pathname.split('/').filter(Boolean);
  
  // A GitHub repository URL at minimum has `owner` and `repo` at indices 0 and 1.
  if (pathParts.length >= 2) {
    return {
      owner: pathParts[0],
      repo: pathParts[1],
      isGithubRepo: true
    };
  }
  return { isGithubRepo: false };
}

// We use chrome.runtime.onMessage so the popup can request the repo context whenever it opens.
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'GET_REPO_INFO') {
    sendResponse(extractRepoInfo());
  }
});
