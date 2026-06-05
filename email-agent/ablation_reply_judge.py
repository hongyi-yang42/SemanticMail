"""Blind LLM-as-judge for reply draft A/B comparison.

For each target, presents both drafts in RANDOMIZED order.
Judge is unaware which is COLD vs SCAFFOLDED.

Usage:
    cd email-agent
    python ablation_reply_judge.py
"""

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from llm.cache import cached_call_llm_with_usage
from deep_analysis import build_mini_thread

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
TARGETS_PATH = os.path.join(MEMORY_DIR, "reply_ablation_targets.json")
RESULTS_PATH = os.path.join(MEMORY_DIR, "reply_judge_results.json")
SEED = 123

JUDGE_SYSTEM_PROMPT = """\
You are an expert evaluator of professional email replies. You will see an incoming \
email thread and TWO draft replies labeled Draft A and Draft B. Your job is to \
evaluate each draft on specific, countable criteria.

You do NOT know which draft was generated with additional context — evaluate purely \
on the quality of the output.

## Scoring Criteria

1. **Open-ask coverage**: Count the specific requests or questions in the incoming \
email that actually require a response. Then count how many of those each draft \
addresses substantively (not just acknowledging). Report as "X of Y".

2. **Tone / face calibration** (1-5): How well does the draft's tone match the \
relationship dynamics visible in the thread? Consider formality, warmth, directness, \
and whether the draft respects face concerns. 1 = tone-deaf, 5 = perfectly calibrated.

3. **Subtext engagement** (yes/no): Does the draft show awareness of pragmatic \
subtext (indirect requests, face concerns, power dynamics, urgency signals) or \
is it a generic acknowledgement?

4. **Overall preference**: A, B, or tie.

## Output Format

Respond with valid JSON:
{
  "draft_a": {
    "n_asks_total": <int>,
    "n_asks_addressed": <int>,
    "open_ask_coverage": "X of Y asks addressed",
    "tone_calibration": <1-5>,
    "subtext_engagement": true,
    "notes": "Brief evaluation notes"
  },
  "draft_b": {
    "n_asks_total": <int>,
    "n_asks_addressed": <int>,
    "open_ask_coverage": "X of Y asks addressed",
    "tone_calibration": <1-5>,
    "subtext_engagement": true,
    "notes": "Brief evaluation notes"
  },
  "overall_preference": "A" | "B" | "tie",
  "preference_rationale": "One sentence."
}
"""


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_judge_user_prompt(thread_messages, draft_a_text, draft_b_text):
    """Format judge prompt with two drafts."""
    formatted_thread = []
    for i, msg in enumerate(thread_messages):
        formatted_thread.append(
            f"--- Email {i + 1} ---\n"
            f"From: {msg.get('from', 'Unknown')}\n"
            f"To: {msg.get('to', 'Unknown')}\n"
            f"Date: {msg.get('date', 'Unknown')}\n"
            f"Subject: {msg.get('subject', '(no subject)')}\n\n"
            f"{msg.get('body', '')}"
        )

    return (
        f"INCOMING EMAIL THREAD:\n"
        f"{chr(10).join(formatted_thread)}\n\n"
        f"DRAFT A:\n---\n{draft_a_text}\n---\n\n"
        f"DRAFT B:\n---\n{draft_b_text}\n---\n\n"
        f"Evaluate both drafts on the criteria above."
    )


def main():
    random.seed(SEED)

    print("Loading targets...")
    data = load_json(TARGETS_PATH)
    targets = data["targets"]
    print(f"  {len(targets)} targets loaded")

    emails = load_json(os.path.join(MEMORY_DIR, "emails.json"))
    triage = load_json(os.path.join(MEMORY_DIR, "triage_results.json"))

    judgments = []

    for rank, target in enumerate(targets):
        idx = target["email_idx"]
        email = emails[idx]
        sender = target["sender"]
        category = target["category"]

        print(f"\n[{rank+1}/{len(targets)}] idx={idx} from={sender} ({category})")

        # Reconstruct mini-thread
        thread_data = build_mini_thread(email, emails, triage)
        thread_messages = thread_data["messages"]

        cold_text = target["cold"]["draft"].get("draft_text", "")
        scaffolded_text = target["scaffolded"]["draft"].get("draft_text", "")

        # Randomize order
        if random.random() < 0.5:
            order = ("cold", "scaffolded")
            draft_a, draft_b = cold_text, scaffolded_text
        else:
            order = ("scaffolded", "cold")
            draft_a, draft_b = scaffolded_text, cold_text

        judge_prompt = format_judge_user_prompt(thread_messages, draft_a, draft_b)

        print("  Running blind judge...")
        judge_response, judge_usage = cached_call_llm_with_usage(
            JUDGE_SYSTEM_PROMPT, judge_prompt,
        )

        try:
            scores = json.loads(judge_response)
        except json.JSONDecodeError:
            scores = {"error": judge_response[:200]}

        # Map preference back to cold/scaffolded
        mapped_preference = "parse_error"
        if "overall_preference" in scores:
            pref = scores["overall_preference"]
            if pref == "A":
                mapped_preference = order[0]
            elif pref == "B":
                mapped_preference = order[1]
            else:
                mapped_preference = "tie"

        judgments.append({
            "email_idx": idx,
            "sender": sender,
            "category": category,
            "randomized_order": {"A": order[0], "B": order[1]},
            "scores": scores,
            "mapped_preference": mapped_preference,
            "judge_tokens": judge_usage,
        })

        print(f"  Judge: {scores.get('overall_preference', '?')} -> mapped: {mapped_preference}")

    # Save
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"judgments": judgments}, f, ensure_ascii=False, indent=2)

    # Quick aggregate
    sc_wins = sum(1 for j in judgments if j["mapped_preference"] == "scaffolded")
    cold_wins = sum(1 for j in judgments if j["mapped_preference"] == "cold")
    ties = sum(1 for j in judgments if j["mapped_preference"] == "tie")

    print(f"\n{'='*60}")
    print(f"BLIND JUDGE AGGREGATE")
    print(f"  Scaffolded wins: {sc_wins}")
    print(f"  Cold wins:       {cold_wins}")
    print(f"  Ties:            {ties}")
    print(f"  Total:           {len(judgments)}")
    print(f"Results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
