"""Self-consistency: regenerate drafts at higher temperature, measure variance.

Hypothesis: scaffold lowers output variance.

Generates 3x COLD and 3x SCAFFOLDED drafts per target at temps 0.5/0.7/0.9,
embeds each, computes pairwise cosine spread.

Usage:
    cd email-agent
    python self_consistency.py
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from llm.cache import cached_call_llm_with_usage
from prompts.reply import REPLY_SYSTEM_PROMPT, format_reply_user_prompt

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
TARGETS_PATH = os.path.join(MEMORY_DIR, "reply_ablation_targets.json")
RESULTS_PATH = os.path.join(MEMORY_DIR, "self_consistency_results.json")
TEMPS = [0.5, 0.7, 0.9]


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cosine_spread(embeddings):
    """Mean pairwise cosine distance (1 - similarity) among embeddings."""
    n = len(embeddings)
    if n < 2:
        return 0.0
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            sim = np.dot(embeddings[i], embeddings[j]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j]) + 1e-9
            )
            total += 1 - sim
            count += 1
    return float(total / count)


def main():
    from sentence_transformers import SentenceTransformer
    from build_index import load_index

    # Load model and index (we only need the embedding model, not the index)
    emb_model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Loading targets...")
    with open(TARGETS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    targets = data["targets"]

    results = []

    for rank, target in enumerate(targets):
        idx = target["email_idx"]
        sender = target["sender"]

        print(f"\n[{rank+1}/{len(targets)}] idx={idx} from={sender}")

        # Rebuild prompts (same as draft_reply.py)
        scaffold_text = ""
        pic = target["scaffolded"].get("pic_analysis", "")
        mem = target["scaffolded"].get("memory_block", "")
        if pic and mem:
            scaffold_text = (
                f"--- PRAGMATIC INFERENCE CHAIN ANALYSIS ---\n{pic}\n\n"
                f"--- RELATIONSHIP & THREAD CONTEXT ---\n{mem}"
            )

        # We need the thread_messages — reconstruct from target's email
        # The draft_reply.py output includes enough to rebuild prompts
        # For cold prompt, we use the cold user prompt structure
        # We'll extract it by reconstructing from the scaffolded data

        # Actually, we need thread_messages. Let's load the original emails.
        emails = load_json(os.path.join(MEMORY_DIR, "emails.json"))
        triage = load_json(os.path.join(MEMORY_DIR, "triage_results.json"))
        from deep_analysis import build_mini_thread
        email = emails[idx]
        thread_data = build_mini_thread(email, emails, triage)
        thread_messages = thread_data["messages"]

        cold_user = format_reply_user_prompt(thread_messages)
        scaffolded_user = format_reply_user_prompt(thread_messages, scaffold=scaffold_text)

        cold_replicas = []
        scaffolded_replicas = []

        for rep, temp in enumerate(TEMPS):
            print(f"  Replica {rep+1}/{len(TEMPS)} (temp={temp})...")

            cold_resp, _ = cached_call_llm_with_usage(
                REPLY_SYSTEM_PROMPT, cold_user, temperature=temp,
            )
            try:
                cold_draft = json.loads(cold_resp).get("draft_text", cold_resp)
            except json.JSONDecodeError:
                cold_draft = cold_resp
            cold_replicas.append(cold_draft)

            sc_resp, _ = cached_call_llm_with_usage(
                REPLY_SYSTEM_PROMPT, scaffolded_user, temperature=temp,
            )
            try:
                sc_draft = json.loads(sc_resp).get("draft_text", sc_resp)
            except json.JSONDecodeError:
                sc_draft = sc_resp
            scaffolded_replicas.append(sc_draft)

        # Embed all replicas
        cold_emb = emb_model.encode(cold_replicas, normalize_embeddings=True)
        sc_emb = emb_model.encode(scaffolded_replicas, normalize_embeddings=True)

        cold_spread = cosine_spread(cold_emb)
        sc_spread = cosine_spread(sc_emb)

        print(f"  Cold spread:      {cold_spread:.4f}")
        print(f"  Scaffolded spread: {sc_spread:.4f}")

        results.append({
            "email_idx": idx,
            "sender": sender,
            "cold_spread": cold_spread,
            "scaffolded_spread": sc_spread,
            "temperatures": TEMPS,
        })

    # Aggregate
    avg_cold = np.mean([r["cold_spread"] for r in results])
    avg_sc = np.mean([r["scaffolded_spread"] for r in results])

    output = {
        "results": results,
        "aggregate": {
            "mean_cold_spread": float(avg_cold),
            "mean_scaffolded_spread": float(avg_sc),
            "delta": float(avg_cold - avg_sc),
            "hypothesis_supported": bool(avg_sc < avg_cold),
        },
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"SELF-CONSISTENCY RESULTS")
    print(f"  Mean cold spread:       {avg_cold:.4f}")
    print(f"  Mean scaffolded spread: {avg_sc:.4f}")
    print(f"  Delta (cold - sc):      {avg_cold - avg_sc:+.4f}")
    label = "SUPPORTED" if avg_sc < avg_cold else "NOT SUPPORTED"
    print(f"  Hypothesis (sc lowers variance): {label}")
    print(f"Saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
