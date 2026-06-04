"""Build the obligation ledger from triage results + sent emails.

Usage:
    cd email-agent
    python build_ledger.py

Pipeline:
  1. Load triage results + emails — filter to ask-bearing emails (~219).
  2. Classify each via obligation prompt (cached_call_llm).
  3. Accumulate obligations from inbound + Jeff's sent emails.
  4. Resolve via thread-based heuristic:
     - If obligor sent a later message in same thread after ask date → tentatively resolved.
     - Uses ThreadState + norm_subject matching.
  5. Compute age relative to corpus "today" (= latest email date in slice).
  6. Rank OPEN by age × contact importance.
  7. Write memory/ledger.json.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from llm.cache import cached_call_llm, _cache_key, _cache_path
from prompts.obligation import OBLIGATION_SYSTEM_PROMPT, format_obligation_user_prompt

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")


def load_json(name: str):
    with open(os.path.join(MEMORY_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(name: str, data):
    with open(os.path.join(MEMORY_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_obligation_json(raw: str) -> list[dict]:
    """Parse obligation JSON, returning [] on failure."""
    try:
        data = json.loads(raw)
        obs = data.get("obligations", [])
        valid = []
        for o in obs:
            if not isinstance(o, dict):
                continue
            direction = o.get("direction", "inbound")
            if direction not in ("inbound", "outbound"):
                direction = "inbound"
            valid.append({
                "direction": direction,
                "canonical_ask": o.get("canonical_ask", "unknown ask"),
                "implied_deadline": o.get("implied_deadline"),
                "obligor": o.get("obligor", "Unknown"),
            })
        return valid
    except (json.JSONDecodeError, TypeError):
        return []


def parse_iso_date(s: str | None) -> datetime | None:
    """Parse ISO date string, return None on failure."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def find_corpus_today(emails: list[dict], sent: list[dict]) -> datetime:
    """The 'today' for the corpus = latest email date across all slices."""
    latest = datetime(2000, 1, 1, tzinfo=timezone.utc)
    for e in emails + sent:
        d = parse_iso_date(e.get("date_iso"))
        if d and d > latest:
            latest = d
    return latest


def build_sent_index(sent: list[dict]) -> dict:
    """Index sent emails by (norm_subject_lower, date_iso) for resolution."""
    by_thread = {}
    for e in sent:
        subj = (e.get("norm_subject") or "").strip().lower()
        if not subj:
            continue
        by_thread.setdefault(subj, []).append(e)
    return by_thread


def build_inbox_index(emails: list[dict]) -> dict:
    """Index inbox emails by norm_subject for resolution lookup."""
    by_thread = {}
    for e in emails:
        subj = (e.get("norm_subject") or "").strip().lower()
        if not subj:
            continue
        by_thread.setdefault(subj, []).append(e)
    return by_thread


def is_resolved(
    obligor: str,
    ask_date: datetime,
    norm_subject: str,
    sent_index: dict,
    inbox_index: dict,
    threads: dict,
) -> bool:
    """Heuristic: obligor sent a later message in the same thread after the ask date.

    Uses thread state + norm_subject matching. Checks both sent and inbox.
    """
    norm_subj = norm_subject.strip().lower()
    if not norm_subj:
        return False

    # Check thread state: pending_reply_from is a strong signal
    thread_key = None
    for tk in threads:
        if tk.strip().lower() == norm_subj:
            thread_key = tk
            break

    if thread_key:
        t = threads[thread_key]
        # If pending_reply_from is null or not the obligor, less likely still pending
        pending = t.get("pending_reply_from")
        # If Jeff is the obligor and thread has no pending reply, might be resolved
        if "jeff" in obligor.lower() or "dasovich" in obligor.lower():
            if pending is None and t.get("n_emails", 0) > 1:
                # Jeff likely replied in thread
                return True

    # Check if obligor (or someone acting for them) sent a later message in the thread
    later_msgs = []

    # Check sent index (Jeff's sent)
    for e in sent_index.get(norm_subj, []):
        msg_date = parse_iso_date(e.get("date_iso"))
        if msg_date and msg_date > ask_date:
            sender = e.get("from", "")
            if "jeff" in sender.lower() or "dasovich" in sender.lower():
                if "jeff" in obligor.lower() or "dasovich" in obligor.lower():
                    later_msgs.append(msg_date)

    # Check inbox index (others' replies)
    for e in inbox_index.get(norm_subj, []):
        msg_date = parse_iso_date(e.get("date_iso"))
        if msg_date and msg_date > ask_date:
            sender = e.get("from", "")
            # Check if the obligor (not Jeff) sent a reply
            if ("jeff" not in sender.lower() and "dasovich" not in sender.lower()):
                # Simple name matching — check if sender matches obligor
                obligor_parts = obligor.lower().replace(",", "").split()
                sender_parts = sender.lower().replace(",", "").split()
                if any(p in sender_parts for p in obligor_parts if len(p) > 2):
                    later_msgs.append(msg_date)

    return len(later_msgs) > 0


def compute_importance(contact_name: str, contacts: dict) -> float:
    """Contact importance = n_interactions × risk_weight."""
    c = contacts.get(contact_name, {})
    n = c.get("n_interactions", 1)
    risk_history = c.get("risk_history", [])
    risk_weight = sum(1 for r in risk_history if r in ("warning", "critical"))
    return n * (1 + risk_weight)


