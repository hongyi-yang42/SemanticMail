"""AppTest fixture — pre-loads the per-session live-call counter to the cap,
then attempts a cache-missing cached_call_llm. Expected result: RateLimitError
fires, network is never touched, and the BLOCKED marker is rendered.

This file is loaded by `AppTest.from_file` from
`tests/test_runtime_guards.py::test_rate_limit_blocks_after_cap`. The test
sets SEMANTICMAIL_RUNTIME=local_dev and patches llm.cache.call_llm before
loading, so by the time this script runs the cache layer is fully wired.
"""

import streamlit as st

from llm.cache import (
    RateLimitError,
    _RATE_LIMIT_PER_SESSION,
    cached_call_llm,
)

st.session_state["_live_llm_calls"] = _RATE_LIMIT_PER_SESSION

try:
    cached_call_llm("sys", "usr")
    st.text("OK: call went through (BAD)")
except RateLimitError as exc:
    st.text(f"BLOCKED: {exc}")
except Exception as exc:  # noqa: BLE001 — surface any other failure type
    st.text(f"OTHER_ERROR: {type(exc).__name__}: {exc}")
