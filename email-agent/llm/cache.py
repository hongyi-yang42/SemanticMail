"""MD5-based caching layer for LLM calls."""

import hashlib
import json
import os
from typing import Optional

from llm.client import call_llm

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
CACHE_DIR = os.path.normpath(CACHE_DIR)


def _cache_key(system_prompt: str, user_prompt: str, temperature: float, model: str = "deepseek-chat") -> str:
    """Generate an MD5 hash key from prompt components and model ID."""
    raw = f"{system_prompt}||{user_prompt}||{temperature}||{model}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> str:
    """Return the file path for a given cache key."""
    return os.path.join(CACHE_DIR, f"{key}.json")


def cached_call_llm(
    system_prompt: str, user_prompt: str, temperature: float = 0.3, model: str = "deepseek-chat"
) -> str:
    """Call the LLM with caching.

    Checks the cache first. On a miss, calls the LLM and stores the result
    as a JSON file ``{response: ...}``.

    Args:
        system_prompt: System-level instructions.
        user_prompt: User message content.
        temperature: Sampling temperature.
        model: Model ID (default ``deepseek-chat``).

    Returns:
        The response content string.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    key = _cache_key(system_prompt, user_prompt, temperature, model)
    path = _cache_path(key)

    # Cache hit
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["response"]

    # Cache miss — call LLM
    response_text = call_llm(system_prompt, user_prompt, temperature, model)

    # Save to cache
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"response": response_text}, f, ensure_ascii=False, indent=2)

    return response_text


def cached_call_llm_with_usage(
    system_prompt: str, user_prompt: str, temperature: float = 0.3, model: str = "deepseek-chat",
) -> tuple[str, dict]:
    """Call LLM with caching and token tracking.

    On cache miss: captures real token counts and wall-clock time.
    On cache hit: estimates tokens (chars/4) with source="estimated".

    Returns (response_text, usage_dict).  usage_dict includes a ``source``
    key (``"measured"`` or ``"estimated"``) and ``wall_ms``.
    """
    import time as _time

    from llm.client import call_llm_with_usage as _call_with_usage

    os.makedirs(CACHE_DIR, exist_ok=True)

    key = _cache_key(system_prompt, user_prompt, temperature, model)
    path = _cache_path(key)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        response_text = data["response"]
        est_in = max(1, (len(system_prompt) + len(user_prompt)) // 4)
        est_out = max(1, len(response_text) // 4)
        return response_text, {
            "prompt_tokens": est_in,
            "completion_tokens": est_out,
            "total_tokens": est_in + est_out,
            "source": "estimated",
            "wall_ms": 0,
        }

    t0 = _time.time()
    response_text, real_usage = _call_with_usage(system_prompt, user_prompt, temperature, model)
    wall_ms = int((_time.time() - t0) * 1000)
    real_usage["source"] = "measured"
    real_usage["wall_ms"] = wall_ms

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"response": response_text}, f, ensure_ascii=False, indent=2)

    return response_text, real_usage


def cached_call_baseline_llm(
    system_prompt: str, user_prompt: str, temperature: float = 0.3, model: str = "baseline-gptoss"
) -> str:
    """Call the baseline LLM (GPT-OSS via OpenRouter) with caching.

    Same caching strategy as :func:`cached_call_llm` but routes through
    :func:`llm.baseline_client.call_baseline_llm` instead.

    Args:
        system_prompt: System-level instructions.
        user_prompt: User message content.
        temperature: Sampling temperature.
        model: Cache key model identifier (default ``baseline-gptoss``).

    Returns:
        The response content string.
    """
    from llm.baseline_client import call_baseline_llm

    os.makedirs(CACHE_DIR, exist_ok=True)

    key = _cache_key(system_prompt, user_prompt, temperature, model)
    path = _cache_path(key)

    # Cache hit
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["response"]

    # Cache miss — call baseline LLM
    response_text = call_baseline_llm(system_prompt, user_prompt, temperature)

    # Save to cache
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"response": response_text}, f, ensure_ascii=False, indent=2)

    return response_text
