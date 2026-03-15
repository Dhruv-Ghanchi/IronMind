import requests
import base64
import os
from datetime import datetime

def get_headers():
    token = os.getenv('GITHUB_TOKEN')
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def get_file_sha(owner, repo, path, branch) -> str or None:
    """GET /repos/{owner}/{repo}/contents/{path}?ref={branch}"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        return response.json().get("sha")
    return None

def create_branch(owner, repo, base_branch, new_branch) -> bool:
    """Create a new branch from a base branch."""
    # 1. Get base branch SHA
    url_get = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}"
    resp_get = requests.get(url_get, headers=get_headers())
    if resp_get.status_code != 200:
        print(f"DEBUG: Failed to get base branch SHA: {resp_get.status_code} {resp_get.text}")
        return False
    
    sha = resp_get.json()["object"]["sha"]
    
    # 2. Create new ref
    url_post = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
    body = {
        "ref": f"refs/heads/{new_branch}",
        "sha": sha
    }
    resp_post = requests.post(url_post, json=body, headers=get_headers())
    if resp_post.status_code != 201:
        print(f"DEBUG: Failed to create ref: {resp_post.status_code} {resp_post.text}")
    return resp_post.status_code == 201

def get_file_content_from_github(owner, repo, path, branch) -> str or None:
    """Fetch and decode file content from GitHub."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        data = response.json()
        content_b64 = data.get("content", "")
        # GitHub might add newlines to b64
        return base64.b64decode(content_b64.replace("\n", "")).decode("utf-8")
    return None

def commit_patched_file(owner, repo, path, new_content, branch, message) -> bool:
    """Commit an updated file to a specific branch."""
    current_sha = get_file_sha(owner, repo, path, branch)
    
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    content_encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    
    body = {
        "message": message,
        "content": content_encoded,
        "branch": branch
    }
    if current_sha:
        body["sha"] = current_sha
        
    response = requests.put(url, json=body, headers=get_headers())
    return response.status_code in [200, 201]

def open_pull_request(owner, repo, head, base, title, body) -> dict:
    """Post a new Pull Request to GitHub."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    payload = {
        "title": title,
        "body": body,
        "head": head,
        "base": base
    }
    response = requests.post(url, json=payload, headers=get_headers())
    if response.status_code == 201:
        data = response.json()
        return {
            "pr_url": data.get("html_url"),
            "pr_number": data.get("number"),
            "pr_title": data.get("title")
        }
    else:
        raise Exception(f"GitHub PR failed: {response.text}")

def create_pr_from_patches(owner, repo, base_branch, patches, intent) -> dict:
    """Orchestrates branch creation, multi-file commits, and PR opening."""
    # a. Generate branch name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    new_branch = f"polyglot/{timestamp}"
    
    # b. Call create_branch()
    if not create_branch(owner, repo, base_branch, new_branch):
        raise Exception(
            f"Cannot create branch on {owner}/{repo}. "
            f"Your GITHUB_TOKEN needs push access to this repository. "
            f"Fork the repo first, or use a repo you own."
        )
    
    committed_files = []
    
    # c. For each patch
    for patch in patches:
        file_path = patch["file_path"]
        original = patch["original"]
        replacement = patch["replacement"]
        reason = patch["reason"]
        
        # Get live content
        live_content = get_file_content_from_github(owner, repo, file_path, new_branch)
        if live_content is None:
            print(f"DEBUG: Skipping commit for {file_path}, file not found in branch.")
            continue
            
        # Apply patch
        if original in live_content:
            new_content = live_content.replace(original, replacement, 1)
            
            # Commit ONLY if changed
            if new_content != live_content:
                msg = f"fix: {reason} [{os.path.basename(file_path)}]"
                if commit_patched_file(owner, repo, file_path, new_content, new_branch, msg):
                    committed_files.append(file_path)
    
    # d. Check if any committed
    if not committed_files:
        raise Exception("No changes were successfully applied to the target branch.")
        
    # e. Build PR body markdown
    files_list_md = "\n".join([f"- `{f}`" for f in committed_files])
    pr_body = f"""## Polyglot Analyzer - Automated Fix

**What changed:** {intent}

**Files modified:** {len(committed_files)}
{files_list_md}

**Risk analysis:** Run by Kimi K2 via Featherless AI
> Auto-generated recommendation. Please review code logic before merging.
"""
    
    # f. Call open_pull_request()
    pr_info = open_pull_request(
        owner=owner,
        repo=repo,
        head=new_branch,
        base=base_branch,
        title=f"Polyglot Fix: {intent[:50]}...",
        body=pr_body
    )
    
    # g. Return summary
    return {
        "pr_url": pr_info["pr_url"],
        "pr_number": pr_info["pr_number"],
        "branch": new_branch,
        "files_changed": committed_files,
        "files_count": len(committed_files)
    }
