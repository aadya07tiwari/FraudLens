"""
Thin wrapper around Google AI Studio's Gemini API, shared by the Intent
Agent and the NL-to-SQL Agent. Centralizing this here means the model
name, retry logic, and JSON-extraction logic only need to live in one
place.

NOTE: this replaces the original Anthropic-backed version. Function
names AND signatures are kept identical (call_claude(system_prompt,
user_prompt, max_tokens, temperature) -> str, and extract_json(text) ->
dict) so intent_agent.py and sql_agent.py do not need any changes.
"""
import json
import os
import re

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_model_cache = {}


def _get_api_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key. "
            "Get one free at https://aistudio.google.com/apikey"
        )
    return api_key


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def _get_model(system_prompt: str):
    genai.configure(api_key=_get_api_key())
    model_name = get_model_name()
    cache_key = (model_name, system_prompt)

    if cache_key not in _model_cache:
        _model_cache[cache_key] = genai.GenerativeModel(
            model_name, system_instruction=system_prompt
        )
    return _model_cache[cache_key]


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> str:
    model = _get_model(system_prompt)
    response = model.generate_content(
        user_prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return response.text.strip()


def extract_json(text: str) -> dict:
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


if __name__ == "__main__":
    print(f"Using model: {get_model_name()}\n")

    reply = call_claude(
        system_prompt="You respond only with valid JSON, nothing else.",
        user_prompt='Reply with only this JSON: {"status": "ok", "provider": "gemini"}',
    )
    print("Raw response:", reply)

    parsed = extract_json(reply)
    print("Parsed JSON:", parsed)
