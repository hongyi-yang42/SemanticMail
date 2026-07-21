"""MD5-based caching layer for LLM calls.

Runtime mode
------------
Live (billable) LLM calls are gated by the ``SEMANTICMAIL_RUNTIME`` env var:

- ``public_demo`` — read cache only; cache miss raises :class:`LiveCallBlockedError`.
- ``local_dev``   — cache miss is allowed, subject to a per-session rate limit.
- ``cli_warmer``  — cache miss is allowed, no rate limit (used by offline warmers).
- **unset / unknown** — fail closed; behaves like ``public_demo``.

CLI warmer scripts set ``SEMANTICMAIL_RUNTIME=cli_warmer`` inside their
``if __name__ == "__main__":`` block so that importing them as a module does
not silently enable live calls.
"""

import hashlib
import json
import os
from typing import Optional

from llm.client import call_llm

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
CACHE_DIR = os.path.normpath(CACHE_DIR)


# ---------------------------------------------------------------------------
# Runtime authorization
# ---------------------------------------------------------------------------

RUNTIME_PUBLIC_DEMO = "public_demo"
RUNTIME_LOCAL_DEV = "local_dev"
RUNTIME_CLI_WARMER = "cli_warmer"

_LIVE_OK = {RUNTIME_LOCAL_DEV, RUNTIME_CLI_WARMER}

_RATE_LIMIT_PER_SESSION = int(os.getenv("SEMANTICMAIL_RATE_LIMIT", "20"))


class LiveCallBlockedError(Exception):
    """Raised when a cache miss would require a live call that the current
    runtime mode does not authorize."""


class RateLimitError(Exception):
    """Raised when a browser session has exceeded its per-session live-call cap."""


def _runtime() -> str:
    return os.getenv("SEMANTICMAIL_RUNTIME", "").strip().lower()


def _assert_live_ok() -> None:
    if _runtime() not in _LIVE_OK:
        raise LiveCallBlockedError(
            f"SEMANTICMAIL_RUNTIME={_runtime() or '<unset>'!r}; "
            f"live LLM calls require one of {sorted(_LIVE_OK)}."
        )


def _check_session_rate_limit() -> None:
    """Per-session runaway guard. Not a global cost ceiling — concurrent
    clients and new sessions are not constrained by this counter. Only
    enforced when a Streamlit script context is available."""
    if _runtime() == RUNTIME_CLI_WARMER:
        return
    try:
        import streamlit as st
        used = st.session_state.get("_live_llm_calls", 0)
    except Exception:
        # No Streamlit context (e.g. CLI warmer, pytest unit test) — skip.
        return
    if used >= _RATE_LIMIT_PER_SESSION:
        raise RateLimitError(
            f"Session cap ({_RATE_LIMIT_PER_SESSION}) reached. "
            f"Refresh the page to reset."
        )
    st.session_state["_live_llm_calls"] = used + 1


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


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

    Checks the cache first. On a miss, authorizes a live call via the current
    ``SEMANTICMAIL_RUNTIME`` and per-session rate limit before proceeding.

    Args:
        system_prompt: System-level instructions.
        user_prompt: User message content.
        temperature: Sampling temperature.
        model: Model ID (default ``deepseek-chat``).

    Returns:
        The response content string.

    Raises:
        LiveCallBlockedError: On cache miss when the runtime mode does not
            authorize live calls.
        RateLimitError: On cache miss when the per-session cap is exhausted.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    key = _cache_key(system_prompt, user_prompt, temperature, model)
    path = _cache_path(key)

    # Cache hit
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["response"]

    # Cache miss — authorize live call
    _assert_live_ok()
    _check_session_rate_limit()
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

    Raises:
        LiveCallBlockedError: On cache miss when the runtime mode does not
            authorize live calls.
        RateLimitError: On cache miss when the per-session cap is exhausted.
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

    # Cache miss — authorize live call
    _assert_live_ok()
    _check_session_rate_limit()
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

    Same caching + authorization strategy as :func:`cached_call_llm` but
    routes through :func:`llm.baseline_client.call_baseline_llm`.

    Args:
        system_prompt: System-level instructions.
        user_prompt: User message content.
        temperature: Sampling temperature.
        model: Cache key model identifier (default ``baseline-gptoss``).

    Returns:
        The response content string.

    Raises:
        LiveCallBlockedError: On cache miss when the runtime mode does not
            authorize live calls.
        RateLimitError: On cache miss when the per-session cap is exhausted.
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

    # Cache miss — authorize live call
    _assert_live_ok()
    _check_session_rate_limit()
    response_text = call_baseline_llm(system_prompt, user_prompt, temperature)

    # Save to cache
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"response": response_text}, f, ensure_ascii=False, indent=2)

    return response_text
