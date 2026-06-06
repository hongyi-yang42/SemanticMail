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
    python batch_cache_fill.py --live --fill-gaps  # patch missing fields only
"""

import json
import os
import sys
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

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
N_WORKERS = 8


def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _atomic_dump(obj, path):
    """Write JSON atomically: write to .tmp then rename."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _cache_read(system_prompt, user_prompt, temperature=0.3, model="deepseek-chat"):
    from llm.cache import _cache_key, _cache_path
    path = _cache_path(_cache_key(system_prompt, user_prompt, temperature, model))
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["response"]
    return None


# ---------------------------------------------------------------------------
# Full build (original mode)
# ---------------------------------------------------------------------------

def run_full(emails, triage_results, contacts, threads, existing, live):
    from sentence_transformers import SentenceTransformer
    vectors, metadata = load_index()
    emb_model = SentenceTransformer("all-MiniLM-L6-v2")

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
            _atomic_dump(existing, os.path.join(MEMORY_DIR, "simulator_cache.json"))

    # Final save
    _atomic_dump(existing, os.path.join(MEMORY_DIR, "simulator_cache.json"))

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s: {n_new} new entries, {n_cached} already cached, {n_miss} misses (no cache)")
    print(f"Output: {os.path.join(MEMORY_DIR, 'simulator_cache.json')} ({len(existing)} entries total)")


# ---------------------------------------------------------------------------
# Fill-gaps mode
# ---------------------------------------------------------------------------

def _count_fields(cache):
    """Count non-None/non-empty fields across cache entries."""
    counts = {"pic": 0, "recalled": 0, "cold_draft": 0, "scaffolded_draft": 0}
    for v in cache.values():
        if v.get("pic"):
            counts["pic"] += 1
        if v.get("recalled"):
            counts["recalled"] += 1
        if v.get("cold_draft"):
            counts["cold_draft"] += 1
        if v.get("scaffolded_draft"):
            counts["scaffolded_draft"] += 1
    return counts


def _process_gap(idx_str, cache_entry, emails, triage_results, contacts, threads,
                 vectors, metadata, emb_model, live):
    """Process a single cache entry, filling missing fields. Returns (idx_str, entry, fills_dict)."""
    fills = {}
    i = int(idx_str)
    email_dict = emails[i]
    triage = cache_entry.get("triage", {})
    risk = triage.get("risk_level", "safe")
    needs_draft = risk in ("caution", "warning", "critical")

    # --- PIC ---
    if not cache_entry.get("pic"):
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

        memory_block = cache_entry.get("memory_block", "")
        pic_user_prompt = memory_block + "\n\n" + format_subtext_user_prompt(thread_data)
        pic_raw = _cache_read(SUBTEXT_SYSTEM_PROMPT, pic_user_prompt)
        if pic_raw is None and live:
            pic_raw = cached_call_llm(SUBTEXT_SYSTEM_PROMPT, pic_user_prompt)
        if pic_raw:
            try:
                pic = json.loads(pic_raw)
                if pic:
                    cache_entry["pic"] = pic
                    fills["pic"] = True
            except json.JSONDecodeError:
                pass

    # --- Recalled ---
    if not cache_entry.get("recalled"):
        recalled = []
        if vectors is not None and emb_model is not None and i > 0:
            recalled = retrieve(
                head_tail(email_dict.get("body", "")),
                vectors[:i], metadata[:i], emb_model, k=3,
            )
        if recalled:
            cache_entry["recalled"] = [
                {
                    "from": r.get("from", ""),
                    "date_iso": r.get("date_iso", ""),
                    "snippet": r.get("snippet", ""),
                    "norm_subject": r.get("norm_subject", ""),
                    "idx": r.get("idx", 0),
                    "score": r.get("score", 0),
                }
                for r in recalled
            ]
            fills["recalled"] = True

    # --- Drafts (non-safe only) ---
    if needs_draft:
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
        msgs = thread_data["messages"]

        # Cold draft
        if not cache_entry.get("cold_draft"):
            cold_prompt = format_reply_user_prompt(msgs)
            cold_raw = _cache_read(REPLY_SYSTEM_PROMPT, cold_prompt)
            if cold_raw is None and live:
                cold_raw = cached_call_llm(REPLY_SYSTEM_PROMPT, cold_prompt)
            if cold_raw:
                try:
                    cold = json.loads(cold_raw)
                except json.JSONDecodeError:
                    cold = {"draft_text": cold_raw, "rationale": "(parse error)"}
                if cold:
                    cache_entry["cold_draft"] = cold
                    fills["cold_draft"] = True

        # Scaffolded draft
        if not cache_entry.get("scaffolded_draft") and cache_entry.get("pic"):
            pic = cache_entry["pic"]
            memory_block = cache_entry.get("memory_block", "")
            scaffold = (
                "--- PRAGMATIC INFERENCE CHAIN ANALYSIS ---\n"
                + json.dumps(pic, indent=2)
                + "\n\n--- RELATIONSHIP & THREAD CONTEXT ---\n"
                + memory_block
            )
            scaffold_prompt = format_reply_user_prompt(msgs, scaffold=scaffold)
            scaffold_raw = _cache_read(REPLY_SYSTEM_PROMPT, scaffold_prompt)
            if scaffold_raw is None and live:
                scaffold_raw = cached_call_llm(REPLY_SYSTEM_PROMPT, scaffold_prompt)
            if scaffold_raw:
                try:
                    scaffolded = json.loads(scaffold_raw)
                except json.JSONDecodeError:
                    scaffolded = {"draft_text": scaffold_raw, "rationale": "(parse error)"}
                if scaffolded:
                    cache_entry["scaffolded_draft"] = scaffolded
                    fills["scaffolded_draft"] = True

    return idx_str, cache_entry, fills


