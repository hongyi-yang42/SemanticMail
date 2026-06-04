"""Memory ablation A/B: deep-analyze one email with vs without memory context.

Usage:
    cd email-agent
    python ablation_memory.py

Picks ONE late email from a sender with 5+ interactions and risk >= caution.
Runs SUBTEXT_SYSTEM_PROMPT twice:
  A) With memory context block prepended
  B) Without memory context block
Both cache results separately (different user prompts = different MD5 keys).
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
ABLATION_RESULT = os.path.join(MEMORY_DIR, "ablation_result.json")


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_ablation_email(emails: list[dict], contacts: dict,
                         triage: list[dict]) -> dict | None:
    """Select best candidate for A/B comparison.

    Criteria:
    - In last 40% of the date range
    - From a sender with 5+ prior interactions
    - Risk >= caution in triage
    """
    n = len(emails)
    cutoff = int(n * 0.6)  # last 40%

    candidates = []
    for i in range(cutoff, n):
        sender = emails[i].get("from", "")
        contact = contacts.get(sender, {})
        t = triage[i] if i < len(triage) else {}
        risk = t.get("risk_level", "safe")

        if contact.get("n_interactions", 0) >= 5 and RISK_ORDER.get(risk, 0) >= 1:
            # Score: prefer higher interaction count and higher risk
            score = contact["n_interactions"] * 10 + RISK_ORDER.get(risk, 0)
            candidates.append((score, i))

    if not candidates:
        # Fallback: any email with 3+ interactions and risk >= caution
        for i in range(cutoff, n):
            sender = emails[i].get("from", "")
            contact = contacts.get(sender, {})
            t = triage[i] if i < len(triage) else {}
            risk = t.get("risk_level", "safe")

            if contact.get("n_interactions", 0) >= 3 and RISK_ORDER.get(risk, 0) >= 1:
                score = contact["n_interactions"] * 10 + RISK_ORDER.get(risk, 0)
                candidates.append((score, i))

    if not candidates:
        print("No suitable A/B candidate found")
        return None

    candidates.sort(key=lambda x: -x[0])
    _, best_idx = candidates[0]
    return {"idx": best_idx, "email": emails[best_idx]}


def main():
    print("Loading data...")
    emails = load_json(os.path.join(MEMORY_DIR, "emails.json"))
    contacts = load_json(os.path.join(MEMORY_DIR, "contacts.json"))
    threads = load_json(os.path.join(MEMORY_DIR, "threads.json"))
    triage = load_json(os.path.join(MEMORY_DIR, "triage_results.json"))

    # Load embedding index
    try:
        from build_index import load_index, retrieve, head_tail
        from sentence_transformers import SentenceTransformer
        vectors, metadata = load_index()
        model = SentenceTransformer("all-MiniLM-L6-v2")
        has_index = True
    except Exception as e:
        print(f"Embedding index not available ({e})")
        has_index = False

    # Pick candidate
    candidate = pick_ablation_email(emails, contacts, triage)
    if candidate is None:
        sys.exit(1)

    idx = candidate["idx"]
    email = candidate["email"]
    sender = email.get("from", "Unknown")
    date_iso = email.get("date_iso", "")
    norm_subj = email.get("norm_subject", "")
    triage_entry = triage[idx] if idx < len(triage) else {}

    print(f"\nA/B candidate: idx={idx}")
    print(f"  From: {sender}")
    print(f"  Date: {date_iso[:10]}")
    print(f"  Subject: {email.get('subject', '')[:80]}")
    print(f"  Triage risk: {triage_entry.get('risk_level', '?')}")
    print(f"  Prior interactions: {contacts.get(sender, {}).get('n_interactions', 0)}")

    # Retrieve related past emails
    recalled = []
    if has_index:
        recalled = retrieve(
            email.get("body", "")[:1000],
            vectors, metadata, model,
            before_idx=idx, k=3,
        )

    # Build thread data
    mini_thread = {
        "title": email.get("subject", "A/B Analysis"),
        "messages": [{
            "from": email.get("from", ""),
            "to": email.get("to", ""),
            "cc": email.get("cc", ""),
            "date": email.get("date", ""),
            "subject": email.get("subject", ""),
            "body": email.get("body", ""),
        }],
    }

    base_user_prompt = format_subtext_user_prompt(mini_thread)

    # --- Condition A: WITH memory context ---
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
    user_prompt_with = memory_block + "\n\n" + base_user_prompt

    print("\nRunning Condition A (WITH memory context)...")
    result_with = cached_call_llm(SUBTEXT_SYSTEM_PROMPT, user_prompt_with)
    print(f"  -> {len(result_with)} chars")

    # --- Condition B: WITHOUT memory context ---
    print("Running Condition B (WITHOUT memory context)...")
    result_without = cached_call_llm(SUBTEXT_SYSTEM_PROMPT, base_user_prompt)
    print(f"  -> {len(result_without)} chars")

    # Save A/B result
    ablation = {
        "email_idx": idx,
        "email": email,
        "sender": sender,
        "date_iso": date_iso,
        "triage": triage_entry,
        "memory_block": memory_block,
        "with_memory": result_with,
        "without_memory": result_without,
    }
    with open(ABLATION_RESULT, "w", encoding="utf-8") as f:
        json.dump(ablation, f, ensure_ascii=False, indent=2)

    print(f"\nA/B result saved to {ABLATION_RESULT}")


if __name__ == "__main__":
    main()
