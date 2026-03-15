/**
 * background.js
 * High-performance background service worker.
 * Connects with `popup.js` via long-lived connection ports to stream real-time status.
 */

// We establish a connection port to prevent timeout issues and permit multi-stage status updates.
chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== 'analyze_repo') return;

  port.onMessage.addListener(async (msg) => {
    if (msg.action === 'START_ANALYSIS') {
      try {
        await executeAnalysis(msg.repoData, port);
      } catch (error) {
        console.error('Analysis failed:', error);
        port.postMessage({ status: 'error', message: error.message || 'An unexpected error occurred.' });
      }
    }
  });
});

/**
 * Core flow execution function. 
 * Fetch Branch -> Get Recursive Tree -> Filter files -> Fetch raw content in batches -> POST to backend
 */
async function executeAnalysis(repoData, port) {
  const { owner, repo } = repoData;

  // 1. Get Repo Metadata (To deterministically find the default branch)
  port.postMessage({ status: 'fetching_tree', message: 'Resolving target repository branch...' });
  const repoRes = await fetch(`https://api.github.com/repos/${owner}/${repo}`);
  
  if (!repoRes.ok) {
    if (repoRes.status === 403 || repoRes.status === 429) {
      throw new Error(`GitHub API Rate Limit Exceeded. Please wait a while before scanning again.`);
    }
    throw new Error(`Could not find repository ${owner}/${repo} (Status: ${repoRes.status})`);
  }
  
  const repoMeta = await repoRes.json();
  const defaultBranch = repoMeta.default_branch || 'main';

  // 2. Fetch the full recursive repository tree
  port.postMessage({ status: 'fetching_tree', message: `Mapping folder structure on branch '${defaultBranch}'...` });
  const treeUrl = `https://api.github.com/repos/${owner}/${repo}/git/trees/${defaultBranch}?recursive=1`;
  const treeRes = await fetch(treeUrl);
  
  if (!treeRes.ok) {
    if (treeRes.status === 403 || treeRes.status === 429) {
      throw new Error(`GitHub API Rate Limit Exceeded while mapping folder.`);
    }
    throw new Error(`Failed to map directory structure for branch ${defaultBranch}`);
  }
  
  const treeData = await treeRes.json();
  
  // 3. Filter for supported code extensions and skip ignored paths
  const supportedExts = ['.py', '.js', '.ts', '.jsx', '.tsx', '.sql', '.html', '.css'];
  const ignoredPaths = ['node_modules/', 'dist/', 'build/', 'venv/', '.venv/', 'package-lock.json']; 
  const MAX_FILE_SIZE = 100 * 1024; // 100KB

  const filesToFetch = treeData.tree.filter(item => {
    if (item.type !== 'blob') return false; // Ignore folders, only check files 
    if (ignoredPaths.some(ignored => item.path.includes(ignored))) return false;
    if (item.size > MAX_FILE_SIZE) return false;
    return supportedExts.some(ext => item.path.endsWith(ext));
  });

  if (filesToFetch.length === 0) {
    throw new Error('No supported files (.py, .js, .ts, .jsx, .tsx, .sql) found in this repository.');
  }

  port.postMessage({ 
    status: 'downloading_files', 
    message: `Fetching ${filesToFetch.length} files from repository contents...` 
  });

  // 4. Batch fetch the RAW file contents concurrently (batch sizes of 10) to optimize throughput
  const chunks = chunkArray(filesToFetch, 10);
  const filePayloads = [];

  let completedCount = 0;
  for (const chunk of chunks) {
    // Array of promises executing fetch requests using Promise.all resolving together per chunk
    const chunkPromises = chunk.map(async (fileNode) => {
      try {
        const rawUrl = `https://raw.githubusercontent.com/${owner}/${repo}/${defaultBranch}/${fileNode.path}`;
        const rawRes = await fetch(rawUrl);
        if (rawRes.ok) {
          let content = await rawRes.text();
          // Ensure file content is not empty
          if (!content || content.trim().length === 0) {
            console.warn(`[Skip] ${fileNode.path}: File content is empty.`);
            return null;
          }
          // Basic utf-8 sanity check using decoding
          try {
            content = decodeURIComponent(escape(encodeURIComponent(content)));
          } catch (e) {
            console.warn(`[Skip] ${fileNode.path}: Failed to decode UTF-8 content.`);
            return null;
          }
          return { filepath: fileNode.path, content };
        } else {
          console.warn(`[Skip] ${fileNode.path}: Fetch failed with status ${rawRes.status}`);
        }
      } catch (err) {
        console.warn(`[Skip] ${fileNode.path}: Exception during download`, err); // Gracefully fail parsing one file
      }
      return null;
    });

    const results = await Promise.all(chunkPromises);
    filePayloads.push(...results.filter(Boolean)); // Clean up any null files
    
    completedCount += chunk.length;
    port.postMessage({ 
      status: 'downloading_files', 
      message: `Downloaded ${completedCount} / ${filesToFetch.length} files...` 
    });
  }

  if (filePayloads.length === 0) {
    throw new Error('All supported files were empty or failed to download over network.');
  }

  // 5. Submit mapped repository layout safely to Backend processing graph
  port.postMessage({ status: 'uploading_backend', message: 'Generating analysis map locally...' });
  const backendUrl = 'http://localhost:8000/upload_temp';

  console.log("Preparing upload payload");
  console.log("Uploading", filePayloads.length, "files to backend");
  
  const requestBody = JSON.stringify({
    repo_name: `${owner}/${repo}`,
    files: filePayloads
  });
  console.log(`Payload size: ${(requestBody.length / 1024).toFixed(2)} KB`);

  try {
    console.log("Sending POST request to backend...");
    const uploadRes = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: requestBody
    });

    console.log("Backend response received");
    console.log("Backend status:", uploadRes.status);

    if (!uploadRes.ok) {
      const errorText = await uploadRes.text();
      console.error(`Backend returned ${uploadRes.status}:`, errorText);
      throw new Error(`Backend rejection: ${uploadRes.status} - ${errorText}`);
    }

    const uploadResponseData = await uploadRes.json();
    const sessionId = uploadResponseData.session_id || uploadResponseData.analysis_id || 'DEMO_SESSION_123';

    // 6. Complete and report stats
    port.postMessage({
      status: 'complete',
      session_id: sessionId,
      stats: {
        total: filePayloads.length,
        py: filePayloads.filter(f => f.filepath.endsWith('.py')).length,
        jsts: filePayloads.filter(f => f.filepath.endsWith('.js') || f.filepath.endsWith('.ts') || f.filepath.endsWith('.jsx') || f.filepath.endsWith('.tsx')).length,
        sql: filePayloads.filter(f => f.filepath.endsWith('.sql')).length,
        filesAnalyzed: filePayloads.length,
        filesSkipped: filesToFetch.length - filePayloads.length
      }
    });

  } catch (error) {
    console.error("Upload failed:", error);
    port.postMessage({ status: 'error', message: `Backend connection failed: ${error.message}` });
  }
}

// Utility Function
function chunkArray(array, chunkSize) {
  const result = [];
  for (let i = 0; i < array.length; i += chunkSize) {
    result.push(array.slice(i, i + chunkSize));
  }
  return result;
}
