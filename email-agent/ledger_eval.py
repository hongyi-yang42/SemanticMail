"""Spot-check harness for the obligation ledger.

Usage:
    cd email-agent
    python ledger_eval.py          # dump spot-check file
    # Then hand-verify memory/ledger_spotcheck.json
    python ledger_eval.py --report # show agreement stats

Dumps ~12 ledger entries (mix of open + resolved) for hand-verification.
Resolution matching is heuristic: thread-reply ≠ guaranteed satisfaction.
"""

import json
import os
import random

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
SPOTCHECK_FILE = os.path.join(MEMORY_DIR, "ledger_spotcheck.json")


def load_json(name: str):
    with open(os.path.join(MEMORY_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def dump_spotcheck():
    """Select ~12 entries for hand-verification."""
    ledger = load_json("ledger.json")
    emails = load_json("emails.json")

    you_owe = ledger["you_owe"]
    you_promised = ledger["you_promised"]
    resolved = ledger["resolved"]

    # Pick 4 from each category (or fewer if not enough)
    n_open = min(4, len(you_owe))
    n_promised = min(4, len(you_promised))
    n_resolved = min(4, len(resolved))

    random.seed(42)  # Deterministic selection
    open_sample = random.sample(you_owe, n_open)
    promised_sample = random.sample(you_promised, n_promised)
    resolved_sample = random.sample(resolved, n_resolved)

    spotcheck = []
    for e in open_sample + promised_sample + resolved_sample:
        idx = e.get("_email_idx", 0)
        email = emails[idx] if idx < len(emails) else {}
        spotcheck.append({
            "category": "you_owe" if e in open_sample else (
                "you_promised" if e in promised_sample else "resolved"),
            "entry": e,
            "email_snippet": {
                "from": email.get("from", ""),
                "date": email.get("date", ""),
                "subject": email.get("subject", ""),
                "body_preview": (email.get("body", "") or "")[:300],
            },
            "hand_check": {
                "correct_direction": None,
                "correct_ask": None,
                "correct_status": None,
                "notes": "",
            },
        })

    with open(SPOTCHECK_FILE, "w", encoding="utf-8") as f:
        json.dump(spotcheck, f, ensure_ascii=False, indent=2)

    print(f"Dumped {len(spotcheck)} entries to {SPOTCHECK_FILE}")
    print(f"  you_owe: {n_open}, you_promised: {n_promised}, resolved: {n_resolved}")
    print()
    print("Hand-verify by editing the `hand_check` fields in the JSON file:")
    print('  correct_direction: true/false/null')
    print('  correct_ask: true/false/null')
    print('  correct_status: true/false/null')
    print('  notes: free text')
    print()
    print("Then run `python ledger_eval.py --report` to see precision.")
    print()
    print("NOTE: Resolution matching is heuristic — a thread reply does NOT")
    print("guarantee the ask was actually satisfied. Mark correct_status=false")
    print("if the reply was non-substantive (e.g., 'thanks', 'will do').")


def report_precision():
    """Read spot-check file and compute agreement."""
    with open(SPOTCHECK_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    checked = [d for d in data if any(
        v is not None for v in d["hand_check"].values()
        if isinstance(v, bool)
    )]

    if not checked:
        print("No entries verified yet. Edit ledger_spotcheck.json first.")
        return

    n_total = len(checked)
    n_direction_ok = sum(1 for d in checked if d["hand_check"]["correct_direction"] is True)
    n_ask_ok = sum(1 for d in checked if d["hand_check"]["correct_ask"] is True)
    n_status_ok = sum(1 for d in checked if d["hand_check"]["correct_status"] is True)

    n_direction_checked = sum(1 for d in checked if d["hand_check"]["correct_direction"] is not None)
    n_ask_checked = sum(1 for d in checked if d["hand_check"]["correct_ask"] is not None)
    n_status_checked = sum(1 for d in checked if d["hand_check"]["correct_status"] is not None)

    print(f"Spot-check results ({n_total}/{len(data)} entries verified)")
    print("=" * 50)
    if n_direction_checked:
        print(f"  Direction precision: {n_direction_ok}/{n_direction_checked} "
              f"({n_direction_ok/n_direction_checked*100:.0f}%)")
    if n_ask_checked:
        print(f"  Ask precision:       {n_ask_ok}/{n_ask_checked} "
              f"({n_ask_ok/n_ask_checked*100:.0f}%)")
    if n_status_checked:
        print(f"  Status precision:    {n_status_ok}/{n_status_checked} "
              f"({n_status_ok/n_status_checked*100:.0f}%)")

    # Print notes
    notes = [d for d in checked if d["hand_check"].get("notes")]
    if notes:
        print(f"\nNotes ({len(notes)}):")
        for d in notes:
            cat = d["category"]
            ask = d["entry"]["canonical_ask"]
            note = d["hand_check"]["notes"]
            print(f"  [{cat}] {ask}: {note}")


def main():
    import sys
    if "--report" in sys.argv:
        report_precision()
    else:
        dump_spotcheck()


if __name__ == "__main__":
    main()
