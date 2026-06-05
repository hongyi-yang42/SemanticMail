"""Inbox Simulator — sit down as Jeff Dasovich and watch the agent think.

Layout: header + 2-column (inbox list | email detail + agent panels).
Phase 2 adds: receive-next-email + memory recall graph.
Phase 3 adds: draft review + critique + rewrite.
"""

import json
import os
import sys

import streamlit as st
import pandas as pd

_AGENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

MEMORY_DIR = os.path.join(_AGENT_DIR, "memory")

RISK_COLORS = {
    "safe": "#28a745", "caution": "#ffc107",
    "warning": "#fd7e14", "critical": "#dc3545",
}
RISK_LABELS = {"safe": "OK", "caution": "!", "warning": "!!", "critical": "!!!"}


def _load_json(fname):
    path = os.path.join(MEMORY_DIR, fname)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _risk_badge_html(risk_level):
    color = RISK_COLORS.get(risk_level, "#999")
    label = RISK_LABELS.get(risk_level, "?")
    return (
        f'<span style="background:{color};color:#fff;padding:1px 6px;'
        f'border-radius:3px;font-size:0.75em;font-weight:bold">{label}</span>'
    )


def _init_state(emails):
    if "inbox_cursor" not in st.session_state:
        st.session_state.inbox_cursor = max(0, len(emails) - 20)
    if "selected_idx" not in st.session_state:
        st.session_state.selected_idx = len(emails) - 1
    if "user_draft" not in st.session_state:
        st.session_state.user_draft = ""
    if "critique" not in st.session_state:
        st.session_state.critique = None
    if "_prev_selected" not in st.session_state:
        st.session_state._prev_selected = st.session_state.selected_idx
    # Reset draft + critique when switching emails
    if st.session_state.selected_idx != st.session_state._prev_selected:
        st.session_state.user_draft = ""
        st.session_state.critique = None
        st.session_state._prev_selected = st.session_state.selected_idx


# ---------------------------------------------------------------------------
# Left pane: scrollable inbox
# ---------------------------------------------------------------------------

