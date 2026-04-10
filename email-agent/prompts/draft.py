"""Module 4: Context-Aware Reply Drafter — naive vs. smart drafts."""

from __future__ import annotations

DRAFT_SYSTEM_PROMPT = """You are an expert email reply drafter specializing in pragmatic \
communication analysis. Your task is to generate TWO reply drafts for the last message in an \
email thread: a **naive draft** and a **smart draft**.

## Naive Draft
The naive draft responds to ONLY the literal, semantic content of the emails. It:
- Takes everything at face value
- Ignores tone shifts, politeness strategies, and power dynamics
- Does not account for indirect speech acts or face threats
- Responds as if all statements are direct and literal
- Misses pragmatic signals like hedging, vagueness, code-switching, and tone changes

## Smart Draft
The smart draft accounts for ALL pragmatic signals in the thread. It:
- Recognizes tone trajectories (warming, cooling, neutral)
- Accounts for power dynamics and formality shifts
- Uses appropriate politeness strategies (positive/negative politeness)
- Addresses indirect speech acts and hidden intentions
- Manages face threats appropriately
- Responds to what is MEANT, not just what is SAID

## Output Format

You MUST respond with valid JSON in this exact schema:
{
  "naive_draft": {
    "draft_text": "Dear [Name],\\n\\n[Complete email body]\\n\\nBest regards,\\n[Sender]",
    "approach_description": "One sentence explaining the approach taken.",
    "pragmatic_awareness": ["List of pragmatic signals this draft MISSES or IGNORES"]
  },
  "smart_draft": {
    "draft_text": "Dear [Name],\\n\\n[Complete email body]\\n\\nBest regards,\\n[Sender]",
    "approach_description": "One sentence explaining the approach taken.",
    "pragmatic_awareness": ["List of pragmatic signals this draft ADDRESSES or LEVERAGES"]
  }
}

Important:
- Both drafts must be COMPLETE emails (greeting, body, sign-off).
- The naive_draft.pragmatic_awareness lists signals it MISSES.
- The smart_draft.pragmatic_awareness lists signals it ADDRESSES.
- The two drafts should be meaningfully different — not just rephrasings.
"""


# Inline fallback subtext prompt used when prompts.subtext is unavailable
_INLINE_SUBTEXT_PROMPT = """Analyze the following email thread for pragmatic/subtext signals. \
Identify: tone trajectory, power dynamics, face threats, politeness strategies, indirect speech \
acts, and cultural communication patterns. Provide a concise 3-5 sentence analysis.

Thread: {thread_title}
Messages:
{messages}
"""


def format_draft_user_prompt(thread_data: dict, subtext_analysis: str = "") -> str:
    """Format thread data + optional subtext analysis into user prompt for drafting.

    Args:
        thread_data: The full thread dictionary with keys 'title', 'scenario',
            'description', 'pragmatic_signals', and 'messages'.
        subtext_analysis: Optional subtext analysis text. If empty or not provided,
            the prompt will instruct the model to infer pragmatic signals itself.

    Returns:
        Formatted user prompt string.
    """
    title = thread_data.get("title", "Unknown Thread")
    scenario = thread_data.get("scenario", "")
    description = thread_data.get("description", "")
    signals = thread_data.get("pragmatic_signals", [])
    messages = thread_data.get("messages", [])

    # Format messages
    formatted_messages = []
    for i, msg in enumerate(messages):
        formatted_messages.append(
            f"--- Email {i + 1} ---\n"
            f"From: {msg.get('from', 'Unknown')}\n"
            f"To: {msg.get('to', 'Unknown')}\n"
            f"Date: {msg.get('date', 'Unknown')}\n"
            f"Subject: {msg.get('subject', '(no subject)')}\n\n"
            f"{msg.get('body', '')}"
        )

    signals_text = "\n".join(f"- {s}" for s in signals) if signals else "None specified"

    subtext_section = ""
    if subtext_analysis:
        subtext_section = f"""
**Subtext / Pragmatic Analysis:**
{subtext_analysis}
"""

    return f"""Please generate a naive draft and a smart draft reply for the following email thread.

**Thread:** {title}
**Scenario:** {scenario}
**Description:** {description}

**Known Pragmatic Signals:**
{signals_text}
{subtext_section}
**Thread Messages:**
{chr(10).join(formatted_messages)}

Generate both drafts. The naive draft should ignore pragmatic signals; the smart draft should \
address them. Respond with valid JSON only."""


def get_inline_subtext_prompt(thread_data: dict) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for inline subtext analysis.

    Used as a fallback when prompts.subtext module is not available.

    Args:
        thread_data: The full thread dictionary.

    Returns:
        A tuple of (system_prompt, user_prompt).
    """
    title = thread_data.get("title", "Unknown Thread")
    messages = thread_data.get("messages", [])

    formatted_messages = []
    for i, msg in enumerate(messages):
        formatted_messages.append(
            f"--- Email {i + 1} ---\n"
            f"From: {msg.get('from', 'Unknown')}\n"
            f"To: {msg.get('to', 'Unknown')}\n"
            f"Date: {msg.get('date', 'Unknown')}\n\n"
            f"{msg.get('body', '')}"
        )

    system_prompt = (
        "You are an expert in pragmatic analysis of email communication. "
        "Analyze the given email thread and provide a concise summary of the "
        "key pragmatic signals including: tone trajectory, power dynamics, "
        "face threats, politeness strategies, indirect speech acts, and "
        "cultural communication patterns. Respond in 3-5 sentences."
    )

    user_prompt = _INLINE_SUBTEXT_PROMPT.format(
        thread_title=title,
        messages="\n".join(formatted_messages),
    )

    return system_prompt, user_prompt
