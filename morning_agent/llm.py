"""OpenRouter client — generate the briefing content with the chosen model."""

from __future__ import annotations

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = 120  # seconds


class LLMError(RuntimeError):
    """OpenRouter communication error or an empty model response."""


def generate(api_key: str, model: str, system_prompt: str, notes: str) -> str:
    """Send the prompt to OpenRouter and return the response text.

    Raises LLMError on any problem.
    """
    if not api_key:
        raise LLMError("Missing OpenRouter key — set it in Settings.")
    if not model:
        raise LLMError("No model selected — set it in Settings.")

    user_content = (
        "Here are the user's notes. Based on them, prepare the morning briefing "
        "according to the system instruction.\n\n" + notes
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional headers, useful in OpenRouter analytics.
        "HTTP-Referer": "https://github.com/morning-agent",
        "X-Title": "Morning Agent",
    }

    try:
        resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise LLMError(f"Network error while contacting OpenRouter: {exc}") from exc

    if resp.status_code != 200:
        detail = resp.text[:500]
        raise LLMError(f"OpenRouter returned HTTP {resp.status_code}: {detail}")

    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as exc:
        raise LLMError(f"Unexpected OpenRouter response: {resp.text[:500]}") from exc

    content = (content or "").strip()
    if not content:
        raise LLMError("The model returned an empty response.")
    return content
