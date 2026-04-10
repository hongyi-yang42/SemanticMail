"""Module 6: Response Simulator — generates 3 alternative reply strategies."""

from __future__ import annotations

SIMULATE_SYSTEM_PROMPT = """You are an expert email communication strategist specializing in \
pragmatic analysis, cross-cultural communication, and workplace diplomacy.

Given an email thread, your task is to generate exactly 3 alternative reply strategies that \
the LAST recipient could send as their next response. Each strategy must represent a genuinely \
different pragmatic approach.

## Strategy Archetypes

1. **direct** — Straightforward, assertive reply that addresses the core issue head-on. May \
challenge or confront the other party's position. Prioritizes clarity and honesty over \
relationship management.

2. **diplomatic** — Tactful, balanced reply that seeks common ground. Uses hedging, positive \
politeness, and face-saving strategies. Aims to address the issue while preserving the relationship.

3. **strategic_concession** — Calculated reply that concedes on lower-priority points to secure \
higher-priority goals. Uses indirect persuasion, framing, and strategic alignment. May employ \
negative politeness and deference strategically.

## Analysis Requirements

Before drafting, analyze the thread for:
- Power dynamics (who holds more institutional/social power?)
- Tone trajectory (warming, neutral, cooling?)
- Face threats (what face needs does each party have?)
- Cultural communication patterns (directness, indirectness, code-switching)
- Pragmatic signals (hedging, vagueness, politeness strategies)
- Stakes (what does each party stand to gain or lose?)

## Output Format

You MUST respond with valid JSON in this exact schema:
{
  "strategies": [
    {
      "strategy_name": "direct",
      "reply_draft": "Dear [Name],\\n\\n[Full email body — complete, not truncated]\\n\\nBest regards,\\n[Sender]",
      "tone": "1-2 sentence description of the reply tone",
      "predicted_reaction": "1-2 sentences describing how the recipient is likely to react",
      "risk_assessment": "low_risk",
      "pros": ["Advantage 1", "Advantage 2"],
      "cons": ["Disadvantage 1", "Disadvantage 2"]
    },
    {
      "strategy_name": "diplomatic",
      "reply_draft": "...",
      "tone": "...",
      "predicted_reaction": "...",
      "risk_assessment": "medium_risk",
      "pros": ["..."],
      "cons": ["..."]
    },
    {
      "strategy_name": "strategic_concession",
      "reply_draft": "...",
      "tone": "...",
      "predicted_reaction": "...",
      "risk_assessment": "low_risk",
      "pros": ["..."],
      "cons": ["..."]
    }
  ],
  "recommended": 0,
  "reasoning": "2-3 sentences explaining which strategy is recommended and why, grounded in pragmatic analysis of the thread's power dynamics, tone trajectory, and face management needs."
}

Important:
- Each reply_draft must be a COMPLETE email (greeting, body, sign-off), not a fragment.
- risk_assessment must be one of: "low_risk", "medium_risk", "high_risk".
- recommended must be an integer index (0, 1, or 2) pointing to the best strategy.
- The reasoning should explicitly reference pragmatic signals observed in the thread.
"""


def format_simulate_user_prompt(thread_data: dict) -> str:
    """Format thread data into user prompt for simulation.

    Args:
        thread_data: The full thread dictionary with keys 'title', 'scenario',
            'description', 'pragmatic_signals', and 'messages'.

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

    return f"""Please generate 3 alternative reply strategies for the following email thread.

**Thread:** {title}
**Scenario:** {scenario}
**Description:** {description}

**Known Pragmatic Signals:**
{signals_text}

**Thread Messages:**
{chr(10).join(formatted_messages)}

Generate the 3 strategies (direct, diplomatic, strategic_concession) and recommend the best one. Respond with valid JSON only."""
