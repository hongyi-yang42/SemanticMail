"""Parse Enron corpus and extract candidate threads for SemanticMail.

Usage:
    cd SemanticMail
    python3 enron_parse.py /path/to/enron_mail_20150507/maildir

Extracts reply-chains from target users, identifies threads with
pragmatic phenomena, and prints candidates.
"""

import email
import email.policy
import os
import re
import sys
from collections import defaultdict

TARGET_USERS = [
    "lay-k",
    "skilling-j",
    "watkins-s",
    "shapiro-r",
    "dasovich-j",
    "kean-s",
    "steffes-j",
    "whalley-g",
    "baxter-s",
    "delainey-d",
    "lucci-p",
    "robertson-l",
]


def normalize_subject(subj: str) -> str:
    """Strip Re:/FW:/Fwd: prefixes and normalize whitespace for threading."""
    s = subj.strip()
    while True:
        prev = s
        s = re.sub(r"^(Re|RE|Fw|FW|Fwd)\s*:\s*", "", s, count=1)
        if s == prev:
            break
    return re.sub(r"\s+", " ", s).strip().lower()


def parse_email_file(filepath: str) -> dict | None:
    """Parse a single email file into a dict."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except Exception:
        return None

    msg = email.message_from_string(raw, policy=email.policy.compat32)

    subj = msg.get("Subject", "")
    date = msg.get("Date", "")
    from_addr = msg.get("From", "")
    to_addr = msg.get("To", "")
    cc_addr = msg.get("Cc", "")
    message_id = msg.get("Message-ID", "")
    in_reply_to = msg.get("In-Reply-To", "")
    references = msg.get("References", "")

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")

    # Trim forwarded/reply blocks to keep only new content
    body_lines = []
    for line in body.split("\n"):
        if re.match(r"^-----Original Message-----", line):
            break
        if re.match(r"^-----Forwarded by", line):
            break
        if re.match(r"^>.*", line) and len(body_lines) > 3:
            break
        body_lines.append(line)
    body = "\n".join(body_lines).strip()

    if not body or len(body) < 20:
        return None

    return {
        "filepath": filepath,
        "subject": subj,
        "norm_subject": normalize_subject(subj),
        "date": date,
        "from": from_addr,
        "to": to_addr,
        "cc": cc_addr,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "body": body,
    }


def find_threads(maildir: str) -> list[list[dict]]:
    """Find email threads from target users, grouped by normalized subject."""
    emails_by_subj: dict[str, list[dict]] = defaultdict(list)
    count = 0

    for user in TARGET_USERS:
        user_dir = os.path.join(maildir, user)
        if not os.path.isdir(user_dir):
            continue

        for root, _, files in os.walk(user_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                parsed = parse_email_file(fpath)
                if parsed:
                    emails_by_subj[parsed["norm_subject"]].append(parsed)
                    count += 1

    print(f"Parsed {count} emails from target users")
    print(f"Found {len(emails_by_subj)} unique subjects")

    # Filter: threads with 2-5 emails, sorted by date within each thread
    threads = []
    for subj, msgs in emails_by_subj.items():
        if 2 <= len(msgs) <= 5:
            msgs.sort(key=lambda m: m["date"])
            threads.append(msgs)

    threads.sort(key=lambda t: -len(t))
    print(f"Threads with 2-5 messages: {len(threads)}")
    return threads


def score_pragmatic_interest(thread: list[dict]) -> int:
    """Heuristic score for pragmatic phenomena (higher = more interesting)."""
    score = 0
    bodies = " ".join(m["body"] for m in thread)
    subjects = " ".join(m["subject"] for m in thread)
    all_text = bodies + " " + subjects

    # Power/hierarchy markers
    power_words = [
        "please review", "need you to", "i need", "asap", "urgent",
        "immediately", "must", "required", "expect", "make sure",
        "appreciate", "would like", "could you", "can you",
    ]
    for w in power_words:
        if w in all_text.lower():
            score += 2

    # Hedging/euphemism
    hedge_words = [
        "i think", "perhaps", "maybe", "possibly", "somewhat",
        "concern", "uncomfortable", "hesitant", "reluctant",
        "understand", "hope", "wish", "suggest", "recommend",
        "might want to", "we should consider",
    ]
    for w in hedge_words:
        if w in all_text.lower():
            score += 2

    # Indirect refusal / delay
    refusal_words = [
        "unfortunately", "not able to", "can't", "unable",
        "at this time", "for now", "let me get back",
        "need to check", "will follow up", "pending",
    ]
    for w in refusal_words:
        if w in all_text.lower():
            score += 2

    # CC escalation
    cc_addrs = [m["cc"] for m in thread if m["cc"]]
    if len(set(cc_addrs)) > 1:
        score += 3

    # Tone shift indicators
    tone_words = ["sorry", "apologize", "frustrated", "disappointed", "concerned"]
    for w in tone_words:
        if w in all_text.lower():
            score += 2

    # Thread length bonus (more back-and-forth = richer dynamics)
    score += len(thread)

    return score


def print_candidates(threads: list[list[dict]], top_n: int = 12):
    """Print top candidate threads."""
    scored = [(score_pragmatic_interest(t), t) for t in threads]
    scored.sort(key=lambda x: -x[0])

    print(f"\n{'='*80}")
    print(f"TOP {top_n} CANDIDATE THREADS (ranked by pragmatic-interest heuristic)")
    print(f"{'='*80}")

    for rank, (score, thread) in enumerate(scored[:top_n], 1):
        subj = thread[0]["subject"]
        print(f"\n--- CANDIDATE #{rank} (score={score}) ---")
        print(f"Subject: {subj}")
        participants = set()
        for m in thread:
            f = m["from"].split("<")[0].strip() or m["from"]
            participants.add(f)
        print(f"Participants: {', '.join(participants)}")
        print(f"Messages: {len(thread)}")
        print()

        for i, m in enumerate(thread):
            print(f"  [Email {i+1}]")
            print(f"  From: {m['from']}")
            print(f"  To: {m['to']}")
            if m["cc"]:
                print(f"  CC: {m['cc']}")
            print(f"  Date: {m['date']}")
            print(f"  Subject: {m['subject']}")
            body_preview = m["body"][:300]
            print(f"  Body: {body_preview}")
            if len(m["body"]) > 300:
                print(f"  ... ({len(m['body'])} chars total)")
            print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} /path/to/enron_mail_20150507/maildir")
        sys.exit(1)

    maildir = sys.argv[1]
    if not os.path.isdir(maildir):
        print(f"Error: {maildir} is not a directory")
        sys.exit(1)

    threads = find_threads(maildir)
    print_candidates(threads, top_n=12)
