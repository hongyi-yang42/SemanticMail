"""Tab 5 — Ablation Comparison (3 conditions side by side)."""

from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st

from llm.cache import _cache_key
from prompts.ablation import (
    ABLATION_SYSTEM_PROMPT,
    NO_ANALYSIS_SYSTEM_PROMPT,
    format_ablation_user_prompt,
    format_no_analysis_user_prompt,
)
from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt
from ui.components import risk_badge

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "deepseek-chat"

CONDITIONS = [
    ("A: Full PIC", "A_full_pic", SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt),
    ("B: Generic", "B_generic", ABLATION_SYSTEM_PROMPT, format_ablation_user_prompt),
    ("C: No Framing", "C_no_analysis", NO_ANALYSIS_SYSTEM_PROMPT, format_no_analysis_user_prompt),
]

_RISK_ORDER = {"safe": 0, "caution": 1, "warning": 2, "critical": 3}

_RISK_COLORS = {
    "safe": "#28a745",
    "caution": "#d39e00",
    "warning": "#fd7e14",
    "critical": "#dc3545",
    "N/A": "#9e9e9e",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_result(sys_prompt: str, fmt_fn, thread: dict) -> dict | None:
    """Load a cached ablation result, returning parsed JSON or None."""
    user_prompt = fmt_fn(thread)
    key = _cache_key(sys_prompt, user_prompt, 0.3, MODEL)
    from llm.cache import _cache_path

    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    text = raw.get("response", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}


def _extract(analysis: dict | None) -> dict:
    """Extract comparison fields from a parsed analysis."""
    if not analysis or "_raw" in analysis:
        return {
            "risk": "N/A",
            "signals": 0,
            "tones": [],
            "tones_str": "N/A",
            "key_observation": "No analysis available.",
        }

    thread_level = analysis.get("thread_level", {})
    per_email = analysis.get("per_email_analysis", [])

    risk = thread_level.get("overall_risk", "N/A")
    tones = thread_level.get("tone_trajectory", [])

    signal_count = 0
    best_observation = ""
    best_signal_count = 0
    for email in per_email:
        pi = email.get("pragmatic_inference", {})
        violations = pi.get("gricean_violations", [])
        speech_acts = pi.get("indirect_speech_acts", [])
        signal_count += len(violations) + len(speech_acts)

        imp = pi.get("implicature", "").strip()
        if imp and len(violations) + len(speech_acts) > best_signal_count:
            best_signal_count = len(violations) + len(speech_acts)
            best_observation = imp

    if not best_observation:
        strategies = []
        for email in per_email:
            sd = email.get("social_dynamics", {})
            s = sd.get("politeness_strategy", "")
            if s:
                strategies.append(s)
        if strategies:
            best_observation = f"Dominant strategy: {max(set(strategies), key=strategies.count)}"
        elif thread_level.get("recommended_strategy"):
            best_observation = thread_level["recommended_strategy"][:120]

    return {
        "risk": risk,
        "signals": signal_count,
        "tones": tones,
        "tones_str": " → ".join(tones) if tones else "N/A",
        "key_observation": best_observation or "No key observation.",
    }


def _risk_badge_html(level: str) -> str:
    color = _RISK_COLORS.get(level, "#9e9e9e")
    label = level.upper()
    return (
        f'<span style="background-color:{color}; color:white; padding:4px 12px; '
        f'border-radius:12px; font-size:0.9em; font-weight:600;">{label}</span>'
    )


def _divergence_summary(extracts: dict[str, dict]) -> str | None:
    """Return a human-readable divergence note, or None if all agree."""
    risks = {k: v["risk"] for k, v in extracts.items()}
    unique_risks = set(risks.values())

    if len(unique_risks) <= 1:
        return None

    risk_levels = sorted(
        [(k, v) for k, v in risks.items()],
        key=lambda x: _RISK_ORDER.get(x[1], -1),
        reverse=True,
    )
    highest_cond, highest_risk = risk_levels[0]
    lowest_cond, lowest_risk = risk_levels[-1]

    base = f"{highest_cond} = **{highest_risk}** vs {lowest_cond} = **{lowest_risk}**"
    if highest_cond == "A: Full PIC":
        return (
            f"{base} — the PIC framework detected social-pressure escalation "
            f"that generic analysis missed."
        )
    elif highest_cond == "B: Generic":
        return f"{base} — Generic subtext analysis flagged higher risk than the structured PIC."
    else:
        return f"{base} — No-framing review flagged the highest risk."


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------


def render_ablation_tab(thread_data: dict) -> None:
    """Render the Ablation Comparison tab (Tab 5)."""
    st.markdown("## ⚖️ Ablation Comparison")
    st.caption(
        "Three conditions compared: **A) Full PIC** (Grice + Brown & Levinson + Spencer-Oatey), "
        "**B) Generic** subtext analysis, **C) No framing** (plain review). "
        "Same JSON schema enforced across all conditions."
    )

    # --- Load all 3 conditions ---
    extracts: dict[str, dict] = {}
    raw_analyses: dict[str, dict | None] = {}

    for label, _, sys_prompt, fmt_fn in CONDITIONS:
        analysis = _load_result(sys_prompt, fmt_fn, thread_data)
        raw_analyses[label] = analysis
        extracts[label] = _extract(analysis)

    # --- Check if any data loaded ---
    loaded_count = sum(1 for v in raw_analyses.values() if v is not None)
    if loaded_count == 0:
        st.warning(
            "No ablation caches found for this thread. "
            "Run `warm_cache_ablation.py` to generate them."
        )
        return

    # --- Divergence banner ---
    div_note = _divergence_summary(extracts)
    if div_note:
        st.markdown(
            '<div style="background-color:#fff3cd; border-left:4px solid #d39e00; '
            'padding:10px 14px; border-radius:6px; margin-bottom:16px;">'
            f'<b>Divergence detected:</b> {div_note}</div>',
            unsafe_allow_html=True,
        )
    else:
        risks = [v["risk"] for v in extracts.values()]
        st.markdown(
            '<div style="background-color:#d4edda; border-left:4px solid #28a745; '
            'padding:10px 14px; border-radius:6px; margin-bottom:16px;">'
            f'<b>All conditions agree:</b> risk = **{risks[0]}**</div>',
            unsafe_allow_html=True,
        )

    # --- 3-column layout ---
    cols = st.columns(3)

    for i, (label, _, _, _) in enumerate(CONDITIONS):
        ext = extracts[label]
        analysis = raw_analyses[label]

        with cols[i]:
            # Condition header
            st.markdown(f"### {label}")

            if analysis is None:
                st.info("Cache not found for this condition.")
                continue

            # Risk badge
            risk_html = _risk_badge_html(ext["risk"])
            st.markdown(
                f'<div style="margin-bottom:8px;">Risk Level: {risk_html}</div>',
                unsafe_allow_html=True,
            )

            # Signal count
            st.metric("Pragmatic Signals", ext["signals"])

            # Tone trajectory
            st.markdown("**Tone Trajectory:**")
            tones = ext["tones"]
            if tones:
                cols_tone = st.columns(len(tones) * 2 - 1)
                for j, tone in enumerate(tones):
                    with cols_tone[j * 2]:
                        st.markdown(
                            f'<div style="text-align:center; font-size:0.85em;">{tone.title()}</div>',
                            unsafe_allow_html=True,
                        )
                    if j < len(tones) - 1:
                        with cols_tone[j * 2 + 1]:
                            st.markdown(
                                '<div style="text-align:center; color:#999;">→</div>',
                                unsafe_allow_html=True,
                            )
            else:
                st.caption("N/A")

            st.markdown("---")

            # Key observation
            st.markdown("**Key Observation:**")
            st.caption(ext["key_observation"])

            # Expandable raw detail
            if analysis and "_raw" not in analysis:
                per_email = analysis.get("per_email_analysis", [])
                with st.expander("Full detail"):
                    for email in per_email:
                        sender = email.get("from", "Unknown")
                        risk = email.get("risk_level", "N/A")
                        st.markdown(f"**Email {email.get('email_index', '?')} — {sender}** [{risk}]")
                        pi = email.get("pragmatic_inference", {})
                        imp = pi.get("implicature", "")
                        if imp:
                            st.markdown(f"*Implicature:* {imp}")
                        violations = pi.get("gricean_violations", [])
                        if violations:
                            for v in violations:
                                st.markdown(f"- {v.get('maxim', '?')}: {v.get('description', '')}")
                        st.markdown("")
