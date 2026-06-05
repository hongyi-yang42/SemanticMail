"""Parse Enron emails for Jeff Dasovich: filter inbox (To/Cc), dedup, de-identify, slice.

Usage:
    cd email-agent
    python enron_load.py ../maildir

Outputs:
    memory/emails.json      — ~400 de-identified inbox emails (chronological)
    memory/sent_emails.json — sent mail metadata (tone baseline)
    memory/id_map.json      — real @address → de-identified address mapping
"""

import email
import email.policy
import email.utils
import json
import os
import re
import sys
from datetime import datetime, timezone

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
TARGET_USER = "dasovich-j"
INBOX_LIMIT = 400

PHONE_RE = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")
ADDR_RE = re.compile(r"<[^>]*@[^>]*>")
BARE_ADDR_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
EXCHANGE_RE = re.compile(r"</O=[^>]+>")
QUOTED_NAME_RE = re.compile(r"'([^']*)'")


def normalize_subject(subj: str) -> str:
    """Strip Re:/FW:/Fwd: prefixes and normalize whitespace for threading."""
    s = subj.strip()
    while True:
        prev = s
        s = re.sub(r"^(Re|RE|Fw|FW|Fwd)\s*:\s*", "", s, count=1)
        if s == prev:
            break
    return re.sub(r"\s+", " ", s).strip().lower()


def parse_enron_date(date_str: str) -> datetime:
    """Parse Enron date strings (multiple formats) into UTC datetime."""
    if not date_str:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)

    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        cleaned = re.sub(r"\s+", " ", date_str.strip())
        cleaned = re.sub(
            r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*,?\s*",
            "", cleaned,
        )
        for fmt in ["%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y"]:
            try:
                return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    except Exception:
        pass

    return datetime(2000, 1, 1, tzinfo=timezone.utc)


def extract_display_name(x_header: str) -> str:
    """Extract display names from X-From/X-To/X-Cc headers.

    Handles formats:
      "Ibrahim, Amr </O=ENRON/OU=NA/CN=RECIPIENTS/CN=AIBRAHI>"
      "Monica Singh <msingh@library.berkeley.edu>"
      "Dasovich, Jeff </O=ENRON/...>"
      "'Tom Chapman' <??S...>"
      "members@realmoney.com"  (bare address, no display name)
    """
    # Split on comma followed by a name pattern (not inside angle brackets)
    # X-To/X-Cc can have multiple recipients separated by commas
    parts = re.split(r",\s*(?=[A-Z])", x_header)
    names = []
    for part in parts:
        part = part.strip()
        # Remove Exchange-style address </O=ENRON/...>
        part = EXCHANGE_RE.sub("", part).strip()
        # Remove <email@domain>
        part = ADDR_RE.sub("", part).strip()
        # If what remains is a bare email address, use it as-is (will be stripped later)
        if not part or part == ",":
            continue
        # Remove surrounding quotes
        part = part.strip("'\"")
        # Remove trailing commas
        part = part.rstrip(",").strip()
        if part:
            names.append(part)
    return ", ".join(names)


