"""Tab 3 — 🎭 Reply Simulator (Module 6)."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from llm.cache import cached_call_llm
from prompts.simulate import SIMULATE_SYSTEM_PROMPT, format_simulate_user_prompt
from ui.components import gated_call

# ---------------------------------------------------------------------------
# Risk badge helpers
# ---------------------------------------------------------------------------

_RISK_COLORS = {
    "low_risk": "🟢",
    "medium_risk": "🟡",
    "high_risk": "🔴",
}

_RISK_CSS = {
    "low_risk": "color: #28a745; font-weight: bold;",
    "medium_risk": "color: #d39e00; font-weight: bold;",
    "high_risk": "color: #dc3545; font-weight: bold;",
}

_STRATEGY_ICONS = {
    "direct": "⚡",
    "diplomatic": "🤝",
    "strategic_concession": "🎯",
}

# Bump when SIMULATE_SYSTEM_PROMPT or temperature changes — invalidates
# any in-flight session_state entries so a stale result is never shown.
_PROMPT_VERSION = "simulate_v1"


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_strategy_card(strategy: dict, index: int, is_recommended: bool) -> None:
    """Render a single strategy in a column card."""
    name = strategy.get("strategy_name", f"Strategy {index + 1}")
    icon = _STRATEGY_ICONS.get(name, "💬")
    risk = strategy.get("risk_assessment", "medium_risk")
    risk_emoji = _RISK_COLORS.get(risk, "⚪")
    risk_style = _RISK_CSS.get(risk, "")

    # Header with recommendation badge
    header = f"{icon} **{name.replace('_', ' ').title()}**"
    if is_recommended:
        header += " ⭐"

    st.markdown(header, unsafe_allow_html=True)

    # Risk badge
    st.markdown(
        f'<p style="{risk_style}">Risk: {risk_emoji} {risk.replace("_", " ").title()}</p>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Reply draft
    st.markdown("**📝 Reply Draft:**")
    st.markdown(
        f"> {strategy.get('reply_draft', '').replace(chr(10), '  ' + chr(10) + '> ')}"
    )

    st.markdown("")

    # Tone
    tone = strategy.get("tone", "")
    if tone:
        st.caption(f"**Tone:** {tone}")

    # Predicted reaction
    reaction = strategy.get("predicted_reaction", "")
    if reaction:
        st.markdown(f"*💭 Predicted reaction: {reaction}*")

    st.markdown("")

    # Pros
    pros = strategy.get("pros", [])
    if pros:
        st.markdown("**Pros:**")
        for p in pros:
            st.markdown(f"✅ {p}")

    # Cons
    cons = strategy.get("cons", [])
    if cons:
        st.markdown("**Cons:**")
        for c in cons:
            st.markdown(f"⚠️ {c}")


# ---------------------------------------------------------------------------
# Main tab renderer
# ---------------------------------------------------------------------------


def render_simulator_tab(thread_data: dict) -> None:
    """Render the Simulator tab with 3 alternative reply strategies.

    Args:
        thread_data: The full thread dictionary.
    """
    st.subheader("🎭 Reply Simulator")
    st.caption(
        "Generate 3 alternative reply strategies with risk assessment and "
        "pragmatic analysis."
    )

    def _generate() -> dict[str, Any]:
        user_prompt = format_simulate_user_prompt(thread_data)
        raw = cached_call_llm(SIMULATE_SYSTEM_PROMPT, user_prompt, temperature=0.3)
        return json.loads(raw)  # raises JSONDecodeError on bad output — caller sees raw error

    result = gated_call(
        feature="simulator",
        thread_data=thread_data,
        prompt_version=_PROMPT_VERSION,
        model="deepseek-chat",
        button_label="Generate reply strategies",
        placeholder=(
            "Click **Generate reply strategies** to produce 3 alternative "
            "replies with risk assessment and pragmatic analysis."
        ),
        generate_fn=_generate,
    )
    if result is None:
        return

    strategies = result.get("strategies", [])
    if not strategies or len(strategies) < 3:
        st.warning("Expected 3 strategies but got fewer. Showing available results.")

    recommended = result.get("recommended", 0)
    reasoning = result.get("reasoning", "")

    # Render 3 columns
    cols = st.columns(len(strategies))
    for i, (col, strategy) in enumerate(zip(cols, strategies)):
        with col:
            with st.container():
                _render_strategy_card(strategy, i, is_recommended=(i == recommended))

    # Recommendation section
    st.markdown("---")
    if strategies and 0 <= recommended < len(strategies):
        rec_name = strategies[recommended].get("strategy_name", f"Strategy {recommended + 1}")
        rec_icon = _STRATEGY_ICONS.get(rec_name, "⭐")
        st.success(
            f"**{rec_icon} Recommended: {rec_name.replace('_', ' ').title()}**\n\n"
            f"{reasoning}"
        )
    else:
        st.info(f"**Recommendation:** {reasoning}")
