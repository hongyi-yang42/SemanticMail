"""Reusable UI components for SemanticMail."""

from __future__ import annotations

from typing import Any

import streamlit as st


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
