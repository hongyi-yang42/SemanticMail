"""Chronological triage pass: 1 LLM call per email, accumulate contacts + threads.

Usage:
    cd email-agent
    python triage_pass.py

Processes ~400 emails in date order via cached_call_llm().
Writes memory/contacts.json and memory/threads.json.
Tracks first-run wall-clock for honest throughput reporting.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from llm.cache import cached_call_llm
from prompts.triage import TRIAGE_SYSTEM_PROMPT, TRIAGE_USER_TEMPLATE

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")

RISK_ORDER = {"safe": 0, "caution": 1, "warning": 2, "critical": 3}


def load_emails() -> list[dict]:
    with open(os.path.join(MEMORY_DIR, "emails.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def format_triage_prompt(e: dict) -> str:
    return TRIAGE_USER_TEMPLATE.format(
        from_=e.get("from", ""),
        to=e.get("to", ""),
        date=e.get("date", ""),
        subject=e.get("subject", ""),
        body=e.get("body", ""),
    )


def parse_triage_json(raw: str) -> dict:
    """Parse triage JSON, returning defaults on failure."""
    try:
        data = json.loads(raw)
        return {
            "intent": data.get("intent", "unknown"),
            "urgency": data.get("urgency", "low"),
            "risk_level": data.get("risk_level", "safe"),
            "tone_label": data.get("tone_label", "neutral"),
            "key_signals": data.get("key_signals", []),
            "open_asks": data.get("open_asks", []),
        }
    except (json.JSONDecodeError, TypeError):
        return {
            "intent": "unknown", "urgency": "low", "risk_level": "safe",
            "tone_label": "neutral", "key_signals": [], "open_asks": [],
        }


def update_contact(contacts: dict, sender: str, triage: dict, date_iso: str):
    """Mutate contacts dict in-place."""
    if sender not in contacts:
        contacts[sender] = {
            "n_interactions": 0,
            "first_seen": date_iso,
            "last_seen": date_iso,
            "tone_labels": [],
            "risk_history": [],
            "open_asks": [],
        }

    c = contacts[sender]
    c["n_interactions"] += 1
    c["last_seen"] = date_iso
    c["tone_labels"].append(triage["tone_label"])
    c["risk_history"].append(triage["risk_level"])
    if triage["open_asks"]:
        c["open_asks"].extend(triage["open_asks"])


def update_thread(threads: dict, norm_subject: str, triage: dict, date_iso: str, sender: str):
    """Mutate threads dict in-place."""
    key = norm_subject or "(no subject)"
    if key not in threads:
        threads[key] = {
            "status": "open",
            "last_date": date_iso,
            "n_emails": 0,
            "pending_reply_from": None,
        }

    t = threads[key]
    t["n_emails"] += 1
    t["last_date"] = date_iso

    # If high urgency or risk >= caution, mark as needing reply
    if triage["urgency"] in ("high", "critical") or RISK_ORDER.get(triage["risk_level"], 0) >= 1:
        t["pending_reply_from"] = sender


def main():
    emails = load_emails()
    print(f"Loaded {len(emails)} emails for triage")

    contacts = {}
    threads = {}
    triage_results = []

    # Check which are already cached (no API call needed)
    cache_dir = os.path.join(os.path.dirname(__file__), "data", "cache")
    from llm.cache import _cache_key, _cache_path

    n_cached = 0
    n_new = 0
    start_time = time.time()

    for i, e in enumerate(emails):
        user_prompt = format_triage_prompt(e)
        key = _cache_key(TRIAGE_SYSTEM_PROMPT, user_prompt, 0.3, "deepseek-chat")
        cache_file = _cache_path(key)
        is_cached = os.path.exists(cache_file)

        if is_cached:
            n_cached += 1
        else:
            n_new += 1

        # Call (will hit cache if available)
        raw = cached_call_llm(TRIAGE_SYSTEM_PROMPT, user_prompt)
        triage = parse_triage_json(raw)
        triage["_email_idx"] = i
        triage["_cached"] = is_cached
        triage_results.append(triage)

        sender = e.get("from", "Unknown")
        date_iso = e.get("date_iso", "")
        norm_subj = e.get("norm_subject", "")

        update_contact(contacts, sender, triage, date_iso)
        update_thread(threads, norm_subj, triage, date_iso, sender)

        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            print(f"  [{i+1}/{len(emails)}] {elapsed:.1f}s elapsed "
                  f"({n_new} new calls, {n_cached} cached)")

    elapsed = time.time() - start_time

    # Save contacts and threads
    with open(os.path.join(MEMORY_DIR, "contacts.json"), "w", encoding="utf-8") as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)

    with open(os.path.join(MEMORY_DIR, "threads.json"), "w", encoding="utf-8") as f:
        json.dump(threads, f, ensure_ascii=False, indent=2)

    # Save triage results alongside emails for report.py
    with open(os.path.join(MEMORY_DIR, "triage_results.json"), "w", encoding="utf-8") as f:
        json.dump(triage_results, f, ensure_ascii=False, indent=2)

    # Summary
    risk_counts = {"safe": 0, "caution": 0, "warning": 0, "critical": 0}
    for t in triage_results:
        r = t.get("risk_level", "safe")
        risk_counts[r] = risk_counts.get(r, 0) + 1

    print(f"\n{'='*60}")
    print(f"TRIAGE COMPLETE")
    print(f"{'='*60}")
    print(f"Total emails: {len(emails)}")
    print(f"New LLM calls: {n_new} | Cached hits: {n_cached}")
    print(f"Wall-clock: {elapsed:.1f}s")
    if n_new > 0:
        print(f"Per-new-email: {elapsed/n_new:.2f}s avg")
    print(f"\nRisk funnel:")
    for level in ["safe", "caution", "warning", "critical"]:
        print(f"  {level:10s}: {risk_counts.get(level, 0)}")
    print(f"\nUnique senders: {len(contacts)}")
    print(f"Unique threads: {len(threads)}")
    print(f"Saved: memory/contacts.json, memory/threads.json, memory/triage_results.json")


if __name__ == "__main__":
    main()
