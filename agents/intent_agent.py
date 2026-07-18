"""
Intent Agent
------------
Takes a user's natural-language question and turns it into a structured
JSON "intent" object: what the user is asking for, which entities/filters
are involved, and what kind of analysis is needed. This structured intent
is what gets handed to the NL-to-SQL Agent, instead of raw free text.
"""

from .claude_client import call_claude, extract_json

INTENT_SYSTEM_PROMPT = """You are the Intent Agent for FraudLens, a fraud-detection assistant \
for financial transaction data (PaySim schema: step, type, amount, nameOrig, \
oldbalanceOrg, newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, \
isFraud, isFlaggedFraud).

Your ONLY job is to read a user's question and output a structured JSON \
description of their intent. You do NOT write SQL and you do NOT answer \
the question yourself.

Output STRICT JSON only, with this exact shape (no markdown, no commentary):

{
  "task": "one of: lookup | aggregate | trend | comparison | fraud_flagged | unknown",
  "summary": "a one-sentence restatement of what the user wants",
  "entities": {
    "account_ids": [],
    "transaction_types": [],
    "amount_filter": null,
    "time_range": null,
    "fraud_only": false
  },
  "metrics": [],
  "clarification_needed": null
}

Rules:
- "task" categorizes the request: "lookup" (find specific rows/accounts), \
"aggregate" (counts/sums/averages), "trend" (over time/steps), \
"comparison" (between groups, e.g. fraud vs non-fraud), \
"fraud_flagged" (specifically about isFraud / isFlaggedFraud), or \
"unknown" if the question is unrelated to the transaction data.
- "transaction_types" must only contain values from: CASH_IN, CASH_OUT, \
DEBIT, PAYMENT, TRANSFER (uppercase). Omit anything else.
- "amount_filter" should be an object like {"op": ">", "value": 100000} or \
null if no amount condition is mentioned. Valid "op": ">", "<", ">=", "<=", "=".
- "time_range" should be an object like {"start_step": 1, "end_step": 100} \
if the user gives a step/time window, else null.
- "fraud_only" is true only if the user explicitly wants fraudulent \
transactions.
- "metrics" is a list of requested aggregates, e.g. ["count"], ["sum(amount)"], \
["avg(amount)"]. Empty list if not an aggregate question.
- If the question is too vague to proceed (e.g. missing which account, or \
ambiguous timeframe when one is clearly required), set "clarification_needed" \
to a short question to ask the user; otherwise set it to null.
- If the question has nothing to do with transactions/fraud, set task to \
"unknown" and clarification_needed to a short note explaining that.

Return ONLY the JSON object. No prose before or after it.
"""


def parse_intent(user_question: str) -> dict:
    """Calls the LLM to convert a natural-language question into a structured
    intent dict. Raises ValueError if the output can't be parsed."""
    raw = call_claude(
        system_prompt=INTENT_SYSTEM_PROMPT,
        user_prompt=user_question,
        max_tokens=1024,
        temperature=0.0,
    )
    intent = extract_json(raw)
    _validate_intent(intent)
    return intent


def _validate_intent(intent: dict) -> None:
    """Light schema validation so downstream agents can trust the shape."""
    required_keys = {"task", "summary", "entities", "metrics", "clarification_needed"}
    missing = required_keys - set(intent.keys())
    if missing:
        raise ValueError(f"Intent JSON missing required keys: {missing}")

    valid_tasks = {"lookup", "aggregate", "trend", "comparison", "fraud_flagged", "unknown"}
    if intent["task"] not in valid_tasks:
        intent["task"] = "unknown"

    entities = intent.get("entities", {})
    entities.setdefault("account_ids", [])
    entities.setdefault("transaction_types", [])
    entities.setdefault("amount_filter", None)
    entities.setdefault("time_range", None)
    entities.setdefault("fraud_only", False)

    valid_types = {"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}
    entities["transaction_types"] = [
        t for t in entities.get("transaction_types", []) if t in valid_types
    ]