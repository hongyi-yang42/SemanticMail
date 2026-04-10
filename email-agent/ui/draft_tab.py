"""Tab 4 — ✍️ Context-Aware Reply Drafter (Module 4)."""

from __future__ import annotations

import json

import streamlit as st

from llm.cache import cached_call_llm
from prompts.draft import (
    DRAFT_SYSTEM_PROMPT,
    format_draft_user_prompt,
    get_inline_subtext_prompt,
)

# ---------------------------------------------------------------------------
# Try to import the subtext module (may not be available yet if T2 hasn't
# been merged).  If unavailable, we fall back to an inline subtext prompt.
# ---------------------------------------------------------------------------

try:
    from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt  # type: ignore[import-untyped]
    _HAS_SUBTEXT_MODULE = True
except ImportError:
    _HAS_SUBTEXT_MODULE = False


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


# ---------------------------------------------------------------------------
# Main tab renderer
# ---------------------------------------------------------------------------


def render_draft_tab(thread_data: dict) -> None:
    """Render the Draft Reply tab with side-by-side naive vs. smart drafts.

    Args:
        thread_data: The full thread dictionary.
    """
    st.subheader("✍️ Context-Aware Reply Drafter")
    st.caption(
        "Compare a naive reply (literal content only) vs. a smart reply "
        "(accounts for pragmatic signals)."
    )

    # Step 1: Obtain subtext analysis (optional)
    subtext_analysis = ""
    try:
        if _HAS_SUBTEXT_MODULE:
            subtext_user_prompt = format_subtext_user_prompt(thread_data)
            subtext_analysis = cached_call_llm(
                SUBTEXT_SYSTEM_PROMPT, subtext_user_prompt, temperature=0.3
            )
        else:
            sys_prompt, usr_prompt = get_inline_subtext_prompt(thread_data)
            subtext_analysis = cached_call_llm(
                sys_prompt, usr_prompt, temperature=0.3
            )
    except Exception:
        # If subtext analysis fails, proceed without it
        subtext_analysis = ""

    # Step 2: Generate drafts
    user_prompt = format_draft_user_prompt(thread_data, subtext_analysis)

    with st.spinner("Generating naive & smart drafts..."):
        try:
            raw = cached_call_llm(
                DRAFT_SYSTEM_PROMPT, user_prompt, temperature=0.5
            )
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse draft results: {e}")
            with st.expander("Raw response"):
                st.text(raw if "raw" in dir() else "No response")
            return
        except Exception as e:
            st.error(f"Error generating drafts: {e}")
            return

    naive = result.get("naive_draft", {})
    smart = result.get("smart_draft", {})

    if not naive and not smart:
        st.warning("No drafts were generated.")
        return

    # Render side-by-side
    col_naive, col_smart = st.columns(2)

    with col_naive:
        _render_draft_section(
            label="Naive Draft",
            icon="😐",
            draft=naive,
            tag_color="#dc3545",
            tag_prefix="❌",
            border_color="#adb5bd",
            bg_color="#f8f9fa",
        )

    with col_smart:
        _render_draft_section(
            label="Smart Draft",
            icon="🧠",
            draft=smart,
            tag_color="#28a745",
            tag_prefix="✅",
            border_color="#28a745",
            bg_color="#f0fff4",
        )

    # Explanation section
    st.markdown("---")
    st.markdown("### 💡 Why the Smart Draft is Better")

    naive_missed = naive.get("pragmatic_awareness", [])
    smart_addressed = smart.get("pragmatic_awareness", [])

    if smart_addressed:
        st.markdown(
            "The smart draft leverages pragmatic signals that the naive draft overlooks:"
        )
        for signal in smart_addressed:
            st.markdown(f"- ✅ **{signal}**")

    if naive_missed:
        with st.expander("See what the naive draft missed"):
            for signal in naive_missed:
                st.markdown(f"- ❌ {signal}")
