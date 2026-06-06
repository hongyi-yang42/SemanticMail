"""Tab 2 — Subtext Analysis (full implementation)."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from llm.cache import cached_call_llm
from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt
from ui.components import email_card, risk_badge, tone_emoji, thread_display

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RISK_COLORS: dict[str, str] = {
    "safe": "#28a745",
    "caution": "#d39e00",
    "warning": "#fd7e14",
    "critical": "#dc3545",
}

_TONE_EMOJI_MAP: dict[str, str] = {
    "enthusiastic": "🤩",
    "warm": "😊",
    "neutral": "😐",
    "cool": "😰",
    "evasive": "🫣",
    "hostile": "😡",
}

_TONE_COLORS: dict[str, str] = {
    "enthusiastic": "#28a745",
    "warm": "#8bc34a",
    "neutral": "#9e9e9e",
    "cool": "#2196f3",
    "evasive": "#ff9800",
    "hostile": "#dc3545",
}

_POLITENESS_LABELS: dict[str, str] = {
    "bald_on_record": "🔴 Bald on Record",
    "positive_politeness": "🟢 Positive Politeness",
    "negative_politeness": "🔵 Negative Politeness",
    "off_record": "🟡 Off Record",
    "avoidance": "⚪ Avoidance",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_tone_emoji(label: str) -> str:
    return _TONE_EMOJI_MAP.get(label.lower(), "💬")


def _get_tone_color(label: str) -> str:
    return _TONE_COLORS.get(label.lower(), "#9e9e9e")


def _get_risk_color(level: str) -> str:
    return _RISK_COLORS.get(level.lower(), "#9e9e9e")


def _render_risk_header(email_idx: int, sender: str, risk_level: str) -> None:
    color = _get_risk_color(risk_level)
    st.markdown(
        f'<div style="background-color:{color}22; border-left:4px solid {color}; '
        f'padding:10px 14px; border-radius:6px; margin-bottom:8px;">'
        f'<span style="font-size:1.1em; font-weight:600;">'
        f"📧 Email {email_idx} — {sender}</span>"
        f' <span style="background-color:{color}; color:white; padding:2px 8px; '
        f'border-radius:10px; font-size:0.8em; margin-left:8px;">'
        f"{risk_level.upper()}</span></div>",
        unsafe_allow_html=True,
    )


def _render_gricean_violations(violations: list[dict[str, str]]) -> None:
    if not violations:
        st.markdown("✅ No Gricean violations detected.")
        return
    for v in violations:
        maxim = v.get("maxim", "unknown")
        desc = v.get("description", "")
        signal = v.get("signal", "")
        st.markdown(f"⚠️ **{maxim.title()} Maxim** — {desc}")
        if signal:
            st.markdown(f"&nbsp;&nbsp;&nbsp;↳ *Signal: {signal}*")


def _render_analysis_card(analysis: dict[str, Any]) -> None:
    idx = analysis.get("email_index", 0)
    sender = analysis.get("from", "Unknown")
    risk = analysis.get("risk_level", "safe")
    pragmatic = analysis.get("pragmatic_inference", {})
    social = analysis.get("social_dynamics", {})

    _render_risk_header(idx, sender, risk)

    with st.expander("📝 Literal → Pragmatic Inference", expanded=True):
        st.markdown("**Literal Content:**")
        st.write(analysis.get("literal_content", ""))
        st.divider()
        st.markdown("**Pragmatic Inference:**")
        st.markdown("*Gricean Violations:*")
        _render_gricean_violations(pragmatic.get("gricean_violations", []))
        speech_acts = pragmatic.get("indirect_speech_acts", [])
        if speech_acts:
            st.markdown("*Indirect Speech Acts:*")
            for sa in speech_acts:
                st.markdown(f"• {sa}")
        else:
            st.markdown("*Indirect Speech Acts:* None detected.")
        st.markdown(f"**Implicature:** {pragmatic.get('implicature', 'N/A')}")

    with st.expander("👥 Social Dynamics"):
        st.markdown(f"**Power Relationship:** {social.get('power_relationship', 'N/A')}")
        st.markdown(f"**Face Threats:** {social.get('face_threats', 'N/A')}")
        strategy = social.get("politeness_strategy", "unknown")
        strategy_label = _POLITENESS_LABELS.get(strategy, strategy)
        st.markdown(f"**Politeness Strategy:** {strategy_label}")
        tone = social.get("tone_label", "neutral")
        st.markdown(f"**Tone:** {_get_tone_emoji(tone)} {tone.title()}")

    st.markdown("---")


def _render_tone_trajectory(trajectory: list[str]) -> None:
    """Render tone trajectory as a horizontal timeline with emojis and arrows."""
    if not trajectory:
        return

    n = len(trajectory)
    cols = st.columns(n + n - 1)  # interleaved: tone, arrow, tone, arrow, ...
    col_idx = 0
    for i, tone in enumerate(trajectory):
        emoji = _get_tone_emoji(tone)
        color = _get_tone_color(tone)
        with cols[col_idx]:
            st.markdown(
                f'<div style="text-align:center; padding:6px;">'
                f'<span style="font-size:1.6em;">{emoji}</span><br>'
                f'<span style="color:{color}; font-weight:600; '
                f'font-size:0.85em;">{tone.title()}</span></div>',
                unsafe_allow_html=True,
            )
        col_idx += 1
        if i < n - 1:
            with cols[col_idx]:
                st.markdown(
                    '<div style="text-align:center; padding-top:14px;">'
                    '<span style="font-size:1.4em; color:#999;">→</span></div>',
                    unsafe_allow_html=True,
                )
            col_idx += 1


def _render_thread_level(thread_level: dict[str, Any]) -> None:
    """Render the thread-level analysis section."""
    st.markdown("### 🔗 Thread-Level Analysis")

    trajectory = thread_level.get("tone_trajectory", [])
    st.markdown("**Tone Trajectory:**")
    _render_tone_trajectory(trajectory)

    st.markdown("---")

    overall_risk = thread_level.get("overall_risk", "safe")
    st.markdown(f"**Overall Risk:** {risk_badge(overall_risk)}")

    strategy = thread_level.get("recommended_strategy", "No recommendation available.")
    st.info(f"💡 **Recommended Strategy:**\n\n{strategy}")

    mistakes = thread_level.get("common_mistakes", [])
    if mistakes:
        warning_lines = "**⚠️ Common Mistakes to Avoid:**\n\n"
        for m in mistakes:
            warning_lines += f"- {m}\n"
        st.warning(warning_lines)


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------


def render_subtext_tab(thread_data: dict) -> None:
    """Render the Subtext Analysis tab (Tab 2).

    Performs a 4-layer Pragmatic Inference Chain analysis on the email thread,
    showing per-email analysis cards and thread-level insights.

    Args:
        thread_data: The full thread dictionary.
    """
    st.markdown("## 🔍 Social Subtext Analyzer")
    st.caption(
        "4-Layer Pragmatic Inference Chain — powered by Grice, Brown & Levinson, "
        "and Spencer-Oatey rapport management theory."
    )

    # --- LLM call (cached) ---
    user_prompt = format_subtext_user_prompt(thread_data)

    with st.spinner("Running 4-layer Pragmatic Inference Chain..."):
        try:
            raw_response = cached_call_llm(
                SUBTEXT_SYSTEM_PROMPT, user_prompt, temperature=0.3
            )
        except Exception as exc:
            st.error(f"LLM call failed: {exc}")
            return

    # --- Parse JSON ---
    try:
        result: dict[str, Any] = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        st.error(f"Failed to parse LLM response as JSON: {exc}")
        with st.expander("Raw response (for debugging)"):
            st.code(raw_response, language="json")
        return

    per_email = result.get("per_email_analysis", [])
    thread_level = result.get("thread_level", {})

    if not per_email:
        st.warning("No per-email analysis returned.")
        return

    # --- Two-column layout: thread | analysis ---
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("### 📨 Email Thread")
        messages = thread_data.get("messages", [])
        for i, msg in enumerate(messages):
            email_card(msg, i)

    with col_right:
        st.markdown("### 🧠 Per-Email PIC Analysis")
        for analysis in per_email:
            _render_analysis_card(analysis)

    # --- Thread-level analysis (full width) ---
    st.markdown("---")
    if thread_level:
        _render_thread_level(thread_level)
    else:
        st.warning("No thread-level analysis returned.")