def _render_inbox_list(emails, triage_map, selected_idx):
    """Render inbox rows. Returns new selected_idx if user clicks."""
    st.markdown(
        '<div style="max-height:75vh;overflow-y:auto;padding-right:4px">',
        unsafe_allow_html=True,
    )
    for i in range(st.session_state.inbox_cursor, len(emails)):
        e = emails[i]
        t = triage_map.get(i, {})
        risk = t.get("risk_level", "safe")
        bg = "#e8f4fd" if i == selected_idx else "#fff"
        border = "2px solid #4a90d9" if i == selected_idx else "1px solid #e0e0e0"
        if i == st.session_state.get("_new_email_idx"):
            border = "2px solid #2196F3"
            bg = "#e3f2fd"

        sender = e.get("from", "?")[:22]
        subject = (e.get("subject", "(no subject)") or "(no subject)")[:32]
        date = e.get("date_iso", "")[:10]
        badge = _risk_badge_html(risk)

        if st.button(
            f"**{sender}** — {subject}",
            key=f"email_{i}",
            use_container_width=True,
        ):
            st.session_state.selected_idx = i

        # Inline style for selected row
        st.markdown(
            f'<div style="margin-top:-8px;margin-bottom:2px;font-size:0.8em;'
            f'padding-left:8px;color:#666">{date} {badge} {sender}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Right pane: email detail + agent analysis
# ---------------------------------------------------------------------------

def _render_email_detail(email_dict, triage, cache_entry):
    sender = email_dict.get("from", "Unknown")
    subject = email_dict.get("subject", "(no subject)")
    date = email_dict.get("date", "")
    risk = triage.get("risk_level", "safe")
    badge = _risk_badge_html(risk)

    st.markdown(
        f'<div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;'
        f'background:#fafafa;margin-bottom:12px">'
        f'<h3 style="margin:0">{badge} {subject}</h3>'
        f'<p style="color:#666;margin:4px 0"><b>From:</b> {sender} &nbsp;|&nbsp; '
        f'<b>Date:</b> {date}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Email body
    body = email_dict.get("body", "")
    st.text_area("Email Body", body, height=180, disabled=True, label_visibility="collapsed")


def _render_triage_panel(triage):
    with st.expander("Triage Labels", expanded=True):
        if not triage or triage.get("intent") == "not analyzed (offline)":
            st.info("Triage not available for this email.")
            return

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Intent", triage.get("intent", "—"))
        c2.metric("Urgency", triage.get("urgency", "—"))
        risk = triage.get("risk_level", "safe")
        c3.metric("Risk", risk)
        c4.metric("Tone", triage.get("tone_label", "—"))

        signals = triage.get("key_signals", [])
        if signals:
            st.markdown("**Key Signals:** " + ", ".join(f"`{s}`" for s in signals))

        asks = triage.get("open_asks", [])
        if asks:
            st.markdown("**Open Asks:** " + ", ".join(f"`{a}`" for a in asks))


def _render_pic_panel(pic):
    with st.expander("4-Layer PIC Analysis", expanded=False):
        if not pic:
            st.info("PIC analysis not cached for this email.")
            return

        per_email = pic.get("per_email_analysis", [])
        for j, analysis in enumerate(per_email):
            sender = analysis.get("from", f"Email {j+1}")
            risk = analysis.get("risk_level", "safe")
            st.markdown(f"#### {sender} {_risk_badge_html(risk)}", unsafe_allow_html=True)

            st.markdown(f"**Literal:** {analysis.get('literal_content', '—')}")

            inf = analysis.get("pragmatic_inference", {})
            if isinstance(inf, dict):
                violations = inf.get("gricean_violations", [])
                indirect = inf.get("indirect_speech_acts", [])
                if violations:
                    st.markdown("**Gricean Violations:**")
                    for v in violations:
                        st.markdown(f"- {v}")
                if indirect:
                    st.markdown("**Indirect Speech Acts:**")
                    for a in indirect:
                        st.markdown(f"- {a}")

            social = analysis.get("social_dynamics", {})
            if isinstance(social, dict):
                face = social.get("face_threats", [])
                power = social.get("power_dynamics", "")
                if face:
                    st.markdown("**Face Threats:**")
                    for f in face:
                        st.markdown(f"- {f}")
                if power:
                    st.markdown(f"**Power Dynamics:** {power}")

            st.markdown(f"**Risk Level:** {risk}")
            if j < len(per_email) - 1:
                st.divider()

        # Thread-level
        thread = pic.get("thread_level", {})
        if thread:
            st.markdown("#### Thread-Level Analysis")
            st.markdown(f"**Tone Trajectory:** {thread.get('tone_trajectory', '—')}")
            st.markdown(f"**Overall Risk:** {thread.get('overall_risk', '—')}")
            st.markdown(f"**Recommended Strategy:** {thread.get('recommended_strategy', '—')}")


def _render_drafts_panel(cold, scaffolded):
    with st.expander("Reply Drafts", expanded=False):
        if not cold and not scaffolded:
            st.info("Draft not cached for this email.")
            return

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Cold Draft** (no PIC context)")
            if cold:
                st.text(cold.get("draft_text", "—"))
                st.caption(cold.get("rationale", ""))
            else:
                st.info("Not cached")

        with c2:
            st.markdown("**Scaffolded Draft** (PIC + memory context)")
            if scaffolded:
                st.text(scaffolded.get("draft_text", "—"))
                st.caption(scaffolded.get("rationale", ""))
            else:
                st.info("Not cached")


# ---------------------------------------------------------------------------
# Phase 2: Memory recall graph
# ---------------------------------------------------------------------------

def _render_memory_recall(cache_entry, emails):
    with st.expander("Memory Recall — Similar Past Emails", expanded=False):
        recalled = cache_entry.get("recalled", []) if cache_entry else []
        if not recalled:
            st.info("No recalled emails for this message.")
            return

        # Similarity graph as HTML (no graphviz dependency)
        current_subject = emails[st.session_state.selected_idx].get("subject", "Current")[:30]
        nodes_html = (
            f'<div style="text-align:center;margin-bottom:12px">'
            f'<span style="background:#2196F3;color:#fff;padding:4px 12px;'
            f'border-radius:12px;font-size:0.85em">Current: {current_subject}</span>'
        )
        for j, r in enumerate(recalled):
            score = r.get("score", 0)
            pct = f"{score:.0%}"
            short_from = r.get("from", "?")[:15]
            nodes_html += (
                f' <span style="color:#666">→</span> '
                f'<span style="background:#e0e0e0;padding:4px 12px;'
                f'border-radius:12px;font-size:0.85em">{short_from} ({pct})</span>'
            )
        nodes_html += "</div>"
        st.markdown(nodes_html, unsafe_allow_html=True)

        # Show recalled emails as cards
        for r in recalled:
            score = r.get("score", 0)
            pct = f"{score:.2f}"
            st.markdown(
                f'<div style="border:1px solid #ddd;border-radius:6px;padding:8px;'
                f'margin-bottom:6px;background:#f8f9fa">'
                f'<b>{r.get("from","?")}</b> ({r.get("date_iso","?")[:10]}) '
                f'— similarity: <code>{pct}</code><br>'
                f'<span style="color:#666;font-size:0.9em">{r.get("snippet","")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            # Button to jump to this email
            idx = r.get("idx", -1)
            if idx >= 0 and idx < len(emails):
                if st.button(f"Jump to email #{idx}", key=f"jump_{idx}"):
                    st.session_state.selected_idx = idx

        # Memory context block
        memory_block = cache_entry.get("memory_block", "") if cache_entry else ""
        if memory_block:
            with st.expander("Memory Context Block (injected into PIC)"):
                st.text(memory_block)


# ---------------------------------------------------------------------------
# Phase 2: Receive next email
# ---------------------------------------------------------------------------

def _render_receive_next(emails):
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    with c1:
        remaining = len(emails) - st.session_state.inbox_cursor
        st.caption(f"Showing {remaining} of {len(emails)} emails (cursor: {st.session_state.inbox_cursor})")
    with c2:
        if st.button("📥 Receive Next Email", use_container_width=True, type="primary"):
            if st.session_state.inbox_cursor > 0:
                st.session_state.inbox_cursor -= 1
                st.session_state._new_email_idx = st.session_state.inbox_cursor
                st.session_state.selected_idx = st.session_state.inbox_cursor
                st.rerun()


# ---------------------------------------------------------------------------
# Phase 3: Draft + critique + rewrite
# ---------------------------------------------------------------------------

def _render_draft_critique(email_dict, triage, pic, cache_entry, live):
    with st.expander("Draft Your Reply + Agent Critique", expanded=False):
        if not pic:
            st.info("PIC analysis required for critique. Not cached for this email.")
            return

        # User draft textarea
        st.markdown(f"**Write your reply as Jeff Dasovich to {email_dict.get('from','?')}:**")
        draft = st.text_area(
            "Your draft",
            value=st.session_state.user_draft,
            height=150,
            key="draft_input",
            label_visibility="collapsed",
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Ask Agent to Review My Draft", type="primary", use_container_width=True):
                if not draft.strip():
                    st.warning("Please write a draft first.")
                else:
                    critique = _run_draft_review(email_dict, triage, pic, cache_entry, draft, live)
                    st.session_state.critique = critique
                    st.session_state.user_draft = draft

        with c2:
            if st.button("Rewrite to Meet PIC Requirements", use_container_width=True):
                if not draft.strip():
                    st.warning("Please write a draft first.")
                else:
                    rewritten = _run_rewrite(email_dict, triage, pic, cache_entry, draft, live)
                    if rewritten:
                        st.session_state.user_draft = rewritten

        # Show critique results
        critique = st.session_state.get("critique")
        if critique:
            _render_critique_results(critique)


def _render_critique_results(critique):
    st.markdown("#### Agent Critique")

    # Coverage checks
    coverage = critique.get("coverage", {})
    if coverage:
        st.markdown("**Open Asks Coverage:**")
        for ask, covered in coverage.items():
            icon = "✅" if covered else "❌"
            st.markdown(f"{icon} `{ask}`")

    # Tone match
    tone = critique.get("tone_match", None)
    if tone is not None:
        st.metric("Tone Match", f"{tone:.0%}")

    # Face threats handled
    face = critique.get("face_threats_handled", [])
    if face:
        st.markdown("**Face Threats Handled:**")
        for f in face:
            st.markdown(f"- {f}")

    # Missing elements
    missing = critique.get("missing_elements", [])
    if missing:
        st.markdown("**Missing Elements:**")
        for m in missing:
            st.markdown(f"- ⚠️ {m}")

    # Suggestions
    suggestions = critique.get("suggestions", [])
    if suggestions:
        st.markdown("**Suggestions:**")
        for s in suggestions:
            st.markdown(f"- 💡 {s}")


# ---------------------------------------------------------------------------
# LLM calls for Phase 3
# ---------------------------------------------------------------------------

REVIEW_SYSTEM_PROMPT = """\
You are a pragmatic email review agent. Given:
1. The original incoming email
2. The PIC (Pragmatic Inference Chain) analysis
3. The user's draft reply

Produce a critique JSON:
{
  "coverage": {"<open_ask>": true/false, ...},
  "tone_match": 0.0-1.0,
  "face_threats_handled": ["<which face threats the draft addresses>"],
  "missing_elements": ["<what's missing>"],
  "suggestions": ["<specific improvement suggestions>"]
}

Evaluate:
- Does the draft address each open_ask from triage?
- Does the tone match the recommended_strategy from PIC?
- Does it handle the face threats identified in PIC?
- What's missing or could be improved?

Respond with ONLY valid JSON."""


REWRITE_SYSTEM_PROMPT = """\
You are a pragmatic email rewrite agent. Given:
1. The original incoming email
2. The PIC analysis with recommended_strategy
3. The user's draft reply
4. The critique

Rewrite the draft to fully meet PIC requirements while preserving the user's intent.
Output ONLY the rewritten email text (no JSON, no markdown)."""


def _run_draft_review(email_dict, triage, pic, cache_entry, user_draft, live):
    from llm.cache import cached_call_llm

    open_asks = triage.get("open_asks", [])
    recommended = ""
    if pic and "thread_level" in pic:
        recommended = pic["thread_level"].get("recommended_strategy", "")

    user_prompt = (
        f"## Incoming Email\n"
        f"From: {email_dict.get('from','?')}\n"
        f"Subject: {email_dict.get('subject','?')}\n"
        f"Body: {email_dict.get('body','')[:500]}\n\n"
        f"## Open Asks\n{json.dumps(open_asks)}\n\n"
        f"## PIC Recommended Strategy\n{recommended}\n\n"
        f"## User's Draft Reply\n{user_draft}\n"
    )

    raw = cached_call_llm(REVIEW_SYSTEM_PROMPT, user_prompt)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"suggestions": [raw[:200]], "missing_elements": [], "coverage": {}, "tone_match": 0.5, "face_threats_handled": []}
    return {"missing_elements": ["LLM unavailable — critique not generated"], "coverage": {}, "tone_match": 0, "face_threats_handled": [], "suggestions": []}


def _run_rewrite(email_dict, triage, pic, cache_entry, user_draft, live):
    from llm.cache import cached_call_llm

    recommended = ""
    if pic and "thread_level" in pic:
        recommended = pic["thread_level"].get("recommended_strategy", "")

    user_prompt = (
        f"## Incoming Email\n"
        f"From: {email_dict.get('from','?')}\n"
        f"Subject: {email_dict.get('subject','?')}\n"
        f"Body: {email_dict.get('body','')[:500]}\n\n"
        f"## PIC Recommended Strategy\n{recommended}\n\n"
        f"## User's Draft\n{user_draft}\n"
    )

    raw = cached_call_llm(REWRITE_SYSTEM_PROMPT, user_prompt)
    return raw if raw else None


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_inbox_simulator():
    emails = _load_json("emails.json")
    triage_results = _load_json("triage_results.json")
    sim_cache = _load_json("simulator_cache.json") or {}

    if not emails:
        st.warning("No emails loaded. Run the agent pipeline first.")
        return

    _init_state(emails)

    # Build triage lookup
    triage_map = {}
    if triage_results:
        for t in triage_results:
            idx = t.get("_email_idx")
            if idx is not None:
                triage_map[idx] = t

    # Header
    st.markdown(
        '<div style="background:linear-gradient(90deg,#1a1a2e,#16213e);'
        f'color:#fff;padding:12px 20px;border-radius:8px;margin-bottom:12px">'
        f'<b>Enron Dataset</b> &middot; dasovich-j inbox &middot; '
        f'<b>{len(emails)}</b> emails through 2001-12-14 &middot; '
        f'viewing as <b>Jeff Dasovich</b></div>',
        unsafe_allow_html=True,
    )

    # Receive next email button
    _render_receive_next(emails)

    selected = st.session_state.selected_idx
    email_dict = emails[selected]
    triage = triage_map.get(selected, {})
    cache_entry = sim_cache.get(str(selected), {})

    # 2-column layout
    col_list, col_detail = st.columns([2, 5])

    with col_list:
        st.markdown("### Inbox")
        _render_inbox_list(emails, triage_map, selected)

    with col_detail:
        _render_email_detail(email_dict, triage, cache_entry)

        # Agent panels
        pic = cache_entry.get("pic")
        cold = cache_entry.get("cold_draft")
        scaffolded = cache_entry.get("scaffolded_draft")

        _render_triage_panel(triage)
        _render_pic_panel(pic)
        _render_memory_recall(cache_entry, emails)
        _render_drafts_panel(cold, scaffolded)
        _render_draft_critique(email_dict, triage, pic, cache_entry, live=True)
