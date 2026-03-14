import os
import json
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

client = None
if API_KEY:
    print(f"DEBUG: AI Service found API Key (length: {len(API_KEY)})")
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL
    )
else:
    print("WARNING: AI Service could NOT find FEATHERLESS_API_KEY in environment!")

def _call_llm(prompt: str, system_message: str = "You are an expert software architect."):
    """Helper to call LLM with fallback logic."""
    if not client:
        return "AI Service not configured."

    try:
        # Try Primary
        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        raw_content = response.choices[0].message.content or ""
        return raw_content.replace("**", "").replace("__", "").replace("`", "")
    except Exception as e:
        print(f"PRIMARY MODEL FAILED: {e}. Switching to fallback.")
        try:
            # Try Fallback
            response = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            raw_content = response.choices[0].message.content or ""
            return raw_content.replace("**", "").replace("__", "").replace("`", "")
        except Exception as e2:
            return f"AI Error: {e2}"

def explain_impact(file_name: str, affected_files: list) -> str:
    """1. explain_impact(file_name, affected_files) -> str"""
    prompt = f"File {file_name} affects these files: {', '.join(affected_files)}. Provide exactly 3 concise bullet points explaining why this is high-risk. Start each point with '•'. No markdown formatting (no bold/italics), no essays."
    return _call_llm(prompt, "You are a concise Risk Advisor. provide exactly 3 bullet points of architectural insight.")

def generate_patches(intent: str, file_contents: str, affected_files: list) -> list:
    """2. generate_patches(intent, file_contents, affected_files) -> list"""
    prompt = f"User wants to: {intent}\nThese files will be affected: {', '.join(affected_files)}\nFile contents: {file_contents}\n\nReturn ONLY a JSON array, no other text:\n[{{'file_path': 'path/to/file', 'original': 'exact string to find', 'replacement': 'new string to replace with', 'reason': 'why this change is needed'}}]"
    
    raw_response = _call_llm(prompt, "You are a code patching engine. Return only JSON.")
    
    # Clean up response in case LLM adds markdown or chatter
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:-3].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:-3].strip()
        
        return json.loads(cleaned)
    except Exception as e:
        print(f"JSON PARSE ERROR: {e}")
        return []

def answer_query(question: str, graph_context: str) -> str:
    """3. answer_query(question, graph_context) -> str"""
    prompt = f"Graph Context: {graph_context}\nArchitectural Question: {question}\nProvide professional advice in exactly 4 concise bullet points. Start each with '•'. Mention specific files. No markdown formatting, no essays."
    return _call_llm(prompt, "You are a high-level Architecture Advisor. Be concise, technical, and provide exactly 4 bullet points.")
