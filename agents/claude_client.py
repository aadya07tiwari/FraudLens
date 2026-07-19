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


def call_claude(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.0,
    force_json: bool = True,
) -> str:
    """Sends a single-turn request to Gemini and returns the raw text response.

    Kept the name `call_claude` so intent_agent.py / sql_agent.py don't need
    to change their imports.

    max_tokens default raised from 1024 -> 2048: Gemini tends to write a bit
    of reasoning/prose before settling into JSON, and the lower limit was
    cutting responses off mid-object on real intent-parsing prompts.

    force_json: defaults to True so intent_agent.py (which needs JSON back)
    keeps working with zero changes on its end. sql_agent.py's SQL-generation
    call should pass force_json=False -- forcing JSON mode on a "write me a
    SQL query" prompt was the bug: Gemini would try to satisfy both the
    "return SQL" instruction and the "ONLY raw JSON" instruction at once and
    produce something that was neither valid SQL nor valid JSON.

    When force_json=True, JSON-ness is enforced structurally via Gemini's
    response_mime_type="application/json" generation config, not just via
    prompt wording. That's a hard guarantee from the API rather than an
    instruction Gemini can drift away from, which is what was causing the
    intermittent "Could not parse JSON" failures.
    """
    client = get_client()

    if force_json:
        # Gemini has no separate system role in the basic generate_content
        # call, so we fold the system prompt in as a hard instruction up
        # front. The prompt wording is now a *belt-and-suspenders* backup --
        # the real guarantee is response_mime_type="application/json" below.
        combined_prompt = (
            f"{system_prompt}\n\n"
            "IMPORTANT: Respond with ONLY the raw JSON object. "
            "Do not include any explanation, reasoning steps, numbered lists, "
            "markdown code fences, or any text before or after the JSON.\n\n"
            f"{user_prompt}"
        )
        generation_config = client.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            response_mime_type="application/json",
        )
    else:
        # No JSON instruction at all -- let the caller's system_prompt (e.g.
        # "return only a SQL query") stand on its own without a conflicting
        # "ONLY raw JSON" directive layered on top of it.
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        generation_config = client.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

    model = client.GenerativeModel(get_model())
    response = model.generate_content(
        combined_prompt,
        generation_config=generation_config,
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



def extract_sql(text: str) -> str:
    """Strips markdown code fences from a plain-SQL response. sql_agent.py
    should call this (not extract_json) on the result of a force_json=False
    call_claude() invocation."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(sql)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned

