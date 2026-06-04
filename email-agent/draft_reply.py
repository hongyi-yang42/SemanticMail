"""Draft reply A/B: COLD (mini-thread only) vs SCAFFOLDED (mini-thread + PIC + memory).

Usage:
    cd email-agent
    python draft_reply.py

Selects ~8 target emails (6 request-with-asks + 2 face-sensitive).
For each, generates both conditions with token tracking.
Results saved to memory/reply_ablation_targets.json.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from llm.cache import cached_call_llm, cached_call_llm_with_usage
from prompts.reply import REPLY_SYSTEM_PROMPT, format_reply_user_prompt
from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt
from prompts.memory_context import build_memory_context_block
from deep_analysis import build_mini_thread

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
RISK_ORDER = {"safe": 0, "caution": 1, "warning": 2, "critical": 3}
TONE_ORDER = {
    "enthusiastic": 0, "warm": 1, "neutral": 2,
    "cool": 3, "evasive": 4, "hostile": 5,
}
OUTPUT_PATH = os.path.join(MEMORY_DIR, "reply_ablation_targets.json")
N_REQUEST = 6
N_FACE = 2


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_targets(emails, contacts, triage, n_request=N_REQUEST, n_face=N_FACE):
    """Select ~8 targets: n_request request-with-asks + n_face face-sensitive."""
    flagged = []
    for i, t in enumerate(triage):
        risk = t.get("risk_level", "safe")
        if RISK_ORDER.get(risk, 0) >= 1:
            flagged.append(i)

    # --- Group 1: Request with asks ---
    request_candidates = []
    for i in flagged:
        sender = emails[i].get("from", "")
        contact = contacts.get(sender, {})
        t = triage[i]
        asks = t.get("open_asks", [])
        n_int = contact.get("n_interactions", 0)

        if n_int >= 5 and len(asks) > 0:
            score = n_int * 10 + RISK_ORDER.get(t.get("risk_level", "safe"), 0) * 5
            if "Mara" in sender:
                score += 100  # flagship bonus
            request_candidates.append((score, i))

    request_candidates.sort(key=lambda x: -x[0])
    request_picks = [idx for _, idx in request_candidates[:n_request]]

    # --- Group 2: Face-sensitive (cooling tone or high risk) ---
    used = set(request_picks)
    face_candidates = []
    for i in flagged:
        if i in used:
            continue
        sender = emails[i].get("from", "")
        contact = contacts.get(sender, {})
        t = triage[i]
        n_int = contact.get("n_interactions", 0)
        tones = contact.get("tone_labels", [])

        has_cooling = False
        if len(tones) >= 3:
            mid = len(tones) // 2
            early_avg = sum(TONE_ORDER.get(t, 2) for t in tones[:mid]) / max(mid, 1)
            late_avg = sum(TONE_ORDER.get(t, 2) for t in tones[mid:]) / max(len(tones) - mid, 1)
            if late_avg > early_avg + 0.5:
                has_cooling = True

        risk = RISK_ORDER.get(t.get("risk_level", "safe"), 0)
        if (has_cooling or risk >= 2) and n_int >= 3:
            score = int(has_cooling) * 50 + risk * 10 + n_int
            face_candidates.append((score, i))

    face_candidates.sort(key=lambda x: -x[0])
    face_picks = [idx for _, idx in face_candidates[:n_face]]

    picks = request_picks + face_picks
    cats = ["request_with_asks"] * len(request_picks) + ["face_sensitive"] * len(face_picks)
    return list(zip(picks, cats))


def main():
    print("Loading data...")
    emails = load_json(os.path.join(MEMORY_DIR, "emails.json"))
    contacts = load_json(os.path.join(MEMORY_DIR, "contacts.json"))
    threads = load_json(os.path.join(MEMORY_DIR, "threads.json"))
    triage = load_json(os.path.join(MEMORY_DIR, "triage_results.json"))

    try:
        from build_index import load_index, retrieve, head_tail
        from sentence_transformers import SentenceTransformer
        vectors, metadata = load_index()
        emb_model = SentenceTransformer("all-MiniLM-L6-v2")
        has_index = True
        print("Embedding index loaded.")
    except Exception as e:
        print(f"Embedding index not available ({e})")
        has_index = False

    targets = select_targets(emails, contacts, triage)
    print(f"\nSelected {len(targets)} targets:")
    for idx, cat in targets:
        sender = emails[idx].get("from", "Unknown")
        subj = emails[idx].get("subject", "")[:60]
        print(f"  [{cat}] idx={idx} from={sender} subj={subj}...")

    results = []

    for rank, (idx, category) in enumerate(targets):
        email = emails[idx]
        sender = email.get("from", "Unknown")
        date_iso = email.get("date_iso", "")
        norm_subj = email.get("norm_subject", "")
        triage_entry = triage[idx] if idx < len(triage) else {}

        print(f"\n[{rank+1}/{len(targets)}] idx={idx} category={category}")
        print(f"  From: {sender}")
        print(f"  Subject: {email.get('subject', '')[:80]}")

        # Build mini-thread (both conditions see the same raw content)
        thread_data = build_mini_thread(email, emails, triage)
        thread_messages = thread_data["messages"]

        # Retrieve related past emails
        recalled = []
        if has_index:
            recalled = retrieve(
                head_tail(email.get("body", "")),
                vectors, metadata, emb_model,
                before_idx=idx, k=3,
            )

        # Build memory context block
        memory_block = build_memory_context_block(
            sender=sender,
            email_idx=idx,
            date_iso=date_iso,
            contacts=contacts,
            thread_key=norm_subj,
            threads=threads,
            recalled_emails=recalled,
            triage_results=triage,
        )

        # Get PIC analysis (cache hit from deep_analysis.py run)
        pic_user_prompt = memory_block + "\n\n" + format_subtext_user_prompt(thread_data)
        pic_result = cached_call_llm(SUBTEXT_SYSTEM_PROMPT, pic_user_prompt)

        # Build scaffold
        scaffold = (
            f"--- PRAGMATIC INFERENCE CHAIN ANALYSIS ---\n"
            f"{pic_result}\n\n"
            f"--- RELATIONSHIP & THREAD CONTEXT ---\n"
            f"{memory_block}"
        )

        # --- COLD: mini-thread only ---
        print("  Generating COLD draft...")
        cold_user_prompt = format_reply_user_prompt(thread_messages)
        cold_response, cold_usage = cached_call_llm_with_usage(
            REPLY_SYSTEM_PROMPT, cold_user_prompt,
        )

        # --- SCAFFOLDED: mini-thread + scaffold ---
        print("  Generating SCAFFOLDED draft...")
        scaffolded_user_prompt = format_reply_user_prompt(thread_messages, scaffold=scaffold)
        scaffolded_response, scaffolded_usage = cached_call_llm_with_usage(
            REPLY_SYSTEM_PROMPT, scaffolded_user_prompt,
        )

        # Parse drafts
        cold_draft = _parse_draft(cold_response)
        scaffolded_draft = _parse_draft(scaffolded_response)

        results.append({
            "email_idx": idx,
            "category": category,
            "sender": sender,
            "date_iso": date_iso,
            "subject": email.get("subject", ""),
            "triage": triage_entry,
            "open_asks": triage_entry.get("open_asks", []),
            "cold": {
                "draft": cold_draft,
                "tokens": cold_usage,
            },
            "scaffolded": {
                "draft": scaffolded_draft,
                "tokens": scaffolded_usage,
                "pic_analysis": pic_result,
                "memory_block": memory_block,
            },
        })

        print(f"  COLD:       {cold_usage['source']} in={cold_usage['prompt_tokens']} "
              f"out={cold_usage['completion_tokens']}")
        print(f"  SCAFFOLDED: {scaffolded_usage['source']} in={scaffolded_usage['prompt_tokens']} "
              f"out={scaffolded_usage['completion_tokens']}")

    output = {"targets": results}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    n_req = sum(1 for r in results if r["category"] == "request_with_asks")
    n_face = sum(1 for r in results if r["category"] == "face_sensitive")
    print(f"\n{'='*60}")
    print(f"Results saved to {OUTPUT_PATH}")
    print(f"  Targets: {len(results)} ({n_req} request, {n_face} face-sensitive)")


def _parse_draft(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"draft_text": raw, "rationale": "(parse error)"}


if __name__ == "__main__":
    main()
