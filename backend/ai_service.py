import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# Explicitly search for .env file
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

# Configuration
PRIMARY_MODEL = "moonshotai/Kimi-K2-Instruct"
FALLBACK_MODEL = "THUDM/GLM-4-9b-chat"
BASE_URL = "https://api.featherless.ai/v1"
API_KEY = os.getenv("FEATHERLESS_API_KEY")
AI_CALL_TIMEOUT_SEC = 8

client = None
if API_KEY:
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=AI_CALL_TIMEOUT_SEC
    )

def _clean_json_response(text: str) -> str:
    """Strips markdown fences and whitespace from AI responses."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()

def safe_call(messages, model=PRIMARY_MODEL) -> str:
    """Try PRIMARY_MODEL, fallback to FALLBACK_MODEL on failure."""
    if not client:
        return "AI analysis unavailable. FEATHERLESS_API_KEY is missing."

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=1000,
            timeout=AI_CALL_TIMEOUT_SEC
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"DEBUG: AI call to {model} failed: {e}")
        if model == PRIMARY_MODEL:
            print("DEBUG: Retrying with fallback model...")
            return safe_call(messages, model=FALLBACK_MODEL)
        return "AI analysis unavailable."

def explain_impact(file_name: str, affected_files: list) -> str:
    """Predict risk level and impact summary for main frontend."""
    system_msg = "You are a concise Risk Advisor. provide exactly 3 bullet points of architectural insight."
    user_prompt = f"File {file_name} affects these files: {', '.join(affected_files)}. Provide exactly 3 concise bullet points explaining why this is high-risk. Start each point with '•'. No markdown formatting, no essays."
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt}
    ]
    return safe_call(messages).replace("**", "").replace("__", "").replace("`", "")

def gh_explain_impact(file_name: str, affected_files: list) -> dict:
    """Predict risk level and impact summary for GitHub Analyzer frontend."""
    system_msg = "You are an expert code analyst. Respond only in valid JSON."
    user_prompt = f"""A developer wants to modify or delete: {file_name}

Affected files found by graph analysis:
{json.dumps(affected_files, indent=2)}

Respond with ONLY this JSON structure:
{{
  "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "risk_score": <number 0-10>,
  "summary": "<one clear sentence about the impact>",
  "bullets": [
    "<specific impact 1 with file name>",
    "<specific impact 2 with file name>",
    "<specific impact 3 with recommendation>"
  ],
  "safe_to_delete": <true|false>
}}"""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt}
    ]

    response_text = safe_call(messages)
    if response_text.startswith("AI analysis unavailable"):
        return _fallback_impact(file_name, affected_files)
    
    try:
        data = json.loads(_clean_json_response(response_text))
        return data
    except Exception as e:
        print(f"DEBUG: Failed to parse impact JSON: {e}")
        return _fallback_impact(file_name, affected_files)

def _fallback_impact(file_name: str, affected_files: list) -> dict:
    affected_count = len(affected_files)
    if affected_count >= 6:
        risk_level, risk_score = "HIGH", 8
    elif affected_count >= 3:
        risk_level, risk_score = "MEDIUM", 6
    elif affected_count >= 1:
        risk_level, risk_score = "LOW", 3
    else:
        risk_level, risk_score = "LOW", 2

    bullet_files = [f.get("name") if isinstance(f, dict) else f for f in affected_files[:3]]
    bullets = []
    for name in bullet_files:
        bullets.append(f"Review dependent logic in {name}.")
    bullets.append("Run unit/integration tests for affected modules before merge.")

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "summary": f"Estimated impact for changes to {file_name or 'the selected file'} across {affected_count} related file(s).",
        "bullets": bullets,
        "safe_to_delete": affected_count == 0
    }

def generate_patches(intent: str, file_contents: str, affected_files: list) -> list:
    """Generate minimal safe patches for a list of files."""
    system_msg = "You are a code patching engine. Return only JSON."
    user_prompt = f"User wants to: {intent}\nThese files will be affected: {', '.join(affected_files)}\nFile contents: {file_contents}\n\nReturn ONLY a JSON array, no other text:\n[{{\"file_path\": \"path/to/file\", \"original\": \"exact string to find\", \"replacement\": \"new string to replace with\", \"reason\": \"why this change is needed\"}}]"
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt}
    ]
    
    raw_response = safe_call(messages)
    try:
        cleaned = _clean_json_response(raw_response)
        return json.loads(cleaned)
    except Exception as e:
        print(f"JSON PARSE ERROR: {e}")
        return []

def gh_generate_patches(intent: str, file_contents: dict, affected_files: list) -> list:
    """Generate minimal safe patches for GitHub Analyzer (multiple files)."""
    system_msg = "You are an expert software engineer. Respond only with a valid JSON array."
    
    formatted_contents = ""
    for name, content in file_contents.items():
        formatted_contents += f"=== {name} ===\n{content}\n\n"

    user_prompt = f"""Developer intent: {intent}

