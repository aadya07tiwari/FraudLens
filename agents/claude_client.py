"""
Thin wrapper around the Anthropic API shared by the Intent Agent and the
NL-to-SQL Agent. Centralizing this here means the model name, retry logic,
and JSON-extraction logic only need to live in one place.
"""

import json
import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

_client = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def get_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> str:
    """Sends a single-turn request to Claude and returns the raw text response."""
    client = get_client()
    response = client.messages.create(
        model=get_model(),
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip()


def extract_json(text: str) -> dict:
    """Claude is instructed to return only JSON, but this strips any stray
    markdown fences or preamble defensively before parsing."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back to grabbing the first {...} block in the text.
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Could not parse JSON from Claude response:\n{text}")
