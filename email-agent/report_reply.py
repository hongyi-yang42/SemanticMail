"""Honest report: per-target cold vs scaffolded + judge scores + self-consistency.

Usage:
    cd email-agent
    python report_reply.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def main():
    section("SEMANTICMAIL SPRINT 3 — REPLY DRAFTING A/B REPORT")

    targets = load_json(os.path.join(MEMORY_DIR, "reply_ablation_targets.json"))["targets"]

    judge_path = os.path.join(MEMORY_DIR, "reply_judge_results.json")
    judge_data = load_json(judge_path) if os.path.exists(judge_path) else None

    sc_path = os.path.join(MEMORY_DIR, "self_consistency_results.json")
    sc_data = load_json(sc_path) if os.path.exists(sc_path) else None

    n_req = sum(1 for t in targets if t["category"] == "request_with_asks")
    n_face = sum(1 for t in targets if t["category"] == "face_sensitive")
    print(f"\n  Targets: {len(targets)} ({n_req} request-with-asks, {n_face} face-sensitive)")

    # ── 1. Per-target side-by-side ──────────────────────────────────
    section("1. PER-TARGET: COLD vs SCAFFOLDED")

    # Find Susan Mara for highlighting
    mara_idx = None
    for i, t in enumerate(targets):
        if "Mara" in t.get("sender", ""):
            mara_idx = i
            break

    for i, t in enumerate(targets):
        idx = t["email_idx"]
        sender = t["sender"]
        cat = t["category"]
        asks = t.get("open_asks", [])
        flagship = " ** FLAGSHIP **" if i == mara_idx else ""

        print(f"\n  --- Target {i+1}: idx={idx} [{cat}]{flagship} ---")
        print(f"  From: {sender}")
        print(f"  Subject: {t.get('subject', '')[:80]}")
        if asks:
            for a in asks[:4]:
                print(f"  Ask: {a[:100]}")

        cold_draft = t["cold"]["draft"].get("draft_text", "(parse error)")
        sc_draft = t["scaffolded"]["draft"].get("draft_text", "(parse error)")
        cold_rat = t["cold"]["draft"].get("rationale", "")
        sc_rat = t["scaffolded"]["draft"].get("rationale", "")

        print(f"\n  COLD ({len(cold_draft)} chars):")
        for line in cold_draft[:350].split("\n"):
            print(f"    {line}")
        if len(cold_draft) > 350:
            print(f"    ... ({len(cold_draft)} chars total)")
        if cold_rat:
            print(f"    Rationale: {cold_rat}")

        print(f"\n  SCAFFOLDED ({len(sc_draft)} chars):")
        for line in sc_draft[:350].split("\n"):
            print(f"    {line}")
        if len(sc_draft) > 350:
            print(f"    ... ({len(sc_draft)} chars total)")
        if sc_rat:
            print(f"    Rationale: {sc_rat}")

        ct = t["cold"]["tokens"]
        st = t["scaffolded"]["tokens"]
        in_delta = st["prompt_tokens"] - ct["prompt_tokens"]
        print(f"\n  Tokens: COLD in={ct['prompt_tokens']} out={ct['completion_tokens']} ({ct['source']})")
        print(f"          SCAF in={st['prompt_tokens']} out={st['completion_tokens']} ({st['source']})")
        print(f"          Scaffold adds ~{in_delta} input tokens ({in_delta/max(ct['prompt_tokens'],1)*100:+.0f}%)")

    # ── 2. Blind judge aggregate ────────────────────────────────────
    if judge_data:
        section("2. BLIND JUDGE RESULTS")

        judgments = judge_data["judgments"]
        n_judged = len(judgments)

        cold_asks_addr = 0
        cold_asks_total = 0
        sc_asks_addr = 0
        sc_asks_total = 0
        cold_tone_sum = 0
        sc_tone_sum = 0
        cold_subtext = 0
        sc_subtext = 0

        for j in judgments:
            scores = j.get("scores", {})
            order = j["randomized_order"]

            for label, cond in [("draft_a", order["A"]), ("draft_b", order["B"])]:
                s = scores.get(label, {})
                n_a = s.get("n_asks_addressed", 0)
                n_t = s.get("n_asks_total", 0)
                tone = s.get("tone_calibration", 0)
                sub = s.get("subtext_engagement", False)

                if cond == "cold":
                    cold_asks_addr += n_a
                    cold_asks_total += n_t
                    cold_tone_sum += tone
                    cold_subtext += int(sub)
                else:
                    sc_asks_addr += n_a
                    sc_asks_total += n_t
                    sc_tone_sum += tone
                    sc_subtext += int(sub)

        sc_wins = sum(1 for j in judgments if j["mapped_preference"] == "scaffolded")
        cold_wins = sum(1 for j in judgments if j["mapped_preference"] == "cold")
        ties = sum(1 for j in judgments if j["mapped_preference"] == "tie")

        print(f"\n  Win rate ({n_judged} targets, blind + order-randomized):")
        print(f"    Scaffolded wins: {sc_wins}/{n_judged} ({sc_wins/n_judged*100:.0f}%)")
        print(f"    Cold wins:       {cold_wins}/{n_judged} ({cold_wins/n_judged*100:.0f}%)")
        print(f"    Ties:            {ties}/{n_judged} ({ties/n_judged*100:.0f}%)")

        print(f"\n  Open-ask coverage (aggregate):")
        if cold_asks_total > 0:
            print(f"    Cold:       {cold_asks_addr}/{cold_asks_total} "
                  f"({cold_asks_addr/cold_asks_total*100:.0f}%)")
        if sc_asks_total > 0:
            print(f"    Scaffolded: {sc_asks_addr}/{sc_asks_total} "
                  f"({sc_asks_addr/sc_asks_total*100:.0f}%)")

        print(f"\n  Tone/face calibration (mean 1-5):")
        print(f"    Cold:       {cold_tone_sum/n_judged:.2f}")
        print(f"    Scaffolded: {sc_tone_sum/n_judged:.2f}")

        print(f"\n  Subtext engagement (yes count):")
        print(f"    Cold:       {cold_subtext}/{n_judged}")
        print(f"    Scaffolded: {sc_subtext}/{n_judged}")

        # Per-target detail
        print(f"\n  --- Per-target judge detail ---")
        for j in judgments:
            idx = j["email_idx"]
            sender = j["sender"]
            mapped = j["mapped_preference"]
            scores = j.get("scores", {})
            order = j["randomized_order"]

            flagship = " ** FLAGSHIP **" if "Mara" in sender else ""
            print(f"\n  idx={idx} {sender}{flagship}")
            print(f"    Order: A={order['A']}, B={order['B']}")
            print(f"    Raw pref: {scores.get('overall_preference', '?')} -> mapped: {mapped}")

            for label in ["draft_a", "draft_b"]:
                s = scores.get(label, {})
                key = label.split("_")[1].upper()
                cond = order[key]
                print(f"    {label} ({cond}): "
                      f"asks={s.get('n_asks_addressed', '?')}/{s.get('n_asks_total', '?')} "
                      f"tone={s.get('tone_calibration', '?')} "
                      f"subtext={s.get('subtext_engagement', '?')}")

    # ── 3. Self-consistency ─────────────────────────────────────────
    if sc_data:
        section("3. SELF-CONSISTENCY (VARIANCE)")

        agg = sc_data["aggregate"]
        results = sc_data["results"]

        print(f"\n  Mean cosine spread (higher = more variance):")
        print(f"    Cold:       {agg['mean_cold_spread']:.4f}")
        print(f"    Scaffolded: {agg['mean_scaffolded_spread']:.4f}")
        print(f"    Delta:      {agg['delta']:+.4f}")
        label = "SUPPORTED" if agg["hypothesis_supported"] else "NOT SUPPORTED"
        print(f"    Hypothesis: {label}")

        print(f"\n  Per-target:")
        for r in results:
            flagship = " *" if "Mara" in r["sender"] else ""
            delta = r["cold_spread"] - r["scaffolded_spread"]
            print(f"    idx={r['email_idx']} {r['sender'][:20]:20s} "
                  f"cold={r['cold_spread']:.4f} sc={r['scaffolded_spread']:.4f} "
                  f"d={delta:+.4f}{flagship}")

    # ── 4. Cost (honest) ────────────────────────────────────────────
    section("4. COST (HONEST)")

    total_cold_in = sum(t["cold"]["tokens"]["prompt_tokens"] for t in targets)
    total_cold_out = sum(t["cold"]["tokens"]["completion_tokens"] for t in targets)
    total_sc_in = sum(t["scaffolded"]["tokens"]["prompt_tokens"] for t in targets)
    total_sc_out = sum(t["scaffolded"]["tokens"]["completion_tokens"] for t in targets)

    n_measured = sum(
        1 for t in targets
        if t["cold"]["tokens"]["source"] == "measured"
        or t["scaffolded"]["tokens"]["source"] == "measured"
    )

    print(f"\n  Scaffolded uses MORE input tokens. That IS the treatment.")
    print(f"  The claimed win is coverage / calibration / variance,")
    print(f"  NOT raw cost or wall-clock speed.\n")

    print(f"  Total COLD tokens:      in={total_cold_in:,} out={total_cold_out:,}")
    print(f"  Total SCAFFOLDED tokens: in={total_sc_in:,} out={total_sc_out:,}")
    overhead = total_sc_in - total_cold_in
    pct = overhead / max(total_cold_in, 1) * 100
    print(f"  Input overhead:         {overhead:,} tokens ({pct:+.0f}%)")

    print(f"\n  Token sources: {n_measured} measured, {len(targets)*2 - n_measured} estimated")
    print(f"  (Measured on first run; estimated on cache hits via chars/4)")
    print(f"  wall_ms = 0 means cache hit (near-instant).")
    print(f"  First-run latency requires fresh cache or check wall_ms > 0 entries.")

    section("DONE")
    print("  Pipeline: draft_reply.py -> ablation_reply_judge.py -> "
          "self_consistency.py -> report_reply.py")


if __name__ == "__main__":
    main()
