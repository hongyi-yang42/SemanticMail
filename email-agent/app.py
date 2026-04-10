"""SemanticMail — Pragmatic Email Analysis Tool."""

import streamlit as st

from data.threads import get_thread_display_names, get_thread_by_name
from ui.overview_tab import render_overview_tab
from ui.subtext_tab import render_subtext_tab
from ui.simulator_tab import render_simulator_tab
from ui.draft_tab import render_draft_tab
from ui.styles import inject_styles

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SemanticMail",
    page_icon="📧",
    layout="wide",
)

inject_styles()

# ---------------------------------------------------------------------------
# Sidebar: thread selector
# ---------------------------------------------------------------------------
st.sidebar.title("SemanticMail")
st.sidebar.caption("Pragmatic Email Analysis")

thread_names = get_thread_display_names()
selected_thread_name = st.sidebar.selectbox("Select a thread", thread_names)
thread_data = get_thread_by_name(selected_thread_name)

st.sidebar.divider()
st.sidebar.markdown("### About")
st.sidebar.info(
    "SemanticMail analyzes email threads for pragmatic signals, "
    "power dynamics, and cross-cultural communication patterns."
)

# ---------------------------------------------------------------------------
# Main area: tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Overview",
    "🔍 Subtext",
    "🎮 Simulator",
    "✍️ Draft",
])

with tab1:
    render_overview_tab(thread_data)

with tab2:
    render_subtext_tab(thread_data)

with tab3:
    render_simulator_tab(thread_data)

with tab4:
    render_draft_tab(thread_data)
