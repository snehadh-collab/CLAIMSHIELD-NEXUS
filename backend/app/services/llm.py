"""Thin, safe wrapper around Gemini.

- Returns (text, error) instead of raising, so callers can fall back truthfully.
- Applies a request timeout so a slow provider cannot hang the API.
- Never exposes the API key or raw provider error text to clients (only the exception class name).
"""
import os
from typing import Any, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "30"))
NOT_CONFIGURED = "AI provider is not configured (no GEMINI_API_KEY)"


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        return None
    try:
        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(REQUEST_TIMEOUT_SECONDS * 1000)),
        )
    except Exception:
        return None


def generate(
    contents: Any,
    system_instruction: Optional[str] = None,
    temperature: float = 0.3,
    response_schema: Any = None,
    client_factory=None,
) -> Tuple[Optional[str], Optional[str]]:
    """Call Gemini. Returns (text, None) on success or (None, reason) on any failure."""
    client = (client_factory or get_gemini_client)()
    if client is None:
        return None, NOT_CONFIGURED
    try:
        cfg = {"temperature": temperature}
        if system_instruction:
            cfg["system_instruction"] = system_instruction
        if response_schema is not None:
            cfg["response_mime_type"] = "application/json"
            cfg["response_schema"] = response_schema
        response = client.models.generate_content(
            model=MODEL_NAME, contents=contents, config=types.GenerateContentConfig(**cfg)
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            return None, "AI provider returned an empty response"
        return text, None
    except Exception as exc:  # network, quota, auth, safety block ...
        return None, f"AI request failed ({type(exc).__name__})"


def chat_contents(history: List[Any], message: str) -> List[types.Content]:
    """Convert [{role: user|assistant, content}] + the new message into Gemini multi-turn contents."""
    items: List[types.Content] = []
    for turn in history:
        role = "model" if turn.role == "assistant" else "user"
        if not items and role == "model":
            continue  # a conversation must start with the user
        items.append(types.Content(role=role, parts=[types.Part.from_text(text=turn.content)]))
    items.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))
    return items
