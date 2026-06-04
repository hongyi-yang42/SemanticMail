"""Obligation extraction prompt — classifies ask-bearing emails into ledger entries.

For each email that contains an ask or commitment, extract structured obligation
data: direction (who owes whom), canonical ask description, implied deadline, and
obligor identity. Used by build_ledger.py.
"""

OBLIGATION_SYSTEM_PROMPT = """\
You are an email obligation analyst. Given an email that contains a request, \
ask, commitment, or promise, extract the obligation structure.

Jeff Dasovich is the mailbox owner (the receiver of inbound emails). \
The "direction" field captures the flow of obligation relative to Jeff:
- "inbound": someone is asking Jeff to do something (Jeff owes)
- "outbound": Jeff is promising or asking someone else to do something (someone owes Jeff)

Respond with ONLY valid JSON:
{
    "obligations": [
        {
            "direction": "inbound" | "outbound",
            "canonical_ask": "<short noun-phrase describing what is owed, max 8 words>",
            "implied_deadline": "<ISO date string or null if no deadline mentioned>",
            "obligor": "<name of the person who must fulfill the ask>"
        }
    ]
}

Rules:
- Extract one obligation per distinct ask. Most emails have 1; some have 2-3.
- If the email has no real ask (just FYI, acknowledgment, social), return {"obligations": []}.
- For inbound direction: obligor is "Jeff Dasovich" (someone asked him).
- For outbound direction: obligor is the recipient Jeff is asking/promising to.
- canonical_ask should be a concise noun phrase: "review CA draft", "send updated numbers", \
"schedule follow-up call", etc.
- implied_deadline: only if explicitly stated or clearly implied ("by Friday", "ASAP" = null). \
Use the most specific date you can infer; otherwise null.
- Be conservative: if in doubt about direction, prefer "inbound" (assume Jeff is being asked).
"""


OBLIGATION_USER_TEMPLATE = """\
Extract obligations from this email.

From: {from_}
To: {to}
Date: {date}
Subject: {subject}

Body:
{body}

Known asks from triage: {open_asks}"""


def format_obligation_user_prompt(email: dict, open_asks: list[str] | None = None) -> str:
    """Format a single email for obligation extraction.

    Args:
        email: Email dict with from, to, date, subject, body fields.
        open_asks: List of open_asks from triage (helps the LLM focus).
    """
    asks_str = ", ".join(open_asks) if open_asks else "(none flagged)"
    return OBLIGATION_USER_TEMPLATE.format(
        from_=email.get("from", ""),
        to=email.get("to", ""),
        date=email.get("date", ""),
        subject=email.get("subject", ""),
        body=email.get("body", ""),
        open_asks=asks_str,
    )
