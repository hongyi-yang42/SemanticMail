"""Tab 4 — 📊 Baseline Comparison."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional, TypeVar

import streamlit as st

from llm.cache import LiveCallBlockedError, cached_call_llm, cached_call_baseline_llm
from prompts.draft import (
    DRAFT_SYSTEM_PROMPT,
    format_draft_user_prompt,
    get_inline_subtext_prompt,
)
from prompts.baseline_gptoss import (
    BASELINE_GPTOSS_SYSTEM_PROMPT,
    format_baseline_gptoss_user_prompt,
)
from ui.components import gated_call

# ---------------------------------------------------------------------------
# Try to import the subtext module (may not be available yet if T2 hasn't
# been merged).  If unavailable, we fall back to an inline subtext prompt.
# ---------------------------------------------------------------------------

try:
    from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt  # type: ignore[import-untyped]
    _HAS_SUBTEXT_MODULE = True
except ImportError:
    _HAS_SUBTEXT_MODULE = False

T = TypeVar("T")

# Bump when any of the three system prompts or temperatures changes.
_PROMPT_VERSION = "draft_v1"

# ---------------------------------------------------------------------------
# Hardcoded signal scorecard (per thread)
# ---------------------------------------------------------------------------

SIGNAL_SCORECARD = {
    "Thread A: 师生推荐信": {
        "signals": [
            "Greeting shift: 'Hi Li Wei' → 'Li Wei'",
            "Enthusiasm drop: 'Sure, happy to help!' → 'I will review when I get a chance'",
            "5-day reply gap (Jan 13 → Jan 18)",
            "Loss of warmth markers (exclamation marks, emojis)",
        ],
        "gptoss_baseline": {
            "Greeting shift: 'Hi Li Wei' → 'Li Wei'": False,
            "Enthusiasm drop: 'Sure, happy to help!' → 'I will review when I get a chance'": False,
            "5-day reply gap (Jan 13 → Jan 18)": False,
            "Loss of warmth markers (exclamation marks, emojis)": False,
        },
        "deepseek_naive": {
            "Greeting shift: 'Hi Li Wei' → 'Li Wei'": False,
            "Enthusiasm drop: 'Sure, happy to help!' → 'I will review when I get a chance'": False,
            "5-day reply gap (Jan 13 → Jan 18)": False,
            "Loss of warmth markers (exclamation marks, emojis)": False,
        },
        "semanticmail_smart": {
            "Greeting shift: 'Hi Li Wei' → 'Li Wei'": True,
            "Enthusiasm drop: 'Sure, happy to help!' → 'I will review when I get a chance'": True,
            "5-day reply gap (Jan 13 → Jan 18)": True,
            "Loss of warmth markers (exclamation marks, emojis)": True,
        },
    },
    "Thread B: 实习跟进": {
        "signals": [
            "Timeline vagueness: 'the coming weeks', 'still finalizing'",
            "Indirect refusal: 'encourage you to make the best choice for your career'",
            "Professional politeness masking no intent to hire",
            "Escalation signal: competing offer deadline introduced",
        ],
        "gptoss_baseline": {
            "Timeline vagueness: 'the coming weeks', 'still finalizing'": False,
            "Indirect refusal: 'encourage you to make the best choice for your career'": False,
            "Professional politeness masking no intent to hire": False,
            "Escalation signal: competing offer deadline introduced": False,
        },
        "deepseek_naive": {
            "Timeline vagueness: 'the coming weeks', 'still finalizing'": False,
            "Indirect refusal: 'encourage you to make the best choice for your career'": False,
            "Professional politeness masking no intent to hire": False,
            "Escalation signal: competing offer deadline introduced": False,
        },
        "semanticmail_smart": {
            "Timeline vagueness: 'the coming weeks', 'still finalizing'": True,
            "Indirect refusal: 'encourage you to make the best choice for your career'": True,
            "Professional politeness masking no intent to hire": True,
            "Escalation signal: competing offer deadline introduced": True,
        },
    },
    "Thread C: 跨文化合作": {
        "signals": [
            "Indirect disagreement via deferential suggestion",
            "Code-switching to Chinese for face-saving",
            "Formality gap between participants",
            "Phased proposal as implicit pushback",
        ],
        "gptoss_baseline": {
            "Indirect disagreement via deferential suggestion": False,
            "Code-switching to Chinese for face-saving": False,
            "Formality gap between participants": False,
            "Phased proposal as implicit pushback": False,
        },
        "deepseek_naive": {
            "Indirect disagreement via deferential suggestion": False,
            "Code-switching to Chinese for face-saving": False,
            "Formality gap between participants": False,
            "Phased proposal as implicit pushback": False,
        },
        "semanticmail_smart": {
            "Indirect disagreement via deferential suggestion": True,
            "Code-switching to Chinese for face-saving": True,
            "Formality gap between participants": True,
            "Phased proposal as implicit pushback": True,
        },
    },
}

_BLOCKED_CARD_MSG = (
    "Cached component not available in the public demo for this thread. "
    "Pick Thread A, B, or C in the sidebar, or run locally with "
    "SEMANTICMAIL_RUNTIME=local_dev."
)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_draft_section(
    label: str,
    icon: str,
    draft: dict,
    tag_color: str,
    tag_prefix: str,
    border_color: str,
    bg_color: str,
) -> None:
    """Render a single draft (naive or smart) with styled container."""
    st.markdown(
        f'<div style="border-left: 4px solid {border_color}; '
        f'background-color: {bg_color}; padding: 16px; border-radius: 4px; '
        f'margin-bottom: 8px;">',
        unsafe_allow_html=True,
    )

    st.markdown(f"### {icon} {label}")

    # Approach description
    approach = draft.get("approach_description", "")
    if approach:
        st.caption(approach)

    # Draft text
    draft_text = draft.get("draft_text", "")
    if draft_text:
        st.text_area(
            "Draft",
            value=draft_text,
            height=220,
            disabled=True,
            label_visibility="collapsed",
        )

    # Pragmatic awareness tags
    awareness = draft.get("pragmatic_awareness", [])
    if awareness:
        st.markdown("")
        section_label = "Signals Missed" if tag_prefix == "❌" else "Signals Addressed"
        st.markdown(f"**{section_label}:**")
        tags_html = " ".join(
            f'<span style="background-color: {tag_color}; color: #fff; '
            f'padding: 2px 8px; border-radius: 10px; font-size: 0.8em; '
            f'margin: 2px;">{tag_prefix} {s}</span>'
            for s in awareness
        )
        st.markdown(tags_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_baseline_section(text: str, border_color: str, bg_color: str) -> None:
    """Render the GPT-OSS baseline plain-text reply."""
    st.markdown(
        f'<div style="border-left: 4px solid {border_color}; '
        f'background-color: {bg_color}; padding: 16px; border-radius: 4px; '
        f'margin-bottom: 8px;">',
        unsafe_allow_html=True,
    )
    st.markdown("### 🤖 GPT-OSS Baseline")
    st.caption("Minimal vanilla prompt — no pragmatic instructions")
    if text:
        st.text_area(
            "Baseline",
            value=text,
            height=220,
            disabled=True,
            label_visibility="collapsed",
        )
    else:
        st.warning("No baseline response available.")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_blocked_section(title: str, icon: str) -> None:
    """Render a 'blocked in public demo' card in place of a missing component."""
    st.markdown(
        '<div style="border-left: 4px solid #adb5bd; '
        'background-color: #f8f9fa; padding: 16px; border-radius: 4px; '
        'margin-bottom: 8px;">',
        unsafe_allow_html=True,
    )
    st.markdown(f"### {icon} {title}")
    st.info(_BLOCKED_CARD_MSG)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_scorecard(thread_title: str) -> None:
    """Render the hardcoded signal scorecard for the given thread."""
    data = SIGNAL_SCORECARD.get(thread_title)
    if not data:
        return

    st.markdown("---")
    st.markdown("### 📋 Signal Detection Scorecard")
    st.caption(
        "Which pragmatic signals does each model catch? "
        "✅ = detected/addressed · ❌ = missed"
    )

    signals = data["signals"]
    models = [
        ("GPT-OSS Baseline", "gptoss_baseline"),
        ("DeepSeek Naive", "deepseek_naive"),
        ("SemanticMail Smart", "semanticmail_smart"),
    ]

    # Header row
    cols = st.columns([3, 1, 1, 1])
    cols[0].markdown("**Signal**")
    for i, (model_label, _) in enumerate(models, start=1):
        cols[i].markdown(f"**{model_label}**")

    # One row per signal
    for signal in signals:
        row = st.columns([3, 1, 1, 1])
        row[0].markdown(signal)
        for i, (_, model_key) in enumerate(models, start=1):
            caught = data[model_key].get(signal, False)
            icon = "✅" if caught else "❌"
            row[i].markdown(icon)

    # Summary row
    st.markdown("")
    summary_cols = st.columns([3, 1, 1, 1])
    summary_cols[0].markdown("**Total**")
    for i, (_, model_key) in enumerate(models, start=1):
        total = sum(1 for s in signals if data[model_key].get(s, False))
        summary_cols[i].markdown(f"**{total}/{len(signals)}**")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _try_call(fn: Callable[[], T]) -> Optional[T]:
    """Run fn; return None on LiveCallBlockedError. Other exceptions propagate."""
    try:
        return fn()
    except LiveCallBlockedError:
        return None


def _generate_comparison(thread_data: dict) -> dict[str, Any]:
    """Run baseline + subtext + draft; return a dict of components. Each
    component is None if its individual call was blocked by the runtime."""
    # ---- Column 1: GPT-OSS Baseline ----
    baseline_text: Optional[str] = None
    try:
        baseline_user_prompt = format_baseline_gptoss_user_prompt(thread_data)
        baseline_text = _try_call(
            lambda: cached_call_baseline_llm(
                BASELINE_GPTOSS_SYSTEM_PROMPT, baseline_user_prompt, temperature=0.3
            )
        )
    except Exception:
        baseline_text = None

    # ---- Column 2 & 3 input: Subtext analysis ----
    subtext_analysis: Optional[str] = None
    try:
        if _HAS_SUBTEXT_MODULE:
            subtext_user_prompt = format_subtext_user_prompt(thread_data)
            subtext_analysis = _try_call(
                lambda: cached_call_llm(
                    SUBTEXT_SYSTEM_PROMPT, subtext_user_prompt, temperature=0.3
                )
            )
        else:
            sys_prompt, usr_prompt = get_inline_subtext_prompt(thread_data)
            subtext_analysis = _try_call(
                lambda: cached_call_llm(sys_prompt, usr_prompt, temperature=0.3)
            )
    except Exception:
        subtext_analysis = None

    # ---- Column 2 & 3: Drafts (depends on subtext) ----
    draft_result: Optional[dict] = None
    if subtext_analysis is not None:
        user_prompt = format_draft_user_prompt(thread_data, subtext_analysis)
        raw = _try_call(
            lambda: cached_call_llm(
                DRAFT_SYSTEM_PROMPT, user_prompt, temperature=0.5
            )
        )
        if raw is not None:
            try:
                draft_result = json.loads(raw)
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse draft results: {e}")
                with st.expander("Raw response"):
                    st.text(raw)
                draft_result = None

    return {
        "baseline": baseline_text,
        "subtext": subtext_analysis,
        "draft_result": draft_result,
    }


# ---------------------------------------------------------------------------
# Main tab renderer
# ---------------------------------------------------------------------------


def render_draft_tab(thread_data: dict) -> None:
    """Render the Baseline Comparison tab with 3-column side-by-side.

    Columns: GPT-OSS Baseline | DeepSeek Naive | SemanticMail PIC Smart.
    Each component is rendered independently; a component whose call was
    blocked by the runtime mode renders a placeholder card instead of
    aborting the whole tab.

    Args:
        thread_data: The full thread dictionary.
    """
    st.subheader("📊 Baseline Comparison")
    st.caption(
        "Compare a vanilla GPT-OSS 20B baseline, a DeepSeek naive reply, "
        "and the SemanticMail PIC smart reply side by side."
    )

    result = gated_call(
        feature="baseline_comparison",
        thread_data=thread_data,
        prompt_version=_PROMPT_VERSION,
        model="deepseek-chat",
        button_label="Generate comparison",
        placeholder=(
            "Click **Generate comparison** to produce the 3-way side-by-side: "
            "GPT-OSS baseline, DeepSeek naive, SemanticMail smart."
        ),
        generate_fn=lambda: _generate_comparison(thread_data),
    )
    if result is None:
        return

    baseline_text: Optional[str] = result.get("baseline")
    subtext_analysis: Optional[str] = result.get("subtext")
    draft_result: Optional[dict] = result.get("draft_result") or {}

    naive = draft_result.get("naive_draft", {}) if draft_result else {}
    smart = draft_result.get("smart_draft", {}) if draft_result else {}

    if not baseline_text and not naive and not smart:
        st.warning("No drafts were generated.")
        return

    # Render 3-column side-by-side; each column may show a blocked card
    col_baseline, col_naive, col_smart = st.columns(3)

    with col_baseline:
        if baseline_text:
            _render_baseline_section(
                baseline_text,
                border_color="#6c757d",
                bg_color="#f8f9fa",
            )
        else:
            _render_blocked_section("GPT-OSS Baseline", "🤖")

    with col_naive:
        if naive:
            _render_draft_section(
                label="DeepSeek Naive",
                icon="😐",
                draft=naive,
                tag_color="#dc3545",
                tag_prefix="❌",
                border_color="#adb5bd",
                bg_color="#f8f9fa",
            )
        else:
            _render_blocked_section("DeepSeek Naive", "😐")

    with col_smart:
        if smart:
            _render_draft_section(
                label="SemanticMail Smart",
                icon="🧠",
                draft=smart,
                tag_color="#28a745",
                tag_prefix="✅",
                border_color="#28a745",
                bg_color="#f0fff4",
            )
        else:
            _render_blocked_section("SemanticMail Smart", "🧠")

    # Explanation section — only if we have a smart draft with addressed signals
    if smart:
        thread_title = thread_data.get("title", "")
        st.markdown("---")
        st.markdown("### 💡 Why the Smart Draft is Better")

        naive_missed = naive.get("pragmatic_awareness", []) if naive else []
        smart_addressed = smart.get("pragmatic_awareness", [])

        if smart_addressed:
            st.markdown(
                "The SemanticMail smart draft leverages pragmatic signals that "
                "both the GPT-OSS baseline and DeepSeek naive draft overlook:"
            )
            for signal in smart_addressed:
                st.markdown(f"- ✅ **{signal}**")

        if naive_missed:
            with st.expander("See what the naive draft missed"):
                for signal in naive_missed:
                    st.markdown(f"- ❌ {signal}")

        # Signal scorecard
        _render_scorecard(thread_title)
