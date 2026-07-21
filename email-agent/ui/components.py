"""Reusable UI components for SemanticMail."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Optional, TypeVar

import streamlit as st

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Emoji helpers
# ---------------------------------------------------------------------------

_TONE_EMOJI_MAP: dict[str, str] = {
    "formal": "🎩",
    "friendly": "😊",
    "neutral": "😐",
    "cold": "❄️",
    "urgent": "🔥",
    "enthusiastic": "🎉",
    "polite": "🙏",
    "hesitant": "🤔",
    "frustrated": "😤",
    "indirect": "🔄",
}

_RISK_BADGE_MAP: dict[str, str] = {
    "low": "🟢 Low",
    "medium": "🟡 Medium",
    "high": "🟠 High",
    "critical": "🔴 Critical",
}


def tone_emoji(tone_label: str) -> str:
    """Return an emoji representing the given tone label."""
    return _TONE_EMOJI_MAP.get(tone_label.lower(), "💬")


def risk_badge(risk_level: str) -> str:
    """Return a colored emoji badge for the given risk level."""
    return _RISK_BADGE_MAP.get(risk_level.lower(), "⚪ Unknown")


# ---------------------------------------------------------------------------
# Card components
# ---------------------------------------------------------------------------


def email_card(msg: dict[str, Any], index: int) -> None:
    """Render a single email message as an expandable card.

    Args:
        msg: A dict with keys ``from``, ``to``, ``date``, ``subject``, ``body``.
        index: Zero-based index of the message in the thread.
    """
    sender = msg.get("from", "Unknown")
    date = msg.get("date", "Unknown")
    subject = msg.get("subject", "(no subject)")
    body = msg.get("body", "")

    with st.expander(f"📧 Email {index + 1} — {sender.split('<')[0].strip()} ({date})"):
        st.markdown(f"**From:** {sender}  ")
        st.markdown(f"**To:** {msg.get('to', 'Unknown')}  ")
        st.markdown(f"**Date:** {date}  ")
        st.markdown(f"**Subject:** {subject}")
        st.divider()
        st.text(body)


def thread_display(messages: list[dict[str, Any]]) -> None:
    """Render all email messages in a thread.

    Args:
        messages: List of message dicts (same format as :func:`email_card`).
    """
    for i, msg in enumerate(messages):
        email_card(msg, i)


# ---------------------------------------------------------------------------
# Result renderers
# ---------------------------------------------------------------------------


def render_email_message(msg: dict[str, Any]) -> None:
    """Render a compact email message (non-expandable)."""
    st.markdown(
        f"**{msg.get('from', 'Unknown').split('<')[0].strip()}** "
        f"*({msg.get('date', 'Unknown')})*"
    )
    st.text(msg.get("body", ""))


def render_classification_result(result: dict[str, Any]) -> None:
    """Render classification results with formatting."""
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Intent", result.get("intent", "N/A"))
    with col2:
        st.metric("Urgency", risk_badge(result.get("urgency", "unknown")))

    if "urgency_signals" in result:
        st.markdown("**Urgency Signals:**")
        for signal in result["urgency_signals"]:
            st.markdown(f"- {signal}")

    confidence = result.get("confidence", 0)
    st.progress(min(confidence, 1.0))
    st.caption(f"Confidence: {confidence:.0%}")


def render_action_items(result: dict[str, Any]) -> None:
    """Render extracted action items."""
    items = result.get("action_items", [])
    if not items:
        st.info("No action items found.")
        return

    for i, item in enumerate(items):
        status_emoji = {
            "pending": "⏳",
            "completed": "✅",
            "blocked": "🚫",
            "unclear": "❓",
        }.get(item.get("status", "unclear"), "❓")

        with st.expander(
            f"{status_emoji} Task {i + 1}: {item.get('task', 'Untitled')}"
        ):
            st.markdown(f"**Owner:** {item.get('owner', 'Unassigned')}")
            st.markdown(f"**Deadline:** {item.get('deadline', 'Not specified')}")
            st.markdown(f"**Status:** {item.get('status', 'unclear')}")
            st.markdown(f"**Source:** {item.get('source_email', 'Unknown')}")


def render_summary(result: dict[str, Any]) -> None:
    """Render thread summary."""
    st.markdown("### 📋 Summary")
    st.write(result.get("summary", "No summary available."))

    decisions = result.get("key_decisions", [])
    if decisions:
        st.markdown("### ✅ Key Decisions")
        for d in decisions:
            st.markdown(f"- {d}")

    questions = result.get("open_questions", [])
    if questions:
        st.markdown("### ❓ Open Questions")
        for q in questions:
            st.markdown(f"- {q}")

    participants = result.get("participants", [])
    if participants:
        st.markdown("### 👥 Participants")
        st.write(", ".join(participants))


# ---------------------------------------------------------------------------
# LLM call gating
# ---------------------------------------------------------------------------


def _gated_session_key(feature: str, thread_data: dict, prompt_version: str, model: str) -> str:
    """Build a session_state key that captures everything that would change the
    LLM output. Prompt or model bumps invalidate stale entries automatically."""
    digest = hashlib.md5(
        json.dumps(thread_data, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    return f"{feature}|{digest}|{prompt_version}|{model}"


def gated_call(
    *,
    feature: str,
    thread_data: dict,
    prompt_version: str,
    model: str,
    button_label: str,
    placeholder: str,
    generate_fn: Callable[[], T],
) -> Optional[T]:
    """Render a placeholder + button; cache only successful results.

    The session key is derived from ``feature``, a hash of ``thread_data``,
    ``prompt_version``, and ``model`` so prompt or model bumps invalidate
    stale entries.

    Args:
        feature: Short identifier of the calling feature (e.g. ``"simulator"``).
        thread_data: The thread dict the call depends on.
        prompt_version: A version string bumped when the prompt or temperature
            changes.
        model: The model identifier used in the cache key.
        button_label: Visible button text.
        placeholder: Visible info text rendered before the button is clicked.
        generate_fn: Zero-arg callable that performs the call(s). Should raise
            ``LiveCallBlockedError`` if the runtime refuses — that exception is
            shown inline and never cached.

    Returns:
        The cached/generated result, or ``None`` if the user hasn't clicked
        the button yet (or the call was blocked).
    """
    from llm.cache import LiveCallBlockedError, RateLimitError

    key = _gated_session_key(feature, thread_data, prompt_version, model)

    cached = st.session_state.get(key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    st.info(placeholder)
    if st.button(button_label, key=f"btn|{key}", type="primary"):
        try:
            result = generate_fn()
        except LiveCallBlockedError as exc:
            st.error(
                f"{exc}\n\n"
                "Live analysis isn't available in the public demo for this thread. "
                "Cached results for Threads A, B, C are available — pick one in the sidebar."
            )
            return None
        except RateLimitError as exc:
            st.error(str(exc))
            return None
        # Cache only on success
        st.session_state[key] = result
        st.rerun()
    return None
