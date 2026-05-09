"""Ablation prompts — Conditions B and C.

Condition B: Generic "analyze subtext" — no PIC structure, no theoretical frameworks.
Condition C: No analysis framing — just "review this email thread."

Both use the same JSON output schema as subtext.py for fair comparison.
"""

# ---------------------------------------------------------------------------
# Condition B: Generic subtext analysis (no theoretical scaffolding)
# ---------------------------------------------------------------------------

ABLATION_SYSTEM_PROMPT = """\
You are an email analysis assistant. Analyze the subtext, implied meaning, and social \
dynamics of the email thread below. Pay attention to what is NOT said as much as what IS said.

For each email, identify:
- What was literally said
- What was implied or left unsaid
- The relationship dynamics between participants
- Whether the message carries any risk of misunderstanding or relational tension

Then provide an overall thread-level assessment.

Your output MUST be ONLY valid JSON matching this exact schema:

{
  "per_email_analysis": [
    {
      "email_index": 1,
      "from": "Sender Name",
      "literal_content": "...",
      "pragmatic_inference": {
        "gricean_violations": [
          {"maxim": "quantity|manner|relevance|quality", "description": "...", "signal": "..."}
        ],
        "indirect_speech_acts": ["..."],
        "implicature": "..."
      },
      "social_dynamics": {
        "power_relationship": "...",
        "face_threats": "...",
        "politeness_strategy": "bald_on_record|positive_politeness|negative_politeness|off_record|avoidance",
        "tone_label": "enthusiastic|warm|neutral|cool|evasive|hostile"
      },
      "risk_level": "safe|caution|warning|critical"
    }
  ],
  "thread_level": {
    "tone_trajectory": ["warm", "enthusiastic", "warm", "cool"],
    "overall_risk": "safe|caution|warning|critical",
    "recommended_strategy": "...",
    "common_mistakes": ["...", "...", "..."]
  }
}

Rules:
- email_index starts at 1 (not 0).
- The "from" field should be the sender's display name (before any <email> part).
- tone_trajectory must have exactly one entry per email in the thread.
- All arrays must be present (use empty arrays if no items).
- risk_level is exactly one of: "safe", "caution", "warning", "critical".
- politeness_strategy is exactly one of: "bald_on_record", "positive_politeness", \
"negative_politeness", "off_record", "avoidance".
- tone_label is exactly one of: "enthusiastic", "warm", "neutral", "cool", "evasive", "hostile".
- Respond with ONLY the JSON object — no markdown fences, no preamble, no commentary.
"""


def format_ablation_user_prompt(thread_data: dict) -> str:
    """Format thread data into user prompt for generic subtext analysis.

    Args:
        thread_data: The full thread dictionary with keys 'title', 'messages', etc.

    Returns:
        Formatted user prompt string ready for the LLM.
    """
    title = thread_data.get("title", "Unknown Thread")
    messages = thread_data.get("messages", [])

    lines = [f"Analyze the following email thread: **{title}**\n"]

    for i, msg in enumerate(messages):
        sender = msg.get("from", "Unknown")
        recipient = msg.get("to", "Unknown")
        date = msg.get("date", "Unknown")
        subject = msg.get("subject", "(no subject)")
        body = msg.get("body", "")

        lines.append(f"--- Email {i + 1} ---")
        lines.append(f"From: {sender}")
        lines.append(f"To: {recipient}")
        lines.append(f"Date: {date}")
        lines.append(f"Subject: {subject}")
        lines.append(f"Body:\n{body}")
        lines.append("")

    lines.append(
        "Analyze the subtext and social dynamics of each email above, "
        "then provide the thread-level summary. Respond with ONLY valid JSON."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Condition C: No analysis framing — just "review this thread"
# ---------------------------------------------------------------------------

NO_ANALYSIS_SYSTEM_PROMPT = """\
You are a helpful assistant. Review the email thread below and provide your assessment.

Your output MUST be ONLY valid JSON matching this exact schema:

{
  "per_email_analysis": [
    {
      "email_index": 1,
      "from": "Sender Name",
      "literal_content": "...",
      "pragmatic_inference": {
        "gricean_violations": [
          {"maxim": "quantity|manner|relevance|quality", "description": "...", "signal": "..."}
        ],
        "indirect_speech_acts": ["..."],
        "implicature": "..."
      },
      "social_dynamics": {
        "power_relationship": "...",
        "face_threats": "...",
        "politeness_strategy": "bald_on_record|positive_politeness|negative_politeness|off_record|avoidance",
        "tone_label": "enthusiastic|warm|neutral|cool|evasive|hostile"
      },
      "risk_level": "safe|caution|warning|critical"
    }
  ],
  "thread_level": {
    "tone_trajectory": ["warm", "enthusiastic", "warm", "cool"],
    "overall_risk": "safe|caution|warning|critical",
    "recommended_strategy": "...",
    "common_mistakes": ["...", "...", "..."]
  }
}

Rules:
- email_index starts at 1 (not 0).
- The "from" field should be the sender's display name (before any <email> part).
- tone_trajectory must have exactly one entry per email in the thread.
- All arrays must be present (use empty arrays if no items).
- risk_level is exactly one of: "safe", "caution", "warning", "critical".
- politeness_strategy is exactly one of: "bald_on_record", "positive_politeness", \
"negative_politeness", "off_record", "avoidance".
- tone_label is exactly one of: "enthusiastic", "warm", "neutral", "cool", "evasive", "hostile".
- Respond with ONLY the JSON object — no markdown fences, no preamble, no commentary.
"""


def format_no_analysis_user_prompt(thread_data: dict) -> str:
    """Format thread data into user prompt with no analysis framing.

    Args:
        thread_data: The full thread dictionary.

    Returns:
        Formatted user prompt string.
    """
    title = thread_data.get("title", "Unknown Thread")
    messages = thread_data.get("messages", [])

    lines = [f"Here is an email thread: **{title}**\n"]

    for i, msg in enumerate(messages):
        sender = msg.get("from", "Unknown")
        recipient = msg.get("to", "Unknown")
        date = msg.get("date", "Unknown")
        subject = msg.get("subject", "(no subject)")
        body = msg.get("body", "")

        lines.append(f"--- Email {i + 1} ---")
        lines.append(f"From: {sender}")
        lines.append(f"To: {recipient}")
        lines.append(f"Date: {date}")
        lines.append(f"Subject: {subject}")
        lines.append(f"Body:\n{body}")
        lines.append("")

    lines.append(
        "Review this thread and respond with ONLY valid JSON."
    )

    return "\n".join(lines)
