"""Warm cache for GPT-OSS 20B baseline module via OpenRouter."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from data.threads import get_thread_display_names, get_thread_by_name
from llm.cache import cached_call_baseline_llm
from prompts.baseline_gptoss import (
    BASELINE_GPTOSS_SYSTEM_PROMPT,
    format_baseline_gptoss_user_prompt,
)

if not os.environ.get("OPENROUTER_API_KEY"):
    print("ERROR: OPENROUTER_API_KEY not set.")
    sys.exit(1)

print(
    f"Warming baseline cache for {len(get_thread_display_names())} threads "
    f"(GPT-OSS 20B via OpenRouter)..."
)

for name in get_thread_display_names():
    thread = get_thread_by_name(name)
    user_prompt = format_baseline_gptoss_user_prompt(thread)
    print(f"\n=== {name} ===")
    print("  baseline_gptoss...", end=" ", flush=True)
    try:
        result = cached_call_baseline_llm(
            BASELINE_GPTOSS_SYSTEM_PROMPT, user_prompt, temperature=0.3
        )
        print(f"OK ({len(result)} chars)")
    except Exception as e:
        print(f"FAILED: {e}")

import glob

cache_files = glob.glob(
    os.path.join(os.path.dirname(__file__), "data", "cache", "*.json")
)
print(f"\nDone! Total cache files: {len(cache_files)}")
