"""OpenRouter client for GPT-OSS 20B baseline comparison."""

import os

from openai import OpenAI


def call_baseline_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
    """Call GPT-OSS 20B via OpenRouter and return plain-text response.

    Client is initialised inside the function (not at module level)
    so that import-time side-effects are avoided.

    Args:
        system_prompt: System-level instructions.
        user_prompt: User message content.
        temperature: Sampling temperature.

    Returns:
        The raw text content of the assistant's reply.
    """
    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content
