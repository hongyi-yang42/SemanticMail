"""Build evidence-only MEMORY CONTEXT BLOCK for memory-augmented analysis.

IMPORTANT (anti-leakage): This block contains raw evidence ONLY.
- Prior email snippets (dated)
- Objective metadata: # prior emails, timespan in days, # unanswered asks
- Per-email triage tone labels marked as "prior cheap-pass observations"
The deep analysis must DERIVE trajectory/escalation conclusions itself.
"""

import json
import os

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "memory")


def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _days_between(d1: str, d2: str) -> int:
    """Days between two ISO date strings."""
    try:
        from datetime import datetime
        a = datetime.fromisoformat(d1.replace("Z", "+00:00"))
        b = datetime.fromisoformat(d2.replace("Z", "+00:00"))
        return abs((b - a).days)
    except Exception:
        return 0


def build_memory_context_block(
    sender: str,
    email_idx: int,
    date_iso: str,
    contacts: dict | None = None,
    thread_key: str | None = None,
    threads: dict | None = None,
    recalled_emails: list[dict] | None = None,
    triage_results: list[dict] | None = None,
) -> str:
    """Build the MEMORY CONTEXT BLOCK with evidence only.

    Args:
        sender: De-identified sender display name.
        email_idx: Index of current email in the corpus.
        date_iso: ISO date of current email.
        contacts: Pre-loaded contacts dict (or loaded from disk if None).
        thread_key: Normalized subject for thread lookup.
        threads: Pre-loaded threads dict (or loaded from disk if None).
        recalled_emails: Top-k retrieved past emails from embedding index.
        triage_results: Triage results for prior cheap-pass observations.

    Returns:
        Formatted memory context block string.
    """
    if contacts is None:
        contacts = _load_json(os.path.join(MEMORY_DIR, "contacts.json"))
    if threads is None:
        threads = _load_json(os.path.join(MEMORY_DIR, "threads.json"))

    contact = contacts.get(sender, {})
    n_prior = contact.get("n_interactions", 0)
    first_seen = contact.get("first_seen", "")
    timespan = _days_between(first_seen, date_iso) if first_seen else 0
    open_asks = contact.get("open_asks", [])
    # Deduplicate open asks, keep last 5
    seen = set()
    unique_asks = []
    for a in reversed(open_asks):
        if a not in seen:
            seen.add(a)
            unique_asks.append(a)
    unique_asks = unique_asks[:5]

    # Prior cheap-pass tone observations (NOT a trajectory verdict)
    tone_labels = contact.get("tone_labels", [])
    # Show last 8 at most, clearly labeled as cheap-pass observations
    recent_tones = tone_labels[-8:] if len(tone_labels) > 8 else tone_labels

    # Thread state
    thread_info = ""
    if thread_key and thread_key in threads:
        t = threads[thread_key]
        thread_info = (
            f"Thread '{thread_key}': {t.get('n_emails', 0)} emails, "
            f"status {t.get('status', 'unknown')}, "
            f"last activity {t.get('last_date', 'unknown')[:10]}."
        )

    # Build block
    lines = ["--- MEMORY CONTEXT (evidence only — derive conclusions yourself) ---"]
    lines.append(f"Current sender: {sender}")
    lines.append(f"Prior interactions with this sender: {n_prior} emails over {timespan} days.")

    if recent_tones:
        lines.append(
            f"Prior cheap-pass tone observations (per-email triage labels): "
            f"{recent_tones}"
        )

    if unique_asks:
        lines.append(f"Unanswered asks accumulated from this sender: {unique_asks}")

    if thread_info:
        lines.append(thread_info)

    if recalled_emails:
        lines.append(f"Related past emails ({len(recalled_emails)} retrieved by semantic similarity):")
        for re_email in recalled_emails:
            snippet = re_email.get("snippet", "")
            date = re_email.get("date_iso", "unknown")[:10]
            frm = re_email.get("from", "unknown")
            lines.append(f"  [{date}] {frm}: \"{snippet}\"")

    lines.append("--- END MEMORY CONTEXT ---")

    return "\n".join(lines)
