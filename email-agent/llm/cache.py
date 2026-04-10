"""MD5-based caching layer for LLM calls."""

import hashlib
import json
import os
from typing import Optional

from llm.client import call_llm

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
CACHE_DIR = os.path.normpath(CACHE_DIR)


def _cache_key(system_prompt: str, user_prompt: str, temperature: float) -> str:
    """Generate an MD5 hash key from prompt components."""
    raw = f"{system_prompt}||{user_prompt}||{temperature}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> str:
    """Return the file path for a given cache key."""
    return os.path.join(CACHE_DIR, f"{key}.json")


def cached_call_llm(
    system_prompt: str, user_prompt: str, temperature: float = 0.3
) -> str:
    """Call the LLM with caching.

    Checks the cache first. On a miss, calls the LLM and stores the result
    as a JSON file ``{response: ...}``.

    Args:
        system_prompt: System-level instructions.
        user_prompt: User message content.
        temperature: Sampling temperature.

    Returns:
        The response content string.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    key = _cache_key(system_prompt, user_prompt, temperature)
    path = _cache_path(key)

    # Cache hit
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["response"]

    # Cache miss — call LLM
    response_text = call_llm(system_prompt, user_prompt, temperature)

    # Save to cache
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"response": response_text}, f, ensure_ascii=False, indent=2)

    return response_text
