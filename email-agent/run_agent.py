#!/usr/bin/env python3
"""SemanticMail Agent CLI — single-command end-to-end email analysis.

Usage:
    python run_agent.py email.eml                     # analyze a .eml file
    python run_agent.py inbox.mbox                    # analyze all emails in mbox
    python run_agent.py --text                        # paste raw email (Ctrl-D)
    python run_agent.py email.eml --live              # allow live LLM on miss
    python run_agent.py email.eml --no-deidentify     # skip PII scrubbing

Offline-first: reads from cache by default. --live allows live LLM on misses.
"""

import argparse
import email
import email.utils
import hashlib
import json
import mailbox
import os
import pickle
import sys
import tempfile

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from llm.cache import _cache_key, _cache_path
from prompts.triage import TRIAGE_SYSTEM_PROMPT
from prompts.reply import REPLY_SYSTEM_PROMPT, format_reply_user_prompt
from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt
from prompts.memory_context import build_memory_context_block
from prompts.obligation import OBLIGATION_SYSTEM_PROMPT, format_obligation_user_prompt

from build_index import load_index, retrieve, head_tail
from deep_analysis import build_mini_thread
from triage_pass import format_triage_prompt, parse_triage_json, update_contact, update_thread
from build_ledger import parse_obligation_json
from enron_load import normalize_subject, strip_addresses

MEMORY_DIR = os.path.join(AGENT_DIR, "memory")
OUT_DIR = os.path.join(AGENT_DIR, "out")

RISK_BADGE = {"safe": "[OK]", "caution": "[!]", "warning": "[!!]", "critical": "[!!!]"}
FEEDBACK_PATH = os.path.join(MEMORY_DIR, "feedback.json")

_LOCAL_ONLY = False  # set by --local-only; hard-disables live LLM

# ---------------------------------------------------------------------------
# Safe I/O helpers
# ---------------------------------------------------------------------------

