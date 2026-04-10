"""DeepSeek V3 wrapper using OpenAI SDK."""

import os
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
    """Call DeepSeek V3 and return the response content as a string.

    Args:
        system_prompt: System-level instructions.
        user_prompt: User message content.
        temperature: Sampling temperature (default 0.3).

    Returns:
        The raw text content of the assistant's reply.
    """
    response = _client.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content
