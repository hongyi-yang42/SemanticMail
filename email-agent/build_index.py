"""Build local embedding index from parsed Enron emails.

Usage:
    cd email-agent
    python build_index.py

Uses sentence-transformers all-MiniLM-L6-v2 (offline after first download).
Embeds ~1000 chars per email (head+tail) to capture sign-off pragmatics.
Persists vectors + metadata to memory/index.pkl.
"""

import json
import os
import pickle
import sys

import numpy as np

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_CHARS = 1000  # head+tail budget


def head_tail(text: str, budget: int = EMBED_CHARS) -> str:
    """Take first half and last quarter of text, within budget.
    Sign-offs carry pragmatic signal and shouldn't be truncated."""
    if len(text) <= budget:
        return text
    head = budget // 2
    tail = budget // 4
    return text[:head] + "\n...\n" + text[-tail:]


def load_emails(path: str = None) -> list[dict]:
    if path is None:
        path = os.path.join(MEMORY_DIR, "emails.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def embed_emails(emails: list[dict], model) -> tuple[np.ndarray, list[dict]]:
    """Embed each email body (head+tail truncated).
    Returns (vectors [N, 384], metadata list)."""
    texts = [head_tail(e.get("body", "")) for e in emails]
    vectors = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    metadata = []
    for i, e in enumerate(emails):
        metadata.append({
            "idx": i,
            "message_id": e.get("message_id", ""),
            "date_iso": e.get("date_iso", ""),
            "norm_subject": e.get("norm_subject", ""),
            "from": e.get("from", ""),
            "snippet": e.get("body", "")[:120].replace("\n", " "),
        })

    return np.array(vectors), metadata


def save_index(vectors: np.ndarray, metadata: list[dict], path: str = None):
    if path is None:
        path = os.path.join(MEMORY_DIR, "index.pkl")
    with open(path, "wb") as f:
        pickle.dump({"model_name": MODEL_NAME, "vectors": vectors, "metadata": metadata}, f)
    print(f"Saved index to {path} ({vectors.shape[0]} vectors, {vectors.shape[1]} dims)")


def load_index(path: str = None) -> tuple[np.ndarray, list[dict]]:
    if path is None:
        path = os.path.join(MEMORY_DIR, "index.pkl")
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["vectors"], data["metadata"]


def retrieve(query_text: str, vectors: np.ndarray, metadata: list[dict],
             model, before_idx: int | None = None, k: int = 3) -> list[dict]:
    """Find top-k most similar emails by cosine similarity.

    Args:
        query_text: Text to search for.
        vectors: Embedding matrix [N, 384].
        metadata: Per-email metadata list.
        model: SentenceTransformer model for encoding query.
        before_idx: If set, only consider emails with idx < before_idx.
        k: Number of results.

    Returns:
        List of {rank, score, idx, date_iso, from, subject, snippet}.
    """
    q_vec = model.encode([query_text], normalize_embeddings=True)[0]

    # Compute scores
    if before_idx is not None:
        mask = np.array([m["idx"] < before_idx for m in metadata])
        if not mask.any():
            return []
        scores = vectors @ q_vec
        scores[~mask] = -np.inf
    else:
        scores = vectors @ q_vec

    top_k = min(k, len(scores))
    top_indices = np.argsort(scores)[-top_k:][::-1]

    results = []
    for rank, idx in enumerate(top_indices):
        if scores[idx] == -np.inf:
            break
        m = metadata[idx]
        results.append({
            "rank": rank + 1,
            "score": float(scores[idx]),
            "idx": int(m["idx"]),
            "date_iso": m["date_iso"],
            "from": m["from"],
            "subject": m["norm_subject"],
            "snippet": m["snippet"],
        })
    return results


def main():
    from sentence_transformers import SentenceTransformer

    print(f"Loading model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    print("Loading emails...")
    emails = load_emails()
    print(f"  {len(emails)} emails loaded")

    print("Embedding emails (head+tail, ~1000 chars each)...")
    vectors, metadata = embed_emails(emails, model)

    save_index(vectors, metadata)

    # Quick test: retrieve for last email
    print("\nQuick retrieval test (last email, k=3):")
    results = retrieve(
        head_tail(emails[-1].get("body", "")),
        vectors, metadata, model,
        before_idx=len(emails) - 1, k=3,
    )
    for r in results:
        print(f"  {r['rank']}. [{r['date_iso'][:10]}] {r['from']}: "
              f"{r['snippet'][:80]}... (score={r['score']:.3f})")


if __name__ == "__main__":
    main()
