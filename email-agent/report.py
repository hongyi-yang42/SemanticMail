"""Console report: funnel, contacts, A/B example, honest throughput.

Usage:
    cd email-agent
    python report.py

Reads all memory/ data and data/cache/ to produce a comprehensive report.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
RISK_ORDER = {"safe": 0, "caution": 1, "warning": 2, "critical": 3}
TONE_ORDER = {"enthusiastic": 0, "warm": 1, "neutral": 2, "cool": 3, "evasive": 4, "hostile": 5}


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_funnel(triage: list[dict]):
    """Print risk funnel."""
    print_section("1. TRIAGE FUNNEL")
    risk_counts = {"safe": 0, "caution": 0, "warning": 0, "critical": 0}
    for t in triage:
        r = t.get("risk_level", "safe")
        risk_counts[r] = risk_counts.get(r, 0) + 1

    total = len(triage)
    print(f"  Total emails:    {total}")
    for level in ["safe", "caution", "warning", "critical"]:
        c = risk_counts.get(level, 0)
        pct = c / total * 100 if total else 0
        bar = "#" * int(pct / 2)
        print(f"  {level:10s}: {c:4d} ({pct:5.1f}%)  {bar}")

    flagged = total - risk_counts.get("safe", 0)
    print(f"\n  Flagged (caution+): {flagged} ({flagged/total*100:.1f}%)")
    print(f"  Cascade ratio (deep/total): ~20/{total} = {20/total*100:.1f}%")


def print_top_contacts(contacts: dict, emails: list[dict], n: int = 5):
    """Print top N contacts with cooling trajectory example."""
    print_section("2. TOP CONTACTS BY INTERACTION")

    sorted_contacts = sorted(
        contacts.items(), key=lambda x: -x[1].get("n_interactions", 0)
    )

    cooling_example = None

    for rank, (sender, c) in enumerate(sorted_contacts[:n], 1):
        tones = c.get("tone_labels", [])
        risks = c.get("risk_history", [])
        n_int = c.get("n_interactions", 0)
        span = f"{c.get('first_seen', '?')[:10]} → {c.get('last_seen', '?')[:10]}"

        # Check for cooling trajectory
        has_cooling = False
        if len(tones) >= 3:
            # Look for warm/enthusiastic → cool/evasive shift
            early_avg = sum(TONE_ORDER.get(t, 2) for t in tones[:len(tones)//2]) / max(len(tones)//2, 1)
            late_avg = sum(TONE_ORDER.get(t, 2) for t in tones[len(tones)//2:]) / max(len(tones) - len(tones)//2, 1)
            if late_avg > early_avg + 0.5:  # temperature rose (cooled)
                has_cooling = True
                if cooling_example is None:
                    cooling_example = (sender, c, tones, risks)

        cooling_mark = " [COOLING]" if has_cooling else ""
        print(f"\n  #{rank} {sender}{cooling_mark}")
        print(f"     {n_int} emails, {span}")
        print(f"     Tones: {tones[-6:] if len(tones) > 6 else tones}")
        print(f"     Risks: {risks[-6:] if len(risks) > 6 else risks}")

    # Print cooling example detail
    if cooling_example:
        sender, c, tones, risks = cooling_example
        print(f"\n  --- COOLING TRAJECTORY EXAMPLE ---")
        print(f"  Sender: {sender}")
        print(f"  Full tone sequence: {tones}")
        print(f"  Full risk sequence: {risks}")
        # Find an example email from this sender
        for e in emails:
            if e.get("from") == sender:
                print(f"  Example email: [{e.get('date_iso', '')[:10]}] {e.get('subject', '')[:70]}")
                print(f"    Body preview: {e.get('body', '')[:150]}...")
                break


def print_ab_comparison():
    """Print A/B comparison side by side."""
    print_section("3. MEMORY ABLATION A/B")

    path = os.path.join(MEMORY_DIR, "ablation_result.json")
    if not os.path.exists(path):
        print("  No A/B result found. Run ablation_memory.py first.")
        return

    ab = load_json(path)
    email = ab.get("email", {})

    print(f"  Email: [{email.get('date_iso', '')[:10]}] {email.get('subject', '')}")
    print(f"  From: {email.get('from', '')}")
    print(f"  Triage risk: {ab.get('triage', {}).get('risk_level', '?')}")
    print(f"\n  Body (first 300 chars):")
    print(f"  {email.get('body', '')[:300]}...")

    print(f"\n  --- MEMORY CONTEXT BLOCK (evidence only) ---")
    memory_block = ab.get("memory_block", "")
    for line in memory_block.split("\n")[:15]:
        print(f"  {line}")
    if len(memory_block.split("\n")) > 15:
        print(f"  ... ({len(memory_block.split(chr(10)))} lines total)")

    # Parse and compare analyses
    print(f"\n  --- COMPARISON ---")
    with_mem = ab.get("with_memory", "")
    without_mem = ab.get("without_memory", "")

    for label, raw in [("WITH memory", with_mem), ("WITHOUT memory", without_mem)]:
        print(f"\n  [{label}] ({len(raw)} chars)")
        try:
            analysis = json.loads(raw)
            per_email = analysis.get("per_email_analysis", [])
            for pe in per_email:
                risk = pe.get("risk_level", "?")
                tone = pe.get("social_dynamics", {}).get("tone_label", "?")
                imp = pe.get("pragmatic_inference", {}).get("implicature", "?")[:120]
                print(f"    Risk: {risk} | Tone: {tone}")
                print(f"    Implicature: {imp}...")
            thread = analysis.get("thread_level", {})
            print(f"    Overall risk: {thread.get('overall_risk', '?')}")
            print(f"    Trajectory: {thread.get('tone_trajectory', [])}")
        except json.JSONDecodeError:
            print(f"    (raw): {raw[:200]}...")

    print(f"\n  WITH memory length:  {len(with_mem)} chars")
    print(f"  WITHOUT memory length: {len(without_mem)} chars")
    diff = len(with_mem) - len(without_mem)
    print(f"  Delta: {diff:+d} chars ({diff/len(without_mem)*100:+.1f}%)")


def print_throughput(triage: list[dict], emails: list[dict]):
    """Print honest throughput metrics."""
    print_section("4. THROUGHPUT & COST")

    total = len(emails)
    flagged = sum(1 for t in triage if RISK_ORDER.get(t.get("risk_level", "safe"), 0) >= 1)
    deep = min(20, flagged)

    # Count cache status
    n_cached = sum(1 for t in triage if t.get("_cached", False))
    n_new = total - n_cached

    print(f"  Total emails:          {total}")
    print(f"  Triage LLM calls:      {total} ({n_new} new, {n_cached} cached)")
    print(f"  Deep analysis calls:   ~{deep}")
    print(f"  A/B calls:             2")
    print(f"  Total LLM calls:       ~{total + deep + 2}")
    print(f"\n  Cascade ratio:         {deep}/{total} = {deep/total*100:.1f}%")

    # Per-new-email incremental cost
    print(f"\n  Per-new-email cost breakdown:")
    print(f"    Embedding:   free (local all-MiniLM-L6-v2)")
    print(f"    Retrieval:   free (cosine sim on ~400 vectors)")
    print(f"    Triage call: 1 x DeepSeek V4-Flash (~500 tokens in, ~200 out)")
    print(f"    Deep call:   only if flagged (~{deep/total*100:.0f}% of emails)")

    # Estimate token cost
    # Average triage: ~500 chars input, ~300 chars output
    triage_input_tokens = total * 125  # ~0.25 tokens/char
    triage_output_tokens = total * 75
    deep_input_tokens = deep * 1500
    deep_output_tokens = deep * 500

    print(f"\n  Estimated tokens (triage):")
    print(f"    Input:  ~{triage_input_tokens:,}")
    print(f"    Output: ~{triage_output_tokens:,}")
    print(f"  Estimated tokens (deep):")
    print(f"    Input:  ~{deep_input_tokens:,}")
    print(f"    Output: ~{deep_output_tokens:,}")

    total_tokens = triage_input_tokens + triage_output_tokens + deep_input_tokens + deep_output_tokens + 3000
    print(f"  Total estimated: ~{total_tokens:,} tokens")

    # DeepSeek V4-Flash pricing (approximate)
    # Input: $0.07/M, Output: $0.33/M (as of 2026)
    cost = (triage_input_tokens + deep_input_tokens) * 0.07 / 1e6 + \
           (triage_output_tokens + deep_output_tokens) * 0.33 / 1e6
    print(f"  Estimated cost: ~${cost:.3f}")


def main():
    print_section("SEMANTICMAIL SPRINT 2 — INBOX MEMORY REPORT")
    print(f"  Receiver: Jeff Dasovich (dasovich-j)")
    print(f"  Corpus: Enron email dataset (public)")

    emails = load_json(os.path.join(MEMORY_DIR, "emails.json"))
    triage_path = os.path.join(MEMORY_DIR, "triage_results.json")
    if not os.path.exists(triage_path):
        print("\n  ERROR: triage_results.json not found. Run triage_pass.py first.")
        return
    triage = load_json(triage_path)

    contacts = load_json(os.path.join(MEMORY_DIR, "contacts.json"))

    print_funnel(triage)
    print_top_contacts(contacts, emails)
    print_ab_comparison()
    print_throughput(triage, emails)

    print_section("DONE")
    print("  Run order: enron_load.py → build_index.py → triage_pass.py → "
          "deep_analysis.py → ablation_memory.py → report.py")


if __name__ == "__main__":
    main()
