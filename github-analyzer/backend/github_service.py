import requests
import base64
import os
import re
import httpx
import asyncio
from fastapi import HTTPException

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_headers():
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def parse_github_url(url: str) -> dict:
    """
    Handles formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo/
    - https://github.com/owner/repo/tree/main
    - http://github.com/owner/repo
    - github.com/owner/repo
    """
    url = url.strip().rstrip("/")
    if url.startswith("http"):
        url = re.sub(r'https?://', '', url)
    
    parts = url.split('/')
    
    if len(parts) < 3 or 'github.com' not in parts[0]:
        raise ValueError("Invalid GitHub URL format. Use: https://github.com/owner/repo")
    
    owner = parts[1]
    repo = parts[2]
    branch = None
    
    if len(parts) >= 5 and parts[3] == "tree":
        branch = parts[4]
        
    return {"owner": owner, "repo": repo, "branch": branch}

def get_repo_info(owner: str, repo: str) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url, headers=get_headers())
    
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Repository not found.")
    elif response.status_code == 403:
        raise HTTPException(
            status_code=403,
            detail="GitHub API rate limit reached. Add GITHUB_TOKEN to backend .env to increase limits."
        )
    elif response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"GitHub API Error: {response.text}")
        
    data = response.json()
    return {
        "full_name": data.get("full_name"),
        "default_branch": data.get("default_branch", "main"),
        "description": data.get("description", ""),
        "language": data.get("language"),
        "stargazers_count": data.get("stargazers_count", 0),
        "forks_count": data.get("forks_count", 0)
    }


# ============ TREES API + PARALLEL CONTENT FETCH ============

async def get_all_files(owner, repo, branch):
    """
    1. ONE API call via GitHub Trees API to get the entire repo file list
    2. Filter by extension, skip dirs, cap size
    3. Parallel batch download of contents via raw.githubusercontent.com
    """
    headers = get_headers()

    SKIP_DIRS = {
        'node_modules', '.git', '__pycache__',
        'venv', 'env', 'dist', 'build', '.next',
        'coverage', 'vendor', '.pytest_cache', '.vscode', '.idea'
    }
    ALLOWED_EXT = {
        '.py', '.js', '.ts', '.jsx', '.tsx',
        '.html', '.css', '.sql', '.vue', '.go', '.rb',
        '.java', '.php', '.c', '.cpp', '.h', '.cs', '.rs', '.swift'
    }

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:

        # ONE API call gets entire repo tree
        res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
            follow_redirects=True
        )

        if res.status_code == 404:
            # try master
            res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/master",
                params={"recursive": "1"},
                follow_redirects=True
            )

        if res.status_code != 200:
            raise HTTPException(
                status_code=res.status_code,
                detail="Could not fetch repo tree"
            )

        tree_data = res.json()
        tree = tree_data.get("tree", [])
        print(f"DEBUG: Trees API returned {len(tree)} items for {owner}/{repo}")

        # Filter files from the flat tree list
        files = []
        for item in tree:
            if item["type"] != "blob":
                continue

            path = item["path"]

            # Skip if any path component is in SKIP_DIRS
            parts = path.split("/")
            if any(p in SKIP_DIRS for p in parts):
                continue

            # Check extension
            ext = os.path.splitext(path)[1].lower()
            if ext not in ALLOWED_EXT:
                continue

            # Skip large files
            size = item.get("size", 0)
            if size > 100000:
                continue

            files.append({
                "name": os.path.basename(path),
                "path": path,
                "sha": item["sha"],
                "size": size,
                "download_url": f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
            })

        print(f"DEBUG: Found {len(files)} files after filtering")

        # Cap at 150 files for speed
        files = files[:150]

        # Fetch all file contents in parallel, batches of 30
        batch_size = 30
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            tasks = [
                client.get(f["download_url"], timeout=8.0)
                for f in batch
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for file_info, response in zip(batch, responses):
                if isinstance(response, Exception):
                    file_info["content"] = ""
                elif response.status_code == 200:
                    file_info["content"] = response.text
                else:
                    file_info["content"] = ""

        return files


# ============ SYNC HELPER (used by pr_service) ============

def get_file_content(download_url: str) -> str:
    """Simple sync GET for a single file."""
    try:
        response = requests.get(download_url, timeout=5)
        if response.status_code == 200:
            return response.text
        return ""
    except Exception:
        return ""
