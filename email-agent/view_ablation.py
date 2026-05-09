"""Ablation results viewer — side-by-side comparison of 3 conditions.

Loads cached ablation results and prints a comparison table showing
how each condition analyzed each thread.

Usage:
    cd email-agent
    python view_ablation.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from llm.cache import _cache_key
from prompts.ablation import (
    ABLATION_SYSTEM_PROMPT,
    NO_ANALYSIS_SYSTEM_PROMPT,
    format_ablation_user_prompt,
    format_no_analysis_user_prompt,
)
from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt
from data.threads import THREAD_MAP

MODEL = "deepseek-chat"

CONDITIONS = [
    ("A_full_pic", SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt),
    ("B_generic", ABLATION_SYSTEM_PROMPT, format_ablation_user_prompt),
    ("C_no_analysis", NO_ANALYSIS_SYSTEM_PROMPT, format_no_analysis_user_prompt),
]

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data", "cache")


def load_result(sys_prompt, fmt_fn, thread):
    """Load a cached result, returning parsed JSON or None."""
    user_prompt = fmt_fn(thread)
    key = _cache_key(sys_prompt, user_prompt, 0.3, MODEL)
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    text = raw.get("response", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}


def extract_signals(analysis):
    """Extract key fields from a parsed analysis for comparison."""
    if not analysis or "_raw" in analysis:
        return {"risk": "N/A", "tones": "N/A", "signals": 0, "has_inference": False}

    thread_level = analysis.get("thread_level", {})
    per_email = analysis.get("per_email_analysis", [])

    risk = thread_level.get("overall_risk", "N/A")
    tones = thread_level.get("tone_trajectory", [])
    tones_str = " → ".join(tones) if tones else "N/A"

    signal_count = 0
    has_inference = False
    for email in per_email:
        pi = email.get("pragmatic_inference", {})
        signal_count += len(pi.get("gricean_violations", []))
        signal_count += len(pi.get("indirect_speech_acts", []))
        if pi.get("implicature") and pi["implicature"].strip():
            has_inference = True

    return {
        "risk": risk,
        "tones": tones_str,
        "signals": signal_count,
        "has_inference": has_inference,
    }


def main():
    threads_with_content = {
        name: t for name, t in THREAD_MAP.items() if t.get("messages")
    }

    if not threads_with_content:
        print("No threads with messages found. Write email content first.")
        return

    print(f"{'Thread':<30} {'Cond':<15} {'Risk':<10} {'Signals':<8} {'Inference':<10} {'Tone Trajectory'}")
    print("-" * 120)

    for name in threads_with_content:
        thread = threads_with_content[name]
        short_name = name.split(":")[1].strip() if ":" in name else name
        short_name = short_name[:28]

        for cond_name, sys_prompt, fmt_fn in CONDITIONS:
            analysis = load_result(sys_prompt, fmt_fn, thread)
            info = extract_signals(analysis)

            if info["risk"] == "N/A" and analysis is None:
                cond_label = f"{cond_name} (missing)"
            else:
                cond_label = cond_name

            print(
                f"{short_name:<30} {cond_label:<15} {info['risk']:<10} "
                f"{info['signals']:<8} {'Yes' if info['has_inference'] else 'No':<10} "
                f"{info['tones']}"
            )
        print()

    # Summary: count completed vs missing
    total = len(threads_with_content) * len(CONDITIONS)
    loaded = 0
    for name, thread in threads_with_content.items():
        for _, sys_prompt, fmt_fn in CONDITIONS:
            result = load_result(sys_prompt, fmt_fn, thread)
            if result is not None:
                loaded += 1

    print(f"\nCache status: {loaded}/{total} results loaded")
    if loaded < total:
        print(f"Run warm_cache_ablation.py to generate missing results.")


if __name__ == "__main__":
    main()
