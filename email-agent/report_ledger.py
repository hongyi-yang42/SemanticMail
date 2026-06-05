"""Print the obligation ledger report.

Usage:
    cd email-agent
    python report_ledger.py

Reads memory/ledger.json and prints summary stats, top open obligations,
and a worked example tied to memory.
"""

import json
import os
import sys

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")


def load_json(name: str):
    with open(os.path.join(MEMORY_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ledger = load_json("ledger.json")
    contacts = load_json("contacts.json")

    counts = ledger["counts"]
    you_owe = ledger["you_owe"]
    you_promised = ledger["you_promised"]
    resolved = ledger["resolved"]

    print("=" * 60)
    print("OBLIGATION LEDGER REPORT")
    print("=" * 60)
    print(f"Corpus date range ends: {ledger['corpus_today'][:10]}")
    print()

    # --- Counts ---
    print("## Counts")
    print(f"  Open you-owe:       {counts['you_owe_open']}")
    print(f"  Open you-promised:  {counts['you_promised_open']}")
    print(f"  Resolved:           {counts['resolved']}")
    total = counts["total"]
    print(f"  Total obligations:  {total}")
    rate = counts["resolved"] / max(1, total) * 100
    print(f"  Resolution rate:    {rate:.1f}%")
    print()

    # --- Oldest 5 open obligations ---
    all_open = you_owe + you_promised
    all_open.sort(key=lambda e: e["age_days"], reverse=True)

    print("## Oldest 5 Open Obligations")
    print(f"  {'#':<3} {'Age':>5} {'Direction':<10} {'Contact':<25} {'Ask'}")
    print(f"  {'-'*3} {'-'*5} {'-'*10} {'-'*25} {'-'*30}")
    for i, e in enumerate(all_open[:5]):
        direction = "OWE" if e["direction"] == "inbound" else "OWED"
        ask = e["canonical_ask"][:40]
        contact = e["contact"][:24]
        print(f"  {i+1:<3} {e['age_days']:>4}d {direction:<10} {contact:<25} {ask}")
    print()

    # --- Top contacts you owe ---
    # Aggregate by contact
    contact_owes = {}
    for e in you_owe:
        c = e["contact"]
        contact_owes.setdefault(c, []).append(e)

    sorted_contacts = sorted(contact_owes.items(), key=lambda x: len(x[1]), reverse=True)

    print("## Top Contacts You Owe")
    print(f"  {'Contact':<25} {'Open Asks':<10} {'Oldest'}")
    print(f"  {'-'*25} {'-'*10} {'-'*10}")
    for c, entries in sorted_contacts[:10]:
        oldest = max(e["age_days"] for e in entries)
        print(f"  {c[:24]:<25} {len(entries):<10} {oldest}d")
    print()

    # --- Worked example: find a rich contact ---
    # Pick the first contact from you_owe that also has memory context
    example = None
    for e in all_open:
        c = e["contact"]
        if c in contacts:
            cdata = contacts[c]
            if cdata.get("n_interactions", 0) >= 3 and cdata.get("open_asks"):
                example = e
                break

    if example:
        c = example["contact"]
        cdata = contacts.get(c, {})
        print("## Worked Example")
        print(f"  Contact: {c}")
        print(f"  Interactions: {cdata.get('n_interactions', 0)}")
        print(f"  Tone trajectory: {' → '.join(cdata.get('tone_labels', []))}")
        print(f"  Risk history: {' → '.join(cdata.get('risk_history', []))}")
        print(f"  Open ask: \"{example['canonical_ask']}\"")
        print(f"  Age: {example['age_days']} days")
        print(f"  Thread: {example['norm_subject']}")
        print(f"  Original asks in memory: {cdata.get('open_asks', [])[:3]}")
        print()

    print("=" * 60)
    print(f"Total: {len(all_open)} open, {len(resolved)} resolved, {rate:.1f}% resolution")


if __name__ == "__main__":
    main()