def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _atomic_write_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _atomic_write_pickle(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            pickle.dump(obj, f)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Memory loading (incremental — never rebuild)
# ---------------------------------------------------------------------------

def _build_seen_set(emails):
    """Build a dedup set: message_id → True when present, else (body, date_iso) tuple."""
    seen = set()
    for e in emails:
        mid = e.get("message_id", "")
        if mid:
            seen.add(("mid", mid))
        else:
            seen.add(("body_date", e.get("body", ""), e.get("date_iso", "")))
    return seen


def _is_seen(email_dict, seen):
    """Check if email is already in the corpus. message_id primary, body+date fallback."""
    mid = email_dict.get("message_id", "")
    if mid:
        return ("mid", mid) in seen
    return ("body_date", email_dict.get("body", ""), email_dict.get("date_iso", "")) in seen


# ---------------------------------------------------------------------------
# Feedback overrides (memory/feedback.json)
# ---------------------------------------------------------------------------

def _email_key(email_dict):
    """Stable key for feedback: message_id or MD5(body)."""
    mid = email_dict.get("message_id", "")
    return mid if mid else hashlib.md5(email_dict.get("body", "").encode()).hexdigest()


def load_feedback():
    return _load_json(FEEDBACK_PATH, {})


def record_feedback(email_dict, overrides, note=""):
    from datetime import datetime, timezone
    feedback = load_feedback()
    key = _email_key(email_dict)
    feedback[key] = {
        "overrides": overrides,
        "note": note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write_json(FEEDBACK_PATH, feedback)
    return key


def apply_feedback(triage, cold, scaffolded, feedback, email_key):
    """Apply overrides in-place. Returns set of overridden field names."""
    entry = feedback.get(email_key, {})
    overrides = entry.get("overrides", {})
    touched = set()
    for field, value in overrides.items():
        if field in ("intent", "urgency", "risk_level", "tone_label"):
            triage[field] = value
            touched.add(field)
        elif field == "cold.draft_text" and cold is not None:
            cold["draft_text"] = value
            touched.add("cold.draft_text")
        elif field == "scaffolded.draft_text" and scaffolded is not None:
            scaffolded["draft_text"] = value
            touched.add("scaffolded.draft_text")
    return touched


def redact_report(text):
    """Scrub PII from rendered report for safe sharing."""
    from enron_load import PHONE_RE, BARE_ADDR_RE, ADDR_RE, EXCHANGE_RE
    text = EXCHANGE_RE.sub("[EMAIL]", text)
    text = ADDR_RE.sub("[EMAIL]", text)
    text = BARE_ADDR_RE.sub("[EMAIL]", text)
    text = PHONE_RE.sub("[PHONE]", text)
    return text


def load_memory():
    vectors, metadata = None, None
    try:
        vectors, metadata = load_index()
    except Exception:
        pass
    emails = _load_json(os.path.join(MEMORY_DIR, "emails.json"), [])
    return {
        "emails":         emails,
        "contacts":       _load_json(os.path.join(MEMORY_DIR, "contacts.json"), {}),
        "threads":        _load_json(os.path.join(MEMORY_DIR, "threads.json"), {}),
        "triage_results": _load_json(os.path.join(MEMORY_DIR, "triage_results.json"), []),
        "ledger":         _load_json(os.path.join(MEMORY_DIR, "ledger.json"),
                                     {"you_owe": [], "you_promised": [], "resolved": []}),
        "vectors":        vectors,
        "metadata":       metadata,
        "_seen":          _build_seen_set(emails),
    }


# ---------------------------------------------------------------------------
# Email parsing (.eml / .mbox / raw text → standard dict)
# ---------------------------------------------------------------------------

def _parse_date(date_str):
    if not date_str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    try:
        return email.utils.parsedate_to_datetime(date_str).isoformat()
    except Exception:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


def _extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
    payload = msg.get_payload(decode=True)
    if payload:
        return payload.decode("utf-8", errors="replace")
    return ""


def _addr_list(header):
    if not header:
        return ""
    return ", ".join(name or addr for name, addr in email.utils.getaddresses([header]))


def parse_eml(raw_bytes):
    msg = email.message_from_bytes(raw_bytes)
    from_display, _ = email.utils.parseaddr(msg.get("From", ""))
    if not from_display:
        from_display = msg.get("From", "Unknown")
    return {
        "message_id":   msg.get("Message-ID", ""),
        "from":         from_display,
        "to":           _addr_list(msg.get("To", "")),
        "cc":           _addr_list(msg.get("Cc", "")),
        "date":         msg.get("Date", ""),
        "date_iso":     _parse_date(msg.get("Date", "")),
        "subject":      msg.get("Subject", ""),
        "norm_subject": normalize_subject(msg.get("Subject", "")),
        "body":         _extract_body(msg),
    }


def parse_raw_text(text):
    headers, body_start = {}, 0
    for i, line in enumerate(text.split("\n")):
        if line.strip() == "":
            body_start = i + 1
            break
        if ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip()] = v.strip()
    body = "\n".join(text.split("\n")[body_start:])
    from_raw = headers.get("From", "Unknown")
    display, _ = email.utils.parseaddr(from_raw)
    return {
        "message_id":   hashlib.md5(text.encode()).hexdigest()[:16],
        "from":         display or from_raw,
        "to":           headers.get("To", "Unknown"),
        "cc":           headers.get("Cc", ""),
        "date":         headers.get("Date", ""),
        "date_iso":     _parse_date(headers.get("Date", "")),
        "subject":      headers.get("Subject", "(no subject)"),
        "norm_subject": normalize_subject(headers.get("Subject", "")),
        "body":         body,
    }


def deidentify(email_dict):
    from enron_load import PHONE_RE
    return {
        "message_id":   email_dict.get("message_id", ""),
        "subject":      strip_addresses(email_dict.get("subject", "")),
        "norm_subject": email_dict.get("norm_subject", ""),
        "date":         email_dict.get("date", ""),
        "date_iso":     email_dict.get("date_iso", ""),
        "from":         strip_addresses(email_dict.get("from", "")),
        "to":           strip_addresses(email_dict.get("to", "")),
        "cc":           strip_addresses(email_dict.get("cc", "")),
        "body":         PHONE_RE.sub("[PHONE]", strip_addresses(email_dict.get("body", ""))),
    }


# ---------------------------------------------------------------------------
# Offline-safe LLM wrapper
# ---------------------------------------------------------------------------

_NOT_ANALYZED = {
    "intent": "not analyzed (offline)",
    "urgency": "low",
    "risk_level": "safe",
    "tone_label": "neutral",
    "key_signals": [],
    "open_asks": [],
}


def _cache_read(system_prompt, user_prompt, temperature=0.3, model="deepseek-chat"):
    """Return cached response or None on miss."""
    path = _cache_path(_cache_key(system_prompt, user_prompt, temperature, model))
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["response"]
    return None


def _has_api_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return True
    env_path = os.path.join(AGENT_DIR, ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY=") and len(line) > 20:
                return True
    return False


def safe_llm(system_prompt, user_prompt, live=False):
    """Cache-first LLM call. Returns None on miss when offline."""
    cached = _cache_read(system_prompt, user_prompt)
    if cached is not None:
        return cached
    if _LOCAL_ONLY or not live or not _has_api_key():
        return None
    from llm.cache import cached_call_llm
    return cached_call_llm(system_prompt, user_prompt)


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def run_triage(email_dict, live):
    raw = safe_llm(TRIAGE_SYSTEM_PROMPT, format_triage_prompt(email_dict), live=live)
    if raw is None:
        return dict(_NOT_ANALYZED)
    return parse_triage_json(raw)


def run_obligations(email_dict, triage_result, live):
    asks = triage_result.get("open_asks", [])
    if not asks:
        return []
    raw = safe_llm(
        OBLIGATION_SYSTEM_PROMPT,
        format_obligation_user_prompt(email_dict, asks),
        live=live,
    )
    if raw is None:
        return []
    return parse_obligation_json(raw)


def _build_thread(email_dict, memory):
    """Build mini-thread, ensuring the new email appears as the last message."""
    thread_data = build_mini_thread(email_dict, memory["emails"], memory["triage_results"])
    # build_mini_thread falls back to including the email itself when no matches —
    # check body to avoid duplicating it.
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
    return thread_data


def run_pic(email_dict, memory, live, emb_model):
    thread_data = _build_thread(email_dict, memory)

    recalled = []
    if memory["vectors"] is not None and emb_model is not None:
        recalled = retrieve(
            head_tail(email_dict.get("body", "")),
            memory["vectors"], memory["metadata"], emb_model, k=3,
        )

    memory_block = build_memory_context_block(
        sender=email_dict.get("from", "Unknown"),
        email_idx=len(memory["emails"]),
        date_iso=email_dict.get("date_iso", ""),
        contacts=memory["contacts"],
        thread_key=email_dict.get("norm_subject", ""),
        threads=memory["threads"],
        recalled_emails=recalled,
        triage_results=memory["triage_results"],
    )

    user_prompt = memory_block + "\n\n" + format_subtext_user_prompt(thread_data)
    raw = safe_llm(SUBTEXT_SYSTEM_PROMPT, user_prompt, live=live)
    pic = None
    if raw is not None:
        try:
            pic = json.loads(raw)
        except json.JSONDecodeError:
            pass
    return pic, memory_block


def run_drafts(email_dict, pic_result, memory_block, memory, live):
    thread_data = _build_thread(email_dict, memory)
    msgs = thread_data["messages"]

    def _draft(user_prompt):
        raw = safe_llm(REPLY_SYSTEM_PROMPT, user_prompt, live=live)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"draft_text": raw, "rationale": "(parse error)"}

    cold = _draft(format_reply_user_prompt(msgs))

    scaffold = ""
    if pic_result:
        scaffold = (
            "--- PRAGMATIC INFERENCE CHAIN ANALYSIS ---\n"
            + json.dumps(pic_result, indent=2)
            + "\n\n--- RELATIONSHIP & THREAD CONTEXT ---\n"
            + memory_block
        )
    scaffolded = _draft(format_reply_user_prompt(msgs, scaffold=scaffold))

    return cold, scaffolded


# ---------------------------------------------------------------------------
# Incremental memory update
# ---------------------------------------------------------------------------

def append_memory(email_dict, triage_result, obligations, memory):
    sender = email_dict.get("from", "Unknown")
    date_iso = email_dict.get("date_iso", "")
    norm_subj = email_dict.get("norm_subject", "")

    if _is_seen(email_dict, memory.get("_seen", set())):
        return

    memory["emails"].append(email_dict)
    # Keep dedup set in sync
    mid = email_dict.get("message_id", "")
    if mid:
        memory.setdefault("_seen", set()).add(("mid", mid))
    else:
        memory.setdefault("_seen", set()).add(("body_date", email_dict.get("body", ""), date_iso))
    triage_result["_email_idx"] = len(memory["emails"]) - 1
    triage_result["_cached"] = True
    memory["triage_results"].append(triage_result)

    update_contact(memory["contacts"], sender, triage_result, date_iso)
    update_thread(memory["threads"], norm_subj, triage_result, date_iso, sender)

    for o in obligations:
        entry = {
            "direction":       o.get("direction", "inbound"),
            "canonical_ask":   o.get("canonical_ask", "unknown ask"),
            "implied_deadline": o.get("implied_deadline"),
            "obligor":         o.get("obligor", "Unknown"),
            "contact":         sender,
            "ask_date":        date_iso,
            "age_days":        0,
            "norm_subject":    norm_subj,
            "importance":      1.0,
            "status":          "open",
            "_email_idx":      len(memory["emails"]) - 1,
        }
        bucket = "you_owe" if entry["direction"] == "inbound" else "you_promised"
        memory["ledger"].setdefault(bucket, []).append(entry)


def persist_memory(memory, emb_model):
    _atomic_write_json(os.path.join(MEMORY_DIR, "emails.json"), memory["emails"])
    _atomic_write_json(os.path.join(MEMORY_DIR, "contacts.json"), memory["contacts"])
    _atomic_write_json(os.path.join(MEMORY_DIR, "threads.json"), memory["threads"])
    _atomic_write_json(os.path.join(MEMORY_DIR, "triage_results.json"), memory["triage_results"])
    _atomic_write_json(os.path.join(MEMORY_DIR, "ledger.json"), memory["ledger"])

    if emb_model is not None:
        _append_index(memory["emails"][-1], memory, emb_model)


def _append_index(email_dict, memory, model):
    import numpy as np

    vectors = memory["vectors"]
    metadata = memory["metadata"]
    if vectors is None:
        vectors = np.empty((0, 384), dtype=np.float32)
        metadata = []

    idx_path = os.path.join(MEMORY_DIR, "index.pkl")
    new_idx = len(metadata)
    vec = model.encode([head_tail(email_dict.get("body", ""))], normalize_embeddings=True)
    vectors = np.vstack([vectors, np.array(vec, dtype=np.float32)])
    metadata.append({
        "idx":          new_idx,
        "message_id":   email_dict.get("message_id", ""),
        "date_iso":     email_dict.get("date_iso", ""),
        "norm_subject": email_dict.get("norm_subject", ""),
        "from":         email_dict.get("from", ""),
        "snippet":      email_dict.get("body", "")[:120].replace("\n", " "),
    })

    _atomic_write_pickle(idx_path, {
        "model_name": "all-MiniLM-L6-v2",
        "vectors": vectors,
        "metadata": metadata,
    })
    memory["vectors"] = vectors
    memory["metadata"] = metadata


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _contact_obligations(sender, ledger):
    results = []
    s = sender.lower()
    for bucket in ("you_owe", "you_promised"):
        for o in ledger.get(bucket, []):
            c = o.get("contact", "").lower()
            if s in c or c in s:
                results.append(o)
    return results


def render_report(email_dict, triage, pic, cold, scaffolded, memory_block, memory,
                  feedback_touched=None):
    _CORR = " ✎ user-corrected"
    fb = feedback_touched or set()
    sender = email_dict.get("from", "Unknown")
    subject = email_dict.get("subject", "(no subject)")
    date = email_dict.get("date", "")
    risk = triage.get("risk_level", "safe")
    badge = RISK_BADGE.get(risk, "[?]")

    md = []
    md.append("# SemanticMail Analysis Report\n")
    md.append(f"**From:** {sender}  ")
    md.append(f"**Subject:** {subject}  ")
    md.append(f"**Date:** {date}\n")

    # --- Triage ---
    md.append(f"## Triage Verdict {badge}\n")
    md.append(f"- **Intent:** {triage.get('intent', 'unknown')}"
              + (_CORR if "intent" in fb else ""))
    md.append(f"- **Urgency:** {triage.get('urgency', 'low')}"
              + (_CORR if "urgency" in fb else ""))
    md.append(f"- **Risk Level:** {risk}"
              + (_CORR if "risk_level" in fb else ""))
    md.append(f"- **Tone:** {triage.get('tone_label', 'neutral')}"
              + (_CORR if "tone_label" in fb else ""))
    for s in triage.get("key_signals", []):
        md.append(f"  - Signal: {s}")
    for a in triage.get("open_asks", []):
        md.append(f"  - Open ask: {a}")
    md.append("")

    # --- PIC analysis ---
    md.append("## 4-Layer PIC Analysis\n")
    if pic:
        for pe in pic.get("per_email_analysis", []):
            md.append(f"### Email {pe.get('email_index', '?')} — {pe.get('from', '?')}\n")
            md.append(f"**Literal:** {pe.get('literal_content', 'N/A')}\n")
            pi = pe.get("pragmatic_inference", {})
            for v in pi.get("gricean_violations", []):
                md.append(f"- Violation ({v.get('maxim', '?')}): {v.get('description', '')}")
            for act in pi.get("indirect_speech_acts", []):
                md.append(f"- Indirect act: {act}")
            md.append(f"\n**Implicature:** {pi.get('implicature', 'N/A')}\n")
            sd = pe.get("social_dynamics", {})
            md.append(f"- **Power:** {sd.get('power_relationship', 'N/A')}")
            md.append(f"- **Face threats:** {sd.get('face_threats', 'N/A')}")
            md.append(f"- **Politeness:** {sd.get('politeness_strategy', 'N/A')}")
            md.append(f"- **Tone:** {sd.get('tone_label', '?')} | **Risk:** {pe.get('risk_level', '?')}\n")
        tl = pic.get("thread_level", {})
        if tl:
            md.append("### Thread Summary\n")
            traj = tl.get("tone_trajectory", [])
            if traj:
                md.append(f"**Tone trajectory:** {' -> '.join(traj)}")
            md.append(f"\n**Overall risk:** {tl.get('overall_risk', 'N/A')}")
            md.append(f"\n**Recommended strategy:** {tl.get('recommended_strategy', 'N/A')}\n")
            for m in tl.get("common_mistakes", []):
                md.append(f"- [avoid] {m}")
            md.append("")
    else:
        md.append("*Not analyzed (offline mode, no cached result).*\n")

    # --- Reply drafts ---
    md.append("## Reply Drafts\n")

    md.append("### COLD Draft (no context)\n")
    if cold:
        md.append("```")
        md.append(cold.get("draft_text", ""))
        md.append("```\n")
        md.append(f"*Rationale: {cold.get('rationale', '')}*"
                  + (_CORR if "cold.draft_text" in fb else ""))
    else:
        md.append("*Not generated (offline).*")
    md.append("")

    md.append("### SCAFFOLDED Draft (PIC + memory context)\n")
    if scaffolded:
        md.append("```")
        md.append(scaffolded.get("draft_text", ""))
        md.append("```\n")
        md.append(f"*Rationale: {scaffolded.get('rationale', '')}*"
                  + (_CORR if "scaffolded.draft_text" in fb else ""))
    else:
        md.append("*Not generated (offline).*")
    md.append("")

    # --- Obligations ---
    obs = _contact_obligations(sender, memory["ledger"])
    md.append(f"## Open Obligations — {sender}\n")
    if obs:
        for o in obs:
            label = "You owe" if o["direction"] == "inbound" else "You promised"
            md.append(f"- **{label}:** {o['canonical_ask']}")
            if o.get("implied_deadline"):
                md.append(f"  - Deadline: {o['implied_deadline']}")
            if o.get("age_days"):
                md.append(f"  - Age: {o['age_days']} days")
    else:
        md.append("*No open obligations with this contact.*")
    md.append("")

    # --- Memory context (collapsed) ---
    if memory_block:
        md.append("<details><summary>Memory Context Block</summary>\n")
        md.append("```")
        md.append(memory_block)
        md.append("```\n</details>\n")

    return "\n".join(md)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _LOCAL_ONLY

    ap = argparse.ArgumentParser(description="SemanticMail Agent — end-to-end email analysis")
    ap.add_argument("input", nargs="?", help=".eml / .mbox file, or '-' for stdin")
    ap.add_argument("--text", action="store_true",
                    help="Read raw email text from stdin (From/To/Date/Subject + body)")
    ap.add_argument("--live", action="store_true",
                    help="Allow live LLM calls on cache miss (needs DEEPSEEK_API_KEY)")
    ap.add_argument("--local-only", action="store_true",
                    help="Hard-disable live LLM — nothing leaves the machine")
    ap.add_argument("--redact", action="store_true",
                    help="Scrub PII from report output for safe sharing")
    ap.add_argument("--feedback", metavar="JSON",
                    help='Record user correction, e.g. \'{"risk_level":"caution"}\'')
    ap.add_argument("--out", help="Output file path (default: out/<id>.md)")
    ap.add_argument("--no-deidentify", action="store_true", help="Skip PII de-identification")
    args = ap.parse_args()

    if not args.input and not args.text:
        ap.error("Provide an input file (.eml/.mbox) or use --text")

    _LOCAL_ONLY = args.local_only

    # --- Parse input ---
    emails = []
    if args.text or args.input == "-":
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit("Error: no input on stdin")
        emails.append(parse_raw_text(raw))
    else:
        path = args.input
        if not os.path.exists(path):
            sys.exit(f"Error: file not found: {path}")
        if path.endswith(".mbox"):
            mbox = mailbox.mbox(path)
            for msg in mbox:
                emails.append(parse_eml(msg.as_bytes()))
            print(f"Loaded {len(emails)} emails from mbox", file=sys.stderr)
        else:
            with open(path, "rb") as f:
                emails.append(parse_eml(f.read()))

    if not emails:
        sys.exit("Error: no emails parsed")

    # --- Load memory (incremental) ---
    print("Loading memory...", file=sys.stderr)
    memory = load_memory()
    feedback = load_feedback()
    print(f"  {len(memory['emails'])} emails | {len(memory['contacts'])} contacts | "
          f"{len(memory['threads'])} threads | {len(feedback)} feedback entries",
          file=sys.stderr)

    emb_model = None
    try:
        from sentence_transformers import SentenceTransformer
        emb_model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        print(f"Embedding model unavailable ({e}), skipping retrieval", file=sys.stderr)

    # --- Process each email ---
    for i, edict in enumerate(emails):
        subj = edict.get("subject", "")[:60]
        sender = edict.get("from", "Unknown")
        print(f"\n[{i+1}/{len(emails)}] {sender}: {subj}...", file=sys.stderr)

        if not args.no_deidentify:
            edict = deidentify(edict)

        # Record feedback if --feedback given (then exit)
        if args.feedback:
            try:
                fb_overrides = json.loads(args.feedback)
            except json.JSONDecodeError:
                sys.exit("Error: --feedback value must be valid JSON")
            note = fb_overrides.pop("_note", "")
            key = record_feedback(edict, fb_overrides, note)
            print(f"Feedback recorded for {key}", file=sys.stderr)
            continue

        triage = run_triage(edict, args.live)
        print(f"  triage: intent={triage['intent']} risk={triage['risk_level']} "
              f"tone={triage['tone_label']}", file=sys.stderr)

        obligations = run_obligations(edict, triage, args.live)
        if obligations:
            print(f"  obligations: {len(obligations)}", file=sys.stderr)

        pic, mem_block = run_pic(edict, memory, args.live, emb_model)
        print(f"  PIC: {'yes' if pic else 'no (offline)'}", file=sys.stderr)

        cold, scaffolded = run_drafts(edict, pic, mem_block, memory, args.live)
        print(f"  drafts: cold={'yes' if cold else 'no'} "
              f"scaffolded={'yes' if scaffolded else 'no'}", file=sys.stderr)

        append_memory(edict, triage, obligations, memory)

        # Apply feedback overrides
        fb_key = _email_key(edict)
        fb_touched = apply_feedback(triage, cold, scaffolded, feedback, fb_key)
        if fb_touched:
            print(f"  feedback applied: {fb_touched}", file=sys.stderr)

        report = render_report(edict, triage, pic, cold, scaffolded, mem_block, memory,
                               feedback_touched=fb_touched)

        # Redact PII if requested
        if args.redact:
            report = redact_report(report)

        # stdout
        print(report)

        # file copy
        os.makedirs(OUT_DIR, exist_ok=True)
        mid = edict.get("message_id", f"email_{i}")
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(mid))[:64]
        out_path = args.out or os.path.join(OUT_DIR, f"{safe_id}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nSaved: {out_path}", file=sys.stderr)

    # --- Persist ---
    print("\nPersisting memory...", file=sys.stderr)
    persist_memory(memory, emb_model)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
