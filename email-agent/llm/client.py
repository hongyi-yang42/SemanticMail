"""DeepSeek API wrapper using OpenAI SDK.

Note: ``deepseek-chat`` currently routes to V4-Flash (since 2026-04-24).
Earlier cached responses were generated under V3/V3.2.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def call_llm_with_usage(
    system_prompt: str, user_prompt: str, temperature: float = 0.3, model: str = "deepseek-chat",
) -> tuple[str, dict]:
    """Call DeepSeek and return (content, usage_dict).

    usage_dict keys: prompt_tokens, completion_tokens, total_tokens.
    """
    response = _client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }
    return content, usage


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, model: str = "deepseek-chat") -> str:
    """Call DeepSeek and return the response content as a string.

    Args:
        system_prompt: System-level instructions.
        user_prompt: User message content.
        temperature: Sampling temperature (default 0.3).
        model: Model ID (default ``deepseek-chat``, currently V4-Flash).

    Returns:
        The raw text content of the assistant's reply.
    """
    response = _client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content
