"""Ablation cache warmer — runs 3 conditions across all threads.

Conditions:
  A  full_pic      — Full PIC prompt (subtext.py)
  B  generic       — Generic "analyze subtext" (ablation.py)
  C  no_analysis   — No analysis framing (ablation.py)

All use DeepSeek V4-Flash (deepseek-chat) via the official API.
Only threads with non-empty messages are included.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from data.threads import THREAD_MAP
from llm.cache import cached_call_llm
from prompts.ablation import (
    ABLATION_SYSTEM_PROMPT,
    NO_ANALYSIS_SYSTEM_PROMPT,
    format_ablation_user_prompt,
    format_no_analysis_user_prompt,
)
from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt

MODEL = "deepseek-chat"  # routes to V4-Flash

CONDITIONS = [
    ("A_full_pic", SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt),
    ("B_generic", ABLATION_SYSTEM_PROMPT, format_ablation_user_prompt),
    ("C_no_analysis", NO_ANALYSIS_SYSTEM_PROMPT, format_no_analysis_user_prompt),
]


def main():
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("ERROR: DEEPSEEK_API_KEY not set.")
        sys.exit(1)

    # Filter to threads that have actual messages
    threads_with_content = {
        name: t for name, t in THREAD_MAP.items() if t.get("messages")
    }

    print(
        f"Ablation: {len(threads_with_content)} threads x {len(CONDITIONS)} conditions "
        f"= {len(threads_with_content) * len(CONDITIONS)} calls"
    )
    print(f"Model: {MODEL}\n")

    results = []
    for name, thread in threads_with_content.items():
        print(f"=== {name} ===")
        for cond_name, sys_prompt, fmt_fn in CONDITIONS:
            label = f"  {cond_name}..."
            print(label, end=" ", flush=True)
            try:
                result = cached_call_llm(
                    sys_prompt, fmt_fn(thread), temperature=0.3, model=MODEL
                )
                print(f"OK ({len(result)} chars)")
                results.append((name, cond_name, "ok", len(result)))
            except Exception as e:
                print(f"FAILED: {e}")
                results.append((name, cond_name, "failed", str(e)))

    print(f"\n{'='*60}")
    ok = sum(1 for _, _, s, _ in results if s == "ok")
    failed = sum(1 for _, _, s, _ in results if s == "failed")
    print(f"Done: {ok} OK, {failed} failed out of {len(results)} total")

    if failed:
        print("\nFailures:")
        for name, cond, status, detail in results:
            if status == "failed":
                print(f"  {name} / {cond}: {detail}")


if __name__ == "__main__":
    # Opt this script into live LLM calls. Set inside __main__ so that
    # importing this module from elsewhere does not silently authorize
    # billable calls.
    os.environ.setdefault("SEMANTICMAIL_RUNTIME", "cli_warmer")
    main()