def run_fill_gaps(emails, triage_results, contacts, threads, cache, live):
    """Detect and fill missing fields across the cache. 8 parallel workers."""
    from sentence_transformers import SentenceTransformer

    vectors, metadata = load_index()
    emb_model = SentenceTransformer("all-MiniLM-L6-v2")

    before = _count_fields(cache)
    total = len(cache)

    # Identify entries needing work
    tasks = []
    for idx_str, entry in cache.items():
        triage = entry.get("triage", {})
        risk = triage.get("risk_level", "safe")
        needs_draft = risk in ("caution", "warning", "critical")
        has_gaps = (
            not entry.get("pic")
            or not entry.get("recalled")
            or (needs_draft and not entry.get("cold_draft"))
            or (needs_draft and not entry.get("scaffolded_draft") and entry.get("pic"))
        )
        if has_gaps:
            tasks.append(idx_str)

    print(f"Cache: {total} entries, {len(tasks)} with gaps to fill")
    print(f"Before: PIC={before['pic']}  Recalled={before['recalled']}  "
          f"Cold={before['cold_draft']}  Scaffolded={before['scaffolded_draft']}")
    print(f"Workers: {N_WORKERS}, live={live}")
    print()

    t0 = time.time()
    fills_summary = {"pic": 0, "recalled": 0, "cold_draft": 0, "scaffolded_draft": 0}
    completed = 0

    with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        futures = {
            pool.submit(
                _process_gap, idx_str, cache[idx_str], emails, triage_results,
                contacts, threads, vectors, metadata, emb_model, live,
            ): idx_str
            for idx_str in tasks
        }

        for future in as_completed(futures):
            idx_str = future.result()[0]
            try:
                idx_str, updated_entry, fills = future.result()
                cache[idx_str] = updated_entry
                for k in fills:
                    fills_summary[k] += 1
                completed += 1
                if completed % 5 == 0 or completed == len(tasks):
                    elapsed = time.time() - t0
                    print(f"  [{completed}/{len(tasks)}] "
                          f"PIC +{fills_summary['pic']}  Recalled +{fills_summary['recalled']}  "
                          f"Cold +{fills_summary['cold_draft']}  Scaffolded +{fills_summary['scaffolded_draft']}  "
                          f"({elapsed:.0f}s)")
            except Exception as e:
                print(f"  ERROR idx={idx_str}: {e}")
                completed += 1

    # Atomic save
    cache_path = os.path.join(MEMORY_DIR, "simulator_cache.json")
    _atomic_dump(cache, cache_path)

    after = _count_fields(cache)
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s")
    print(f"Delta:")
    print(f"  PIC:               {before['pic']:>4} → {after['pic']:>4}  (+{after['pic'] - before['pic']})")
    print(f"  Recalled:          {before['recalled']:>4} → {after['recalled']:>4}  (+{after['recalled'] - before['recalled']})")
    print(f"  Cold drafts:       {before['cold_draft']:>4} → {after['cold_draft']:>4}  (+{after['cold_draft'] - before['cold_draft']})")
    print(f"  Scaffolded drafts: {before['scaffolded_draft']:>4} → {after['scaffolded_draft']:>4}  (+{after['scaffolded_draft'] - before['scaffolded_draft']})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    live = "--live" in args
    fill_gaps = "--fill-gaps" in args

    emails = _load_json(os.path.join(MEMORY_DIR, "emails.json"))
    triage_results = _load_json(os.path.join(MEMORY_DIR, "triage_results.json"))
    contacts = _load_json(os.path.join(MEMORY_DIR, "contacts.json"))
    threads = _load_json(os.path.join(MEMORY_DIR, "threads.json"))

    if not emails:
        print("ERROR: memory/emails.json not found. Run enron_load.py first.")
        sys.exit(1)

    cache_path = os.path.join(MEMORY_DIR, "simulator_cache.json")
    existing = _load_json(cache_path) or {}

    if fill_gaps:
        run_fill_gaps(emails, triage_results, contacts, threads, existing, live)
    else:
        run_full(emails, triage_results, contacts, threads, existing, live)


if __name__ == "__main__":
    main()
