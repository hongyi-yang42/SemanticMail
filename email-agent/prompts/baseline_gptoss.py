"""Minimal vanilla baseline prompt for GPT-OSS 20B comparison."""

from __future__ import annotations


BASELINE_GPTOSS_SYSTEM_PROMPT = (
    "You are a helpful email assistant. "
    "Write a professional reply to the latest email in the thread below."
)


def format_baseline_gptoss_user_prompt(thread_data: dict) -> str:
    """Format thread data into a minimal user prompt for the baseline model.

    Args:
        thread_data: The full thread dictionary.

    Returns:
        Formatted user prompt string.
    """
    messages = thread_data.get("messages", [])
    parts = []
    for i, msg in enumerate(messages):
        parts.append(
            f"[Email {i + 1}] From: {msg.get('from', 'Unknown')}\n"
            f"To: {msg.get('to', 'Unknown')}\n"
            f"Date: {msg.get('date', 'Unknown')}\n"
            f"Subject: {msg.get('subject', '(no subject)')}\n\n"
            f"{msg.get('body', '')}"
        )
    return "Here is the email thread:\n\n" + "\n\n---\n\n".join(parts)
