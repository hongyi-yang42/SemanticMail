"""Memory-augmented deep PIC analysis on ~20 flagged emails.

Usage:
    cd email-agent
    python deep_analysis.py

Selects emails with risk >= caution, prioritizing cooling tone trajectories.
For each: retrieves top-3 related past emails, builds evidence-only memory context
block, prepends to user prompt, runs SUBTEXT_SYSTEM_PROMPT via cached_call_llm().
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from llm.cache import cached_call_llm
from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt
from prompts.memory_context import build_memory_context_block

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
RISK_ORDER = {"safe": 0, "caution": 1, "warning": 2, "critical": 3}
DEEP_LIMIT = 20


def load_json(path: str) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_flagged(emails: list[dict], triage: list[dict], n: int = DEEP_LIMIT) -> list[dict]:
    """Select up to n emails with risk >= caution.

    Prioritize:
    1. Contacts with cooling tone trajectories (warning/critical)
    2. Then caution emails from high-interaction senders
    """
    flagged = []
    for i, t in enumerate(triage):
        risk = t.get("risk_level", "safe")
        if RISK_ORDER.get(risk, 0) >= 1:  # caution or above
            flagged.append((i, RISK_ORDER.get(risk, 0), t))

    # Sort by risk level descending, then by index (chronological)
    flagged.sort(key=lambda x: (-x[1], x[0]))

    # Take top n
    return [{"idx": idx, "risk": risk, "triage": t} for idx, risk, t in flagged[:n]]


def build_mini_thread(email: dict, emails: list[dict], triage: list[dict]) -> dict:
    """Build a thread-like dict from a single email for format_subtext_user_prompt.

    Looks up other emails with same norm_subject to form a mini-thread.
    """
    norm_subj = email.get("norm_subject", "")
    thread_emails = []

    for i, e in enumerate(emails):
        if e.get("norm_subject") == norm_subj:
            thread_emails.append((i, e))

    if not thread_emails:
        thread_emails = [(0, email)]

    # Sort by date
    thread_emails.sort(key=lambda x: x[1].get("date_iso", ""))

    messages = []
    for idx, e in thread_emails:
        messages.append({
            "from": e.get("from", "Unknown"),
            "to": e.get("to", "Unknown"),
            "cc": e.get("cc", ""),
            "date": e.get("date", ""),
            "subject": e.get("subject", ""),
            "body": e.get("body", ""),
        })

    return {
        "title": email.get("subject", "Single Email Analysis"),
        "messages": messages,
    }


def main():
    print("Loading data...")
    emails = load_json(os.path.join(MEMORY_DIR, "emails.json"))
    contacts = load_json(os.path.join(MEMORY_DIR, "contacts.json"))
    threads = load_json(os.path.join(MEMORY_DIR, "threads.json"))
    triage = load_json(os.path.join(MEMORY_DIR, "triage_results.json"))

    # Load embedding index for retrieval
    try:
        from build_index import load_index, retrieve, head_tail
        from sentence_transformers import SentenceTransformer
        print("Loading embedding index...")
        vectors, metadata = load_index()
        model = SentenceTransformer("all-MiniLM-L6-v2")
        has_index = True
    except Exception as e:
        print(f"Embedding index not available ({e}), skipping retrieval")
        has_index = False

    # Select flagged emails
    flagged = select_flagged(emails, triage)
    print(f"\nSelected {len(flagged)} flagged emails for deep analysis")

    for rank, entry in enumerate(flagged):
        idx = entry["idx"]
        email = emails[idx]
        sender = email.get("from", "Unknown")
        date_iso = email.get("date_iso", "")
        norm_subj = email.get("norm_subject", "")
        triage_entry = entry["triage"]

        print(f"\n[{rank+1}/{len(flagged)}] idx={idx} risk={entry['risk']} "
              f"from={sender} subj={email.get('subject', '')[:60]}...")

        # Retrieve related past emails
        recalled = []
        if has_index:
            recalled = retrieve(
                head_tail(email.get("body", "")),
                vectors, metadata, model,
                before_idx=idx, k=3,
            )

        # Build evidence-only memory context block
        memory_block = build_memory_context_block(
            sender=sender,
            email_idx=idx,
            date_iso=date_iso,
            contacts=contacts,
            thread_key=norm_subj,
            threads=threads,
            recalled_emails=recalled,
            triage_results=triage,
        )

        # Build thread data for subtext analysis
        thread_data = build_mini_thread(email, emails, triage)

        # Prepend memory block to user prompt
        user_prompt = memory_block + "\n\n" + format_subtext_user_prompt(thread_data)

        # Run deep analysis (cached)
        result = cached_call_llm(SUBTEXT_SYSTEM_PROMPT, user_prompt)
        print(f"  -> {len(result)} chars response")

    print(f"\n{'='*60}")
    print(f"DEEP ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Analyzed {len(flagged)} flagged emails")
    print(f"Cascade ratio: {len(flagged)}/{len(emails)} = "
          f"{len(flagged)/len(emails)*100:.1f}%")


if __name__ == "__main__":
    main()
