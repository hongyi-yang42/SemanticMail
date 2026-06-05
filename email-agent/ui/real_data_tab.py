"""Real Data dashboard — shows stats from email-agent/memory/."""

import json
import os
import glob

import streamlit as st
import pandas as pd

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "memory")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "out")

RISK_COLORS = {
    "safe": "#28a745",
    "caution": "#ffc107",
    "warning": "#fd7e14",
    "critical": "#dc3545",
}


def _load_json(fname):
    path = os.path.join(MEMORY_DIR, fname)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _load_index_pkl():
    import pickle
    path = os.path.join(MEMORY_DIR, "index.pkl")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def _html_bar(label, value, max_val, color="#4a90d9", height=22):
    """Render a single horizontal bar as HTML."""
    pct = int(value / max_val * 100) if max_val else 0
    return (
        f'<div style="margin-bottom:6px">'
        f'<span style="font-size:0.85em;width:160px;display:inline-block">{label}</span>'
        f'<span style="display:inline-block;width:{pct}%;min-width:2px;height:{height}px;'
        f'background:{color};border-radius:3px;vertical-align:middle"></span>'
        f' <span style="font-size:0.8em;color:#666">{value}</span>'
        f"</div>"
    )


def _render_dataset_overview(emails, contacts, threads, ledger):
    st.subheader("Dataset Overview")

    total_obligations = 0
    if ledger and "counts" in ledger:
        total_obligations = ledger["counts"].get("total", 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Emails Processed", len(emails) if emails else 0)
    c2.metric("Contacts Profiled", len(contacts) if contacts else 0)
    c3.metric("Threads Tracked", len(threads) if threads else 0)
    c4.metric("Obligations Extracted", total_obligations)


def _render_contact_hall(contacts):
    st.subheader("Contact Hall of Fame")

    if not contacts:
        st.info("No contact data available.")
        return

    rows = []
    for name, info in contacts.items():
        n = info.get("n_interactions", 0)
        risks = info.get("risk_history", [])
        dominant = max(set(risks), key=risks.count) if risks else "safe"
        last = info.get("last_seen", "—")
        rows.append({
            "Contact": name,
            "Emails": n,
            "Dominant Risk": dominant,
            "Last Seen": last[:10] if last != "—" else "—",
        })

    rows.sort(key=lambda r: r["Emails"], reverse=True)
    top = rows[:10]

    # Table
    st.dataframe(pd.DataFrame(top), use_container_width=True, hide_index=True)

    # Pure-HTML bar chart
    max_val = top[0]["Emails"] if top else 1
    html = ""
    for r in top:
        color = RISK_COLORS.get(r["Dominant Risk"], "#4a90d9")
        html += _html_bar(r["Contact"], r["Emails"], max_val, color)
    st.markdown(f'<div style="margin-top:8px">{html}</div>', unsafe_allow_html=True)


def _render_obligation_ledger(ledger):
    st.subheader("Obligation Ledger Breakdown")

    if not ledger or "counts" not in ledger:
        st.info("No obligation data available.")
        return

    counts = ledger["counts"]
    you_owe_open = counts.get("you_owe_open", 0)
    you_promised_open = counts.get("you_promised_open", 0)
    resolved = counts.get("resolved", 0)

    c1, c2, c3 = st.columns(3)
    c1.metric("You Owe (open)", you_owe_open)
    c2.metric("You Promised (open)", you_promised_open)
    c3.metric("Resolved", resolved)

    # Pure-HTML bar chart
    total = max(you_owe_open + you_promised_open + resolved, 1)
    html = ""
    for label, val, color in [
        ("You Owe", you_owe_open, "#dc3545"),
        ("You Promised", you_promised_open, "#fd7e14"),
        ("Resolved", resolved, "#28a745"),
    ]:
        html += _html_bar(label, val, total, color, height=28)
    st.markdown(f'<div style="margin-top:12px">{html}</div>', unsafe_allow_html=True)

    # Open obligations table
    open_items = []
    for key in ("you_owe", "you_promised"):
        for item in ledger.get(key, []):
            if item.get("status") == "open":
                open_items.append(item)
    open_items.sort(key=lambda x: x.get("importance", 0), reverse=True)

    if open_items:
        st.markdown("**Top 10 Open Obligations (by importance)**")
        display = []
        for item in open_items[:10]:
            display.append({
                "Obligation": item.get("canonical_ask", "—"),
                "Direction": item.get("direction", "—"),
                "Contact": item.get("contact", "—"),
                "Age (days)": item.get("age_days", "—"),
                "Importance": item.get("importance", "—"),
            })
        st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)


def _render_triage_distribution(triage):
    st.subheader("Triage Distribution")

    if not triage:
        st.info("No triage data available.")
        return

    from collections import Counter

    risks = Counter(t.get("risk_level", "?") for t in triage)
    intents = Counter(t.get("intent", "?") for t in triage)
    urgencies = Counter(t.get("urgency", "?") for t in triage)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Risk Levels**")
        total = sum(risks.values())
        html = ""
        for label in ["safe", "caution", "warning", "critical"]:
            val = risks.get(label, 0)
            color = RISK_COLORS.get(label, "#999")
            html += _html_bar(label, val, total, color)
        st.markdown(html, unsafe_allow_html=True)

    with c2:
        st.markdown("**Urgency**")
        total = sum(urgencies.values())
        html = ""
        for label, color in [("high", "#dc3545"), ("medium", "#ffc107"), ("low", "#28a745")]:
            val = urgencies.get(label, 0)
            html += _html_bar(label, val, total, color)
        st.markdown(html, unsafe_allow_html=True)

    with c3:
        st.markdown("**Top Intents**")
        total = sum(intents.values())
        top_intents = intents.most_common(6)
        html = ""
        for label, val in top_intents:
            html += _html_bar(label, val, total, "#4a90d9")
        st.markdown(html, unsafe_allow_html=True)


def _render_pipeline_report():
    st.subheader("Sample Pipeline Report")

    if not os.path.isdir(OUT_DIR):
        st.info("Run `python3 run_agent.py --live --text` to generate a real report.")
        return

    md_files = sorted(
        glob.glob(os.path.join(OUT_DIR, "*.md")),
        key=os.path.getmtime,
        reverse=True,
    )

    if not md_files:
        st.info("Run `python3 run_agent.py --live --text` to generate a real report.")
        return

    with st.expander(f"Latest Report ({os.path.basename(md_files[0])})", expanded=False):
        with open(md_files[0]) as f:
            st.markdown(f.read())


def _render_memory_growth():
    st.subheader("Memory Growth")

    index = _load_index_pkl()
    if index is None:
        st.info("Memory index not built yet.")
        return

    vectors = index["vectors"]
    model = index.get("model_name", "unknown")
    st.metric("Vector Index", f"{vectors.shape[0]:,} emails x {vectors.shape[1]} dims")
    st.caption(f"Embedding model: {model}")


def render_real_data_dashboard():
    """Render the full Real Data dashboard."""

    emails = _load_json("emails.json")
    contacts = _load_json("contacts.json")
    threads = _load_json("threads.json")
    ledger = _load_json("ledger.json")
    triage = _load_json("triage_results.json")

    if not any([emails, contacts, threads, ledger]):
        st.warning("Memory not loaded yet. Run the agent pipeline first.")
        return

    _render_dataset_overview(emails, contacts, threads, ledger)
    st.divider()
    _render_contact_hall(contacts)
    st.divider()
    _render_obligation_ledger(ledger)
    st.divider()
    _render_triage_distribution(triage)
    st.divider()
    _render_pipeline_report()
    st.divider()
    _render_memory_growth()