Affected files: {json.dumps([f['name'] if isinstance(f, dict) else f for f in affected_files])}

File contents to modify:
{formatted_contents}

Generate minimal safe patches.
Each patch must have 'original' text that EXISTS verbatim in the file content shown above.

Respond with ONLY a JSON array:
[
  {{
    "file_path": "<exact path>",
    "original": "<exact string from file>",
    "replacement": "<new string>",
    "reason": "<why needed>"
  }}
]"""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt}
    ]

    response_text = safe_call(messages)
    if response_text.startswith("AI analysis unavailable"):
        return _fallback_patches(intent, file_contents, affected_files)
    
    try:
        data = json.loads(_clean_json_response(response_text))
        if isinstance(data, list):
            return data if data else _fallback_patches(intent, file_contents, affected_files)
        return _fallback_patches(intent, file_contents, affected_files)
    except Exception as e:
        print(f"DEBUG: Failed to parse patches JSON: {e}")
        return _fallback_patches(intent, file_contents, affected_files)

def _fallback_patches(intent: str, file_contents: dict, affected_files: list) -> list:
    patches = []
    preferred_paths = [f.get("path") if isinstance(f, dict) else f for f in affected_files]
    seen = set()

    for path in preferred_paths + list(file_contents.keys()):
        if path in seen:
            continue
        seen.add(path)
        content = file_contents.get(path, "")
        if not content:
            continue

        original_line = next((line for line in content.splitlines() if line.strip()), None)
        if not original_line:
            continue

        replacement_line = f"{original_line}{_comment_suffix_for_file(path)}"
        patches.append({
            "file_path": path,
            "original": original_line,
            "replacement": replacement_line,
            "reason": f"Fallback patch suggestion for intent: {intent[:80]}"
        })

        if len(patches) >= 3:
            break

    return patches

def _comment_suffix_for_file(path: str) -> str:
    ext = os.path.splitext((path or "").lower())[1]
    if ext == ".py": return "  # polyglot-review"
    if ext == ".sql": return " -- polyglot-review"
    if ext in {".js", ".ts", ".jsx", ".tsx", ".css", ".go", ".java", ".c", ".cpp", ".cs", ".rb", ".php"}:
        return " // polyglot-review"
    if ext in {".html", ".xml", ".vue"}: return " <!-- polyglot-review -->"
    return " # polyglot-review"

def answer_query(question: str, graph_context: str) -> str:
    """Conversational answer for main frontend."""
    system_msg = "You are a high-level Architecture Advisor. Be concise, technical, and provide exactly 4 bullet points."
    user_prompt = f"Graph Context: {graph_context}\nArchitectural Question: {question}\nProvide professional advice in exactly 4 concise bullet points. Start each with '•'. Mention specific files. No markdown formatting, no essays."

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt}
    ]
    return safe_call(messages).replace("**", "").replace("__", "").replace("`", "")

def gh_answer_query(question: str, graph_summary: str) -> str:
    """Conversational answer for GitHub Analyzer."""
    system_msg = "You are an expert software architect providing concise technical advice."
    
    user_prompt = f"""Based on this codebase graph summary:
{graph_summary}

Answer this question: {question}

Max 120 words. Mention specific file names."""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt}
    ]

    return safe_call(messages)
