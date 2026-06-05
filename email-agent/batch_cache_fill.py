#!/usr/bin/env python3
"""Batch-fill PIC + draft cache for all 400 emails.

Produces memory/simulator_cache.json keyed by email index:
{
  "0": {"triage": {...}, "pic": {...}, "memory_block": "...",
        "cold_draft": {...}, "scaffolded_draft": {...},
        "recalled": [...]},
  ...
}

Usage:
    cd email-agent
    python batch_cache_fill.py              # cache-only (no live calls)
    python batch_cache_fill.py --live       # allow live LLM on cache misses
"""

import json
import os
import sys
import time

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from llm.cache import cached_call_llm
from prompts.triage import TRIAGE_SYSTEM_PROMPT, TRIAGE_USER_TEMPLATE
from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt
from prompts.reply import REPLY_SYSTEM_PROMPT, format_reply_user_prompt
from prompts.memory_context import build_memory_context_block
from triage_pass import format_triage_prompt, parse_triage_json
from build_index import load_index, retrieve, head_tail
from deep_analysis import build_mini_thread

MEMORY_DIR = os.path.join(AGENT_DIR, "memory")


def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    live = "--live" in sys.argv
    emails = _load_json(os.path.join(MEMORY_DIR, "emails.json"))
    triage_results = _load_json(os.path.join(MEMORY_DIR, "triage_results.json"))
    contacts = _load_json(os.path.join(MEMORY_DIR, "contacts.json"))
    threads = _load_json(os.path.join(MEMORY_DIR, "threads.json"))

    from sentence_transformers import SentenceTransformer
    vectors, metadata = load_index()
    emb_model = SentenceTransformer("all-MiniLM-L6-v2")

    cache_path = os.path.join(MEMORY_DIR, "simulator_cache.json")
    existing = _load_json(cache_path) or {}

    n_total = len(emails)
    n_cached = 0
    n_new = 0
    n_miss = 0
    t0 = time.time()

    for i, email_dict in enumerate(emails):
        key = str(i)
        if key in existing:
            n_cached += 1
            continue

        triage = triage_results[i] if i < len(triage_results) else {}

        # Build thread
        thread_data = build_mini_thread(email_dict, emails, triage_results)
        new_body = email_dict.get("body", "")
        already_in = any(m.get("body", "") == new_body for m in thread_data["messages"])
        if not already_in:
            thread_data["messages"].append({
                "from":    email_dict.get("from", "Unknown"),
                "to":      email_dict.get("to", "Unknown"),
                "cc":      email_dict.get("cc", ""),
                "date":    email_dict.get("date", ""),
                "subject": email_dict.get("subject", ""),
                "body":    new_body,
            })
        thread_data["title"] = email_dict.get("subject", "Single Email Analysis")

        # Memory recall
        recalled = []
        if vectors is not None and emb_model is not None and i > 0:
            recalled = retrieve(
                head_tail(email_dict.get("body", "")),
                vectors[:i], metadata[:i], emb_model, k=3,
            )

        memory_block = build_memory_context_block(
            sender=email_dict.get("from", "Unknown"),
            email_idx=i,
            date_iso=email_dict.get("date_iso", ""),
            contacts=contacts,
            thread_key=email_dict.get("norm_subject", ""),
            threads=threads,
            recalled_emails=recalled,
            triage_results=triage_results,
        )

        # PIC analysis
        pic_user_prompt = memory_block + "\n\n" + format_subtext_user_prompt(thread_data)
        pic = None
        pic_raw = _cache_read(SUBTEXT_SYSTEM_PROMPT, pic_user_prompt)
        if pic_raw is not None:
            try:
                pic = json.loads(pic_raw)
            except json.JSONDecodeError:
                pass
        elif live:
            pic_raw = cached_call_llm(SUBTEXT_SYSTEM_PROMPT, pic_user_prompt)
            if pic_raw:
                try:
                    pic = json.loads(pic_raw)
                except json.JSONDecodeError:
                    pass

        # Drafts
        msgs = thread_data["messages"]
        cold = None
        scaffolded = None

        cold_raw = _cache_read(REPLY_SYSTEM_PROMPT, format_reply_user_prompt(msgs))
        if cold_raw is not None:
            try:
                cold = json.loads(cold_raw)
            except json.JSONDecodeError:
                cold = {"draft_text": cold_raw, "rationale": "(parse error)"}

        if pic:
            scaffold = (
                "--- PRAGMATIC INFERENCE CHAIN ANALYSIS ---\n"
                + json.dumps(pic, indent=2)
                + "\n\n--- RELATIONSHIP & THREAD CONTEXT ---\n"
                + memory_block
            )
            scaffold_prompt = format_reply_user_prompt(msgs, scaffold=scaffold)
            scaffold_raw = _cache_read(REPLY_SYSTEM_PROMPT, scaffold_prompt)
            if scaffold_raw is not None:
                try:
                    scaffolded = json.loads(scaffold_raw)
                except json.JSONDecodeError:
                    scaffolded = {"draft_text": scaffold_raw, "rationale": "(parse error)"}

        if pic is None and cold is None and scaffolded is None:
            n_miss += 1
            continue

        entry = {
            "triage": triage,
            "pic": pic,
            "memory_block": memory_block,
            "cold_draft": cold,
            "scaffolded_draft": scaffolded,
            "recalled": [
                {
                    "from": r.get("from", ""),
                    "date_iso": r.get("date_iso", ""),
                    "snippet": r.get("snippet", ""),
                    "norm_subject": r.get("norm_subject", ""),
                    "idx": r.get("idx", 0),
                    "score": r.get("score", 0),
                }
                for r in recalled
            ],
        }
        existing[key] = entry
        n_new += 1

        if n_new % 5 == 0:
            elapsed = time.time() - t0
            print(f"[{i+1}/{n_total}] {n_new} new, {n_cached} cached, {n_miss} miss — {elapsed:.0f}s")
            # Incremental save every 5 new entries
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=1)

    # Final save
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=1)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s: {n_new} new entries, {n_cached} already cached, {n_miss} misses (no cache)")
    print(f"Output: {cache_path} ({len(existing)} entries total)")


def _cache_read(system_prompt, user_prompt, temperature=0.3, model="deepseek-chat"):
    from llm.cache import _cache_key, _cache_path
    path = _cache_path(_cache_key(system_prompt, user_prompt, temperature, model))
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["response"]
    return None


if __name__ == "__main__":
    main()
