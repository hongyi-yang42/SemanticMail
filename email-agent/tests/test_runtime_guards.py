"""Runtime-guard tests for the SemanticMail cost-containment layer.

Mocks at the ``call_llm`` / ``call_baseline_llm`` function boundary — not at
the OpenAI ``_client`` singleton — so tests stay robust to changes in client
construction (e.g. after the DeepSeek key is revoked and ``_client`` would be
built with ``api_key=None``).
"""

from __future__ import annotations

import json
import os
import sys

import pytest

from llm.cache import (
    LiveCallBlockedError,
    RateLimitError,
    RUNTIME_LOCAL_DEV,
    RUNTIME_CLI_WARMER,
    RUNTIME_PUBLIC_DEMO,
    cached_call_llm,
    cached_call_baseline_llm,
    _RATE_LIMIT_PER_SESSION,
)

SYS = "sys"
USR = "usr"


# ---------------------------------------------------------------------------
# Unit-level: cache hit / miss authorization
# ---------------------------------------------------------------------------


def test_cache_hit_never_calls_network(tmp_cache_dir, mock_network, monkeypatch):
    """Cache hit path must never reach the network, regardless of runtime."""
    monkeypatch.setenv("SEMANTICMAIL_RUNTIME", RUNTIME_PUBLIC_DEMO)
    from tests.conftest import seed_cache
    seed_cache(tmp_cache_dir, SYS, USR, 0.3, "deepseek-chat", '{"cached": true}')

    result = cached_call_llm(SYS, USR)
    assert json.loads(result) == {"cached": True}
    assert mock_network["deepseek"] == 0


def test_public_demo_blocks_on_miss(tmp_cache_dir, mock_network, monkeypatch):
    """public_demo mode must refuse cache misses without touching the network."""
    monkeypatch.setenv("SEMANTICMAIL_RUNTIME", RUNTIME_PUBLIC_DEMO)
    with pytest.raises(LiveCallBlockedError):
        cached_call_llm(SYS, USR)
    assert mock_network["deepseek"] == 0


def test_unset_runtime_blocks(tmp_cache_dir, mock_network, monkeypatch):
    """Fail closed: an unset SEMANTICMAIL_RUNTIME behaves like public_demo."""
    monkeypatch.delenv("SEMANTICMAIL_RUNTIME", raising=False)
    with pytest.raises(LiveCallBlockedError):
        cached_call_llm(SYS, USR)
    assert mock_network["deepseek"] == 0


def test_unknown_runtime_blocks(tmp_cache_dir, mock_network, monkeypatch):
    """Fail closed: an unknown SEMANTICMAIL_RUNTIME value blocks live calls."""
    monkeypatch.setenv("SEMANTICMAIL_RUNTIME", "production_but_misspelled")
    with pytest.raises(LiveCallBlockedError):
        cached_call_llm(SYS, USR)
    assert mock_network["deepseek"] == 0


def test_local_dev_calls_network_once(tmp_cache_dir, mock_network, monkeypatch):
    """local_dev allows a live call on miss; second call hits the cache."""
    monkeypatch.setenv("SEMANTICMAIL_RUNTIME", RUNTIME_LOCAL_DEV)

    first = cached_call_llm(SYS, USR)
    second = cached_call_llm(SYS, USR)

    assert first == second  # deterministic mock output
    assert mock_network["deepseek"] == 1  # only the miss fired


def test_cli_warmer_calls_network(tmp_cache_dir, mock_network, monkeypatch):
    """cli_warmer allows live calls with no rate-limit attempt."""
    monkeypatch.setenv("SEMANTICMAIL_RUNTIME", RUNTIME_CLI_WARMER)
    result = cached_call_llm(SYS, USR)
    assert json.loads(result) == {"fake": "deepseek_response"}
    assert mock_network["deepseek"] == 1


def test_baseline_blocked_in_public_demo(tmp_cache_dir, mock_network, monkeypatch):
    """Baseline client goes through the same guard."""
    monkeypatch.setenv("SEMANTICMAIL_RUNTIME", RUNTIME_PUBLIC_DEMO)
    with pytest.raises(LiveCallBlockedError):
        cached_call_baseline_llm(SYS, USR)
    assert mock_network["openrouter"] == 0


# ---------------------------------------------------------------------------
# Unit-level: rate limit (per-session runaway)
# ---------------------------------------------------------------------------


def test_rate_limit_blocks_after_cap(tmp_cache_dir, mock_network, monkeypatch):
    """When the per-session counter is at or above the cap, RateLimitError
    fires and the network is never touched.

    Loads a tiny AppTest fixture script that pre-loads the session counter
    to the cap and then attempts a live call. The fixture app is a sibling
    file so that AppTest's script context is fully bootstrapped."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("SEMANTICMAIL_RUNTIME", RUNTIME_LOCAL_DEV)
    fixture = os.path.join(os.path.dirname(__file__), "_rate_limit_app.py")
    at = AppTest.from_file(fixture, default_timeout=30).run()

    rendered = " ".join((t.value or "") for t in at.text)
    assert "BLOCKED" in rendered, f"Expected BLOCKED in output, got: {rendered!r}"
    assert mock_network["deepseek"] == 0


# ---------------------------------------------------------------------------
# App-level: dispatcher + button-gate (via AppTest)
# ---------------------------------------------------------------------------


def _make_app_test(monkeypatch, runtime: str):
    """Helper: build an AppTest for app.py with the given runtime mode."""
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("SEMANTICMAIL_RUNTIME", runtime)
    app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
    return AppTest.from_file(app_path, default_timeout=30)


def test_app_default_load_dispatches_only_overview(tmp_cache_dir, mock_network, monkeypatch):
    """Default app load (Demo Mode, default thread, default section=Overview)
    must fire zero LLM calls in public_demo. The page heading for Thread A
    renders; cache-miss tabs surface the friendly 'not available' info card
    instead of raising."""
    at = _make_app_test(monkeypatch, RUNTIME_PUBLIC_DEMO).run()

    # Section radio defaults to overview
    section_radio = at.radio[0]
    assert section_radio.value == "overview"

    # Thread A heading is rendered via st.header
    assert any("Thread A" in (h.value or "") for h in at.header)

    # The blocked-info card rendered (cache miss in public_demo)
    assert any("public demo" in (i.value or "") for i in at.info)

    # Zero network calls
    assert mock_network["deepseek"] == 0
    assert mock_network["openrouter"] == 0


def test_simulator_zero_calls_before_generate(tmp_cache_dir, mock_network, monkeypatch):
    """Switching to the Simulator section must NOT fire any LLM call until
    the Generate button is clicked."""
    at = _make_app_test(monkeypatch, RUNTIME_PUBLIC_DEMO).run()
    # radio[0] = section, radio[1] = sidebar mode
    at.radio[0].set_value("simulator").run()

    button_labels = [b.label for b in at.button]
    assert any("Generate reply strategies" in (l or "") for l in button_labels)
    assert mock_network["deepseek"] == 0


def test_baseline_zero_calls_before_generate(tmp_cache_dir, mock_network, monkeypatch):
    """Switching to Baseline Comparison must NOT fire any LLM call until
    the Generate button is clicked."""
    at = _make_app_test(monkeypatch, RUNTIME_PUBLIC_DEMO).run()
    at.radio[0].set_value("baseline").run()

    button_labels = [b.label for b in at.button]
    assert any("Generate comparison" in (l or "") for l in button_labels)
    assert mock_network["deepseek"] == 0
    assert mock_network["openrouter"] == 0
