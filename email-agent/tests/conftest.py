"""Shared pytest fixtures for SemanticMail runtime-guard tests."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import pytest

# Make sure email-agent/ is on sys.path so `import llm.cache` etc. work when
# pytest is invoked from the repo root or from inside email-agent/.
_AGENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)


@pytest.fixture(autouse=True)
def isolated_runtime_env(monkeypatch):
    """Force a clean SEMANTICMAIL_RUNTIME before each test."""
    monkeypatch.delenv("SEMANTICMAIL_RUNTIME", raising=False)
    yield


@pytest.fixture
def tmp_cache_dir(tmp_path, monkeypatch):
    """Redirect llm.cache.CACHE_DIR to a per-test tmp directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    import llm.cache as cache_mod
    monkeypatch.setattr(cache_mod, "CACHE_DIR", str(cache_dir))
    return cache_dir


@pytest.fixture
def mock_network(monkeypatch):
    """Patch the bound names `call_llm` and `call_baseline_llm` inside
    `llm.cache` — NOT the underlying `_client`. This keeps tests robust to
    changes in how the OpenAI client is constructed (e.g. after the
    DeepSeek key is revoked)."""
    calls = {"deepseek": 0, "openrouter": 0, "with_usage": 0}

    def fake_call_llm(system_prompt, user_prompt, temperature=0.3, model="deepseek-chat"):
        calls["deepseek"] += 1
        return '{"fake": "deepseek_response"}'

    def fake_call_baseline_llm(system_prompt, user_prompt, temperature=0.3):
        calls["openrouter"] += 1
        return "fake_baseline_response"

    def fake_call_with_usage(system_prompt, user_prompt, temperature=0.3, model="deepseek-chat"):
        calls["with_usage"] += 1
        return '{"fake": "with_usage"}', {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }

    import llm.cache as cache_mod
    monkeypatch.setattr(cache_mod, "call_llm", fake_call_llm)
    # cached_call_baseline_llm does `from llm.baseline_client import call_baseline_llm`
    # at call time, so patch the source module.
    import llm.baseline_client as baseline_mod
    monkeypatch.setattr(baseline_mod, "call_baseline_llm", fake_call_baseline_llm)
    # cached_call_llm_with_usage does `from llm.client import call_llm_with_usage`
    # at call time.
    import llm.client as client_mod
    monkeypatch.setattr(client_mod, "call_llm_with_usage", fake_call_with_usage)
    return calls


def seed_cache(cache_dir, system_prompt: str, user_prompt: str, temperature: float,
               model: str, response: Any) -> None:
    """Write a fake cache entry that matches the given call signature."""
    import hashlib
    raw = f"{system_prompt}||{user_prompt}||{temperature}||{model}"
    key = hashlib.md5(raw.encode("utf-8")).hexdigest()
    path = cache_dir / f"{key}.json"
    path.write_text(json.dumps({"response": response}))
