"""
Thin wrapper around the Google Gemini API shared by the Intent Agent and the
NL-to-SQL Agent. Centralizing this here means the model name, retry logic,
and JSON-extraction logic only need to live in one place.

Note: filename/function names are kept as `claude_client.py` / `call_claude`
on purpose -- intent_agent.py and sql_agent.py import from this module by
name, so keeping the interface identical means no changes are needed there.
"""
import json
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_client_configured = False


def get_client():
    """Configures the Gemini SDK once and returns the genai module handle."""
    global _client_configured
    if not _client_configured:
        # Accept either name -- GOOGLE_API_KEY and GEMINI_API_KEY have both
        # been used across the team's local .env files; supporting both
        # avoids a silent "key not found" for whichever name someone has set.
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set. Copy .env.example "
                "to .env and add your key. Get one free at https://aistudio.google.com/apikey"
            )
        genai.configure(api_key=api_key)
        _client_configured = True
    return genai


def get_model() -> str:
    # NOTE: gemini-2.5-flash returns a 404 ("no longer available to new
    # users") as of this project's testing, and gemini-2.0-flash returns a
    # quota limit:0 error (deprecated model). gemini-flash-latest is the
    # current working alias -- if Google renames again, override via
    # GEMINI_MODEL in .env rather than editing this file.
    return os.getenv("GEMINI_MODEL", "gemini-flash-latest")


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 2048, temperature: float = 0.0) -> str:
    """Sends a single-turn request to Gemini and returns the raw text response.

    Kept the name `call_claude` so intent_agent.py / sql_agent.py don't need
    to change their imports.

    max_tokens default raised from 1024 -> 2048: Gemini tends to write a bit
    of reasoning/prose before settling into JSON, and the lower limit was
    cutting responses off mid-object on real intent-parsing prompts.
    """
    client = get_client()

    # Gemini has no separate system role in the basic generate_content call,
    # so we fold the system prompt in as a hard instruction up front, with an
    # explicit "JSON only" directive -- Gemini needs this to be more explicit
    # than Claude does, or it defaults to explaining itself first.
    combined_prompt = (
        f"{system_prompt}\n\n"
        "IMPORTANT: Respond with ONLY the raw JSON object. "
        "Do not include any explanation, reasoning steps, numbered lists, "
        "markdown code fences, or any text before or after the JSON.\n\n"
        f"{user_prompt}"
    )

    model = client.GenerativeModel(get_model())
    response = model.generate_content(
        combined_prompt,
        generation_config=client.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )

    return (response.text or "").strip()


def extract_json(text: str) -> dict:
    """Gemini is instructed to return only JSON, but this strips any stray
    markdown fences or preamble defensively before parsing."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Could not parse JSON from Gemini response:\n{text}")
