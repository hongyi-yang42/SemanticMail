"""Reply generation prompt — single draft with optional structural scaffold.

Two conditions share the SAME system prompt (neutral — no pragmatic framing):
  COLD:       mini-thread only.
  SCAFFOLDED: mini-thread + PIC analysis + memory context block.

Output: ready-to-send draft + one-line rationale (separate from body).
"""

from __future__ import annotations

REPLY_SYSTEM_PROMPT = """\
You are a professional email reply drafter. Given an incoming email thread, \
compose a complete, ready-to-send reply to the most recent message.

Requirements:
- Professional tone appropriate for workplace communication.
- Address the substantive content and any explicit requests.
- Complete email: greeting, body, sign-off.

Output valid JSON with this exact schema:
{
  "draft_text": "Dear [Name],\\n\\n[Body]\\n\\nBest,\\n[Sender]",
  "rationale": "One sentence explaining key decisions in this draft."
}
"""


def format_reply_user_prompt(
    thread_messages: list[dict],
    scaffold: str = "",
) -> str:
    """Format user prompt for reply drafting.

    Args:
        thread_messages: List of message dicts (from, to, date, subject, body).
        scaffold: Optional structural scaffold (PIC analysis + memory context).

    Returns:
        Formatted user prompt string.
    """
    formatted = []
    for i, msg in enumerate(thread_messages):
        formatted.append(
            f"--- Email {i + 1} ---\n"
            f"From: {msg.get('from', 'Unknown')}\n"
            f"To: {msg.get('to', 'Unknown')}\n"
            f"Date: {msg.get('date', 'Unknown')}\n"
            f"Subject: {msg.get('subject', '(no subject)')}\n\n"
            f"{msg.get('body', '')}"
        )

    thread_text = "\n\n".join(formatted)

    scaffold_section = ""
    if scaffold:
        scaffold_section = (
            f"[STRUCTURAL CONTEXT]\n{scaffold}\n[END STRUCTURAL CONTEXT]\n\n"
        )

    return (
        f"{scaffold_section}"
        f"Draft a professional reply to the most recent message in this thread.\n\n"
        f"{thread_text}"
    )