def main():
    # Load data
    emails = load_json("emails.json")
    sent = load_json("sent_emails.json")
    triage_results = load_json("triage_results.json")
    contacts = load_json("contacts.json")
    threads = load_json("threads.json")

    corpus_today = find_corpus_today(emails, sent)
    print(f"Corpus 'today': {corpus_today.isoformat()}")
    print(f"Loaded {len(emails)} inbox, {len(sent)} sent, {len(triage_results)} triage results")

    # Step 1: filter ask-bearing emails
    ask_indices = [
        t["_email_idx"] for t in triage_results
        if t.get("open_asks") and "_email_idx" in t
    ]
    print(f"Ask-bearing emails: {len(ask_indices)}")

    # Step 2: classify each ask-bearing email
    obligations = []
    n_cached = 0
    n_new = 0
    start_time = time.time()

    for count, idx in enumerate(ask_indices):
        email = emails[idx]
        triage = triage_results[idx]
        open_asks = triage.get("open_asks", [])

        user_prompt = format_obligation_user_prompt(email, open_asks)

        # Check cache status
        key = _cache_key(OBLIGATION_SYSTEM_PROMPT, user_prompt, 0.3, "deepseek-chat")
        cache_file = _cache_path(key)
        is_cached = os.path.exists(cache_file)
        if is_cached:
            n_cached += 1
        else:
            n_new += 1

        raw = cached_call_llm(OBLIGATION_SYSTEM_PROMPT, user_prompt)
        obs = parse_obligation_json(raw)

        for o in obs:
            o["_email_idx"] = idx
            o["_norm_subject"] = email.get("norm_subject", "")
            o["_date_iso"] = email.get("date_iso", "")
            o["_from"] = email.get("from", "")
            obligations.append(o)

        if (count + 1) % 50 == 0:
            elapsed = time.time() - start_time
            print(f"  [{count+1}/{len(ask_indices)}] {elapsed:.1f}s "
                  f"({n_new} new, {n_cached} cached) — {len(obligations)} obligations so far")

    elapsed = time.time() - start_time
    print(f"\nClassification done: {len(obligations)} obligations from {len(ask_indices)} emails")
    print(f"  New calls: {n_new} | Cached: {n_cached} | Wall: {elapsed:.1f}s")

    # Step 3: resolve obligations
    sent_index = build_sent_index(sent)
    inbox_index = build_inbox_index(emails)

    you_owe = []      # inbound — Jeff owes
    you_promised = []  # outbound — someone owes Jeff (or Jeff promised to follow up)
    resolved = []

    for o in obligations:
        ask_date = parse_iso_date(o["_date_iso"]) or corpus_today
        norm_subj = o.get("_norm_subject", "")
        direction = o["direction"]
        obligor = o["obligor"]

        is_res = is_resolved(obligor, ask_date, norm_subj, sent_index, inbox_index, threads)

        # Compute age in days relative to corpus today
        age_days = (corpus_today - ask_date).days
        if age_days < 0:
            age_days = 0

        # Determine contact (the other party, not Jeff)
        is_jeff = "jeff" in obligor.lower() or "dasovich" in obligor.lower()
        contact = o["_from"] if is_jeff else obligor
        # Clean contact name for lookup
        contact_key = contact.strip()
        # Try matching in contacts
        best_match = None
        for ck in contacts:
            if ck.lower() in contact_key.lower() or contact_key.lower() in ck.lower():
                best_match = ck
                break
        importance = compute_importance(best_match, contacts) if best_match else 1.0

        entry = {
            "direction": direction,
            "canonical_ask": o["canonical_ask"],
            "implied_deadline": o.get("implied_deadline"),
            "obligor": obligor,
            "contact": best_match or contact_key,
            "ask_date": o["_date_iso"],
            "age_days": age_days,
            "norm_subject": norm_subj,
            "importance": round(importance, 1),
            "status": "resolved" if is_res else "open",
            "_email_idx": o["_email_idx"],
        }

        if is_res:
            resolved.append(entry)
        elif direction == "inbound":
            you_owe.append(entry)
        else:
            you_promised.append(entry)

    # Step 4: rank open obligations by age × importance
    def sort_key(e):
        return e["age_days"] * e["importance"]

    you_owe.sort(key=sort_key, reverse=True)
    you_promised.sort(key=sort_key, reverse=True)

    # Step 5: write ledger
    ledger = {
        "corpus_today": corpus_today.isoformat(),
        "counts": {
            "you_owe_open": len(you_owe),
            "you_promised_open": len(you_promised),
            "resolved": len(resolved),
            "total": len(obligations),
        },
        "you_owe": you_owe,
        "you_promised": you_promised,
        "resolved": resolved,
    }

    save_json("ledger.json", ledger)
    print(f"\nLedger written to memory/ledger.json")
    print(f"  you_owe (open):     {len(you_owe)}")
    print(f"  you_promised (open): {len(you_promised)}")
    print(f"  resolved:           {len(resolved)}")
    print(f"  resolution rate:    {len(resolved)/max(1, len(obligations))*100:.1f}%")


if __name__ == "__main__":
    main()
