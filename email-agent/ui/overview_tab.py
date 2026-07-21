"""Tab 1 — Overview: thread metadata, emails, classification, tasks, summary."""

from __future__ import annotations

import json
from typing import Any, Optional

import streamlit as st

from data.threads import get_thread_display_names, get_thread_by_name
from llm.cache import LiveCallBlockedError, cached_call_llm
from prompts.classify import CLASSIFY_SYSTEM_PROMPT, CLASSIFY_USER_PROMPT_TEMPLATE
from prompts.decompose import DECOMPOSE_SYSTEM_PROMPT, DECOMPOSE_USER_PROMPT_TEMPLATE
from prompts.summarize import SUMMARIZE_SYSTEM_PROMPT, SUMMARIZE_USER_PROMPT_TEMPLATE
from ui.components import (
    thread_display,
    render_classification_result,
    render_action_items,
    render_summary,
)

_BLOCKED_MSG = (
    "Live analysis isn't available in the public demo for this thread. "
    "Cached results for Threads A, B, C are available — pick one in the sidebar."
)


def _format_messages(messages: list[dict[str, Any]]) -> str:
    """Format messages into a readable string for prompt templates."""
    parts: list[str] = []
    for i, msg in enumerate(messages):
        parts.append(
            f"[Email {i + 1}] From: {msg['from']}\n"
            f"To: {msg['to']}\n"
            f"Date: {msg['date']}\n"
            f"Subject: {msg['subject']}\n\n"
            f"{msg['body']}"
        )
    return "\n\n---\n\n".join(parts)


def _safe_cached_call(system_prompt: str, user_prompt: str, spinner_label: str) -> Optional[str]:
    """Run a cached LLM call. On LiveCallBlockedError, render the info card
    once and return None so the caller can short-circuit."""
    try:
        with st.spinner(spinner_label):
            return cached_call_llm(system_prompt, user_prompt)
    except LiveCallBlockedError:
        st.info(_BLOCKED_MSG)
        return None


def render_overview_tab(thread_data: dict[str, Any]) -> None:
    """Render the Overview tab for a given thread.

    Args:
        thread_data: The full thread dictionary.
    """
    # --- Thread metadata ---
    st.header(f"📧 {thread_data['title']}")
    st.caption(f"Scenario: {thread_data['scenario']}")
    st.write(thread_data.get("description", ""))

    # Pragmatic signals
    signals = thread_data.get("pragmatic_signals", [])
    if signals:
        st.markdown("**🔍 Pragmatic Signals:**")
        for s in signals:
            st.markdown(f"- {s}")

    st.divider()

    # --- Email messages ---
    st.subheader("📬 Email Thread")
    thread_display(thread_data["messages"])

    st.divider()

    # --- Prepare prompt inputs ---
    messages_text = _format_messages(thread_data["messages"])
    subject = thread_data["messages"][0].get("subject", "") if thread_data["messages"] else ""

    # --- Module 1: Classification ---
    st.subheader("🏷️ Module 1: Intent & Urgency Classification")
    classify_user = CLASSIFY_USER_PROMPT_TEMPLATE.format(
        subject=subject, messages=messages_text
    )
    classify_raw = _safe_cached_call(
        CLASSIFY_SYSTEM_PROMPT, classify_user, "Running classification..."
    )
    if classify_raw is None:
        return
    try:
        classify_result = json.loads(classify_raw)
        render_classification_result(classify_result)
    except json.JSONDecodeError:
        st.error("Failed to parse classification result.")
        st.text(classify_raw)

    st.divider()

    # --- Module 2: Task Extraction ---
    st.subheader("✅ Module 2: Task Extraction")
    decompose_user = DECOMPOSE_USER_PROMPT_TEMPLATE.format(
        subject=subject, messages=messages_text
    )
    decompose_raw = _safe_cached_call(
        DECOMPOSE_SYSTEM_PROMPT, decompose_user, "Extracting action items..."
    )
    if decompose_raw is None:
        return
    try:
        decompose_result = json.loads(decompose_raw)
        render_action_items(decompose_result)
    except json.JSONDecodeError:
        st.error("Failed to parse task extraction result.")
        st.text(decompose_raw)

    st.divider()

    # --- Module 3: Summary ---
    st.subheader("📝 Module 3: Thread Summary")
    summarize_user = SUMMARIZE_USER_PROMPT_TEMPLATE.format(
        subject=subject, messages=messages_text
    )
    summarize_raw = _safe_cached_call(
        SUMMARIZE_SYSTEM_PROMPT, summarize_user, "Generating summary..."
    )
    if summarize_raw is None:
        return
    try:
        summarize_result = json.loads(summarize_raw)
        render_summary(summarize_result)
    except json.JSONDecodeError:
        st.error("Failed to parse summary result.")
        st.text(summarize_raw)
