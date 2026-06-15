"""SemanticMail — Pragmatic Email Analysis Tool."""

import streamlit as st

from data.threads import get_thread_display_names, get_thread_by_name, build_thread_from_raw
from ui.overview_tab import render_overview_tab
from ui.subtext_tab import render_subtext_tab
from ui.simulator_tab import render_simulator_tab
from ui.draft_tab import render_draft_tab
from ui.ablation_tab import render_ablation_tab
from ui.real_data_tab import render_real_data_dashboard
from ui.inbox_simulator import render_inbox_simulator
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
# Sidebar: mode toggle (top)
# ---------------------------------------------------------------------------
app_mode = st.sidebar.radio(
    "Mode",
    ["🎭 Demo Mode", "📬 Inbox Simulator (400 Enron)", "📊 Real Data Dashboard"],
    index=0,
    label_visibility="collapsed",
)

# ---------------------------------------------------------------------------
# Inbox Simulator Mode
# ---------------------------------------------------------------------------
if app_mode == "📬 Inbox Simulator (400 Enron)":
    st.sidebar.title("SemanticMail")
    st.sidebar.caption("Inbox Simulator")
    st.sidebar.divider()
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "Sit down as Jeff Dasovich. Browse 400 Enron emails, "
        "watch the agent triage, analyze pragmatics, recall memory, "
        "and help you draft replies."
    )
    render_inbox_simulator()

# ---------------------------------------------------------------------------
# Real Data Dashboard Mode
# ---------------------------------------------------------------------------
elif app_mode == "📊 Real Data Dashboard":
    st.sidebar.title("SemanticMail")
    st.sidebar.caption("Real Data Dashboard")
    st.sidebar.divider()
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "Dashboard showing pipeline output from processed email data "
        "(contacts, obligations, threads, and triage results)."
    )
    render_real_data_dashboard()

# ---------------------------------------------------------------------------
# Demo Mode (default)
# ---------------------------------------------------------------------------
else:
    st.sidebar.title("SemanticMail")
    st.sidebar.caption("Pragmatic Email Analysis")

    PASTE_OPTION = "✍️ Paste your own email..."
    thread_names = get_thread_display_names() + [PASTE_OPTION]
    selected_thread_name = st.sidebar.selectbox("Select a thread", thread_names)

    if selected_thread_name == PASTE_OPTION:
        raw_email = st.sidebar.text_area(
            "Paste raw email (with headers)",
            height=220,
            key="paste_email_input",
            help=(
                "Paste an email in RFC 822 / .eml format: From/To/Subject/Date "
                "headers, then a blank line, then the body. Loose body-only "
                "paste is also accepted."
            ),
        )
        if raw_email and raw_email.strip():
            thread_data = build_thread_from_raw(raw_email)
        else:
            st.info(
                "📎 Paste an email in the sidebar to begin ad-hoc pragmatic analysis. "
                "The PIC chain will derive signals from the message content."
            )
            st.stop()
    else:
        thread_data = get_thread_by_name(selected_thread_name)

    st.sidebar.divider()
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "SemanticMail analyzes email threads for pragmatic signals, "
        "power dynamics, and cross-cultural communication patterns."
    )

    # -------------------------------------------------------------------
    # Main area: tabs
    # -------------------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Overview",
        "🔍 Subtext",
        "🎮 Simulator",
        "📊 Baseline Comparison",
        "⚖️ Ablation",
    ])

    with tab1:
        render_overview_tab(thread_data)

    with tab2:
        render_subtext_tab(thread_data)

    with tab3:
        render_simulator_tab(thread_data)

    with tab4:
        render_draft_tab(thread_data)

    with tab5:
        render_ablation_tab(thread_data)