def parse_email_enhanced(filepath: str) -> dict | None:
    """Parse email with X-From/X-To display names."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except Exception:
        return None

    msg = email.message_from_string(raw, policy=email.policy.compat32)

    # Use X-headers for display names, fall back to standard headers
    x_from = msg.get("X-From", "")
    from_addr = msg.get("From", "")
    x_to = msg.get("X-To", "")
    to_addr = msg.get("To", "")
    x_cc = msg.get("X-Cc", "") or ""
    cc_addr = msg.get("Cc", "") or ""

    # Pick display-name version; fall back to raw if X-header empty
    from_display = extract_display_name(x_from) if x_from else from_addr
    to_display = extract_display_name(x_to) if x_to else to_addr
    cc_display = extract_display_name(x_cc) if x_cc else cc_addr

    # For To/Cc filtering, use raw addresses (more reliable for matching)
    subj = msg.get("Subject", "")
    date_str = msg.get("Date", "")
    message_id = msg.get("Message-ID", "")

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")

    # Trim forwarded/reply blocks
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
        "date": date_str,
        "from_display": from_display,
        "from_raw": from_addr,
        "to_display": to_display,
        "to_raw": to_addr,
        "cc_display": cc_display,
        "cc_raw": cc_addr,
        "message_id": message_id,
        "body": body,
    }


def is_recipient(parsed: dict, user: str = "dasovich") -> bool:
    """Check if user appears in raw To or Cc fields."""
    for field in ["to_raw", "cc_raw"]:
        val = parsed.get(field, "")
        if user.lower() in val.lower():
            return True
    return False


def dedup_by_message_id(emails: list[dict]) -> list[dict]:
    """Remove duplicates by Message-ID, keeping first occurrence."""
    seen = set()
    out = []
    for e in emails:
        mid = e.get("message_id", "")
        if mid in seen:
            continue
        seen.add(mid)
        out.append(e)
    return out


def strip_addresses(text: str) -> str:
    """Remove raw email addresses from text, keeping display names."""
    text = EXCHANGE_RE.sub("", text)
    text = ADDR_RE.sub("", text)
    text = BARE_ADDR_RE.sub("[EMAIL]", text)
    return text.strip()


def deidentify_email(parsed: dict) -> dict:
    """Return a copy with @addresses and phone numbers stripped.
    Keep real display names (Enron is a public research corpus)."""
    return {
        "message_id": parsed.get("message_id", ""),
        "subject": strip_addresses(parsed.get("subject", "")),
        "norm_subject": parsed.get("norm_subject", ""),
        "date": parsed.get("date", ""),
        "date_iso": parse_enron_date(parsed.get("date", "")).isoformat(),
        "from": strip_addresses(parsed.get("from_display", "")),
        "to": strip_addresses(parsed.get("to_display", "")),
        "cc": strip_addresses(parsed.get("cc_display", "")),
        "body": PHONE_RE.sub("[PHONE]", strip_addresses(parsed.get("body", ""))),
    }


def load_folder(maildir_root: str, user: str, folder: str) -> list[dict]:
    """Parse all emails from a specific maildir folder."""
    folder_path = os.path.join(maildir_root, user, folder)
    if not os.path.isdir(folder_path):
        print(f"  Folder not found: {folder_path}")
        return []

    emails = []
    for fname in sorted(os.listdir(folder_path)):
        fpath = os.path.join(folder_path, fname)
        if not os.path.isfile(fpath):
            continue
        parsed = parse_email_enhanced(fpath)
        if parsed:
            emails.append(parsed)
    return emails


def main():
    if len(sys.argv) < 2:
        maildir_root = os.path.join(os.path.dirname(__file__), "..", "maildir")
    else:
        maildir_root = sys.argv[1]

    maildir_root = os.path.normpath(maildir_root)
    os.makedirs(MEMORY_DIR, exist_ok=True)

    # --- Load inbox ---
    print(f"Loading inbox for {TARGET_USER}...")
    inbox = load_folder(maildir_root, TARGET_USER, "inbox")
    print(f"  Raw inbox files: {len(inbox)}")

    # Filter to where dasovich is a recipient (use raw addresses for matching)
    inbox = [e for e in inbox if is_recipient(e, "dasovich")]
    print(f"  After To/Cc filter: {len(inbox)}")

    # Dedup
    inbox = dedup_by_message_id(inbox)
    print(f"  After dedup: {len(inbox)}")

    # Sort chronologically
    inbox.sort(key=lambda e: parse_enron_date(e.get("date", "")))

    # Slice
    inbox = inbox[:INBOX_LIMIT]
    print(f"  Chronological slice: {len(inbox)} emails")

    # --- Load sent ---
    print(f"Loading sent mail for {TARGET_USER}...")
    sent = load_folder(maildir_root, TARGET_USER, "sent")
    sent_extra = load_folder(maildir_root, TARGET_USER, "sent_items")
    all_sent = dedup_by_message_id(sent + sent_extra)
    all_sent.sort(key=lambda e: parse_enron_date(e.get("date", "")))
    print(f"  Sent emails (deduped): {len(all_sent)}")

    # --- De-identify ---
    print("De-identifying...")
    inbox_clean = [deidentify_email(e) for e in inbox]
    sent_clean = [deidentify_email(e) for e in all_sent]

    # --- Date range ---
    if inbox_clean:
        first_date = inbox_clean[0]["date_iso"][:10]
        last_date = inbox_clean[-1]["date_iso"][:10]
        print(f"  Date range: {first_date} -> {last_date}")

    # --- Write outputs ---
    emails_path = os.path.join(MEMORY_DIR, "emails.json")
    with open(emails_path, "w", encoding="utf-8") as f:
        json.dump(inbox_clean, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {emails_path} ({len(inbox_clean)} emails)")

    sent_path = os.path.join(MEMORY_DIR, "sent_emails.json")
    with open(sent_path, "w", encoding="utf-8") as f:
        json.dump(sent_clean, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {sent_path} ({len(sent_clean)} emails)")

    # --- Build address map ---
    addr_map = {}
    for e in inbox + all_sent:
        for field in ["from_raw", "to_raw", "cc_raw"]:
            val = e.get(field, "")
            for match in re.finditer(r"[\w.+-]+@[\w.-]+\.\w+", val):
                addr = match.group(0)
                addr_map[addr] = "[EMAIL]"
    map_path = os.path.join(MEMORY_DIR, "id_map.json")
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(addr_map, f, indent=2)
    print(f"  Wrote {map_path}")

    # --- Quick stats ---
    senders = set(e["from"] for e in inbox_clean)
    subjects = set(e["norm_subject"] for e in inbox_clean)
    print(f"\nStats: {len(senders)} unique senders, {len(subjects)} unique subjects")

    # Sample senders
    sender_counts = {}
    for e in inbox_clean:
        s = e["from"]
        sender_counts[s] = sender_counts.get(s, 0) + 1
    print("\nTop 10 senders:")
    for s, c in sorted(sender_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {c:4d}  {s}")


if __name__ == "__main__":
    main()
