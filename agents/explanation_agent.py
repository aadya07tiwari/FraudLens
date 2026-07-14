"""
FraudLens AI - Explanation & Reporting Layer (Member D)
----------------------------------------------------------
Consumes the output of detect_fraud_patterns() in
agents/fraud_detection_agent.py (Member B) and turns one account's
result into a plain-English compliance paragraph.

KEY DESIGN POINT
-----------------
Member B's detectors already produce a grounded, human-readable
"evidence" one-liner for every pattern that fired (e.g. "ACC_A sent
250,000.00 to ACC_B, who sent 240,000.00 to ACC_C..."). This layer's
job is NOT to reason about fraud, or even to summarize raw numbers
from scratch - it's to combine those already-grounded sentences (plus
the risk_score and rules_fired list) into one coherent paragraph,
without introducing any claim, cause, or number that isn't already
present in the evidence object.
"""

import json
import os
import re
from datetime import datetime
import requests  # swap for anthropic SDK if you prefer


# ---------------------------------------------------------------------------
# 1. EXAMPLE EVIDENCE OBJECT
#    This matches the REAL shape of detect_fraud_patterns()["accounts"][acct],
#    with the account id folded in. Built from the circular-transfer example
#    in fraud_detection_agent.py's own __main__ test block.
# ---------------------------------------------------------------------------

EXAMPLE_EVIDENCE = {
    "account": "ACC_A",
    "risk_score": 40,
    "rules_fired": ["circular_transfer"],
    "evidence": [
        {
            "pattern": "circular_transfer",
            "accounts_involved": ["ACC_A", "ACC_B", "ACC_C"],
            "cycle_txn_ids": ["T1", "T2", "T3"],
            "cycle_amounts": [250000, 240000, 235000],
            "time_gaps_minutes": [10.0, 10.0],
            "total_elapsed_minutes": 20.0,
            "evidence": (
                "ACC_A sent 250,000.00 to ACC_B, who sent 240,000.00 to "
                "ACC_C 10 min later, who sent 235,000.00 back to ACC_A "
                "10 min after that (total: 20 min)."
            ),
        }
    ],
}


# ---------------------------------------------------------------------------
# 2. FIELD CRITICALITY
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ["account", "risk_score", "rules_fired", "evidence"]


def check_evidence(evidence: dict) -> list:
    """
    Return a list of problems with the evidence object. Empty list = OK
    to proceed. Checks both presence AND that rules_fired/evidence aren't
    just empty lists (an account with 0 hits shouldn't reach this layer
    at all - that's a caller bug, not something to paper over).
    """
    problems = [f for f in REQUIRED_FIELDS if f not in evidence or evidence[f] in (None, "")]
    if "rules_fired" in evidence and not evidence["rules_fired"]:
        problems.append("rules_fired (empty)")
    if "evidence" in evidence and not evidence["evidence"]:
        problems.append("evidence (empty)")
    return problems


# ---------------------------------------------------------------------------
# 3. PROMPT TEMPLATE
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the explanation layer for FraudLens AI. You do not
detect fraud yourself. Member B's rule-based detectors already produced
every fact you're allowed to use, including a grounded one-line "evidence"
string for each pattern that fired.

Rules:
1. Use ONLY the fields present in the evidence object below. Every
   account, amount, transaction ID, timestamp, gap, and score you mention
   must come directly from this object.
2. Do not add causes, motives, or context beyond what's given. Do not say
   things like "this is consistent with money laundering" - state only
   what the data shows.
3. Each item in the "evidence" list already contains a pattern-specific
   one-line summary (its own "evidence" field). Base your paragraph on
   these - you may reword them for flow and combine several into one
   paragraph, but do not introduce claims that go beyond what they state.
4. Always report the exact risk_score, and name every rule in rules_fired.
5. If more than one pattern fired, cover all of them - don't focus on
   just one and drop the rest.
6. Do not compute new numbers (percentages, sums, differences) unless
   that exact number already appears in the evidence object.
7. Output one paragraph, 3-6 sentences, no bullet points, no markdown,
   written for a compliance officer deciding whether to escalate this
   account.
"""

USER_PROMPT_TEMPLATE = """Account evidence object:
{evidence_json}

Write the compliance summary."""


def _json_default(obj):
    """Handle datetime objects, which Member B's output includes raw."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


# ---------------------------------------------------------------------------
# 4. GROUNDING CHECK
# ---------------------------------------------------------------------------

def _flatten_numbers(obj) -> set:
    """Collect every number found anywhere in a (possibly nested) evidence object."""
    found = set()
    if isinstance(obj, dict):
        for v in obj.values():
            found |= _flatten_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= _flatten_numbers(v)
    elif isinstance(obj, bool):
        pass  # bool is technically an int subclass in Python - skip it
    elif isinstance(obj, (int, float)):
        found.add(float(obj))
    return found


def check_grounding(text: str, evidence: dict) -> list:
    """
    Return a list of numbers found in `text` that do NOT appear anywhere
    in `evidence`. Empty list = every number in the output is traceable
    back to the source data.
    """
    evidence_numbers = _flatten_numbers(evidence)
    text_numbers = {float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*\.?\d*", text)}

    ungrounded = []
    for n in text_numbers:
        if not any(abs(n - e) < 0.01 for e in evidence_numbers):
            ungrounded.append(n)
    return ungrounded


def _flatten_strings(obj) -> set:
    """Collect every string value found anywhere in a (possibly nested) evidence object."""
    found = set()
    if isinstance(obj, dict):
        for v in obj.values():
            found |= _flatten_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= _flatten_strings(v)
    elif isinstance(obj, str):
        found.add(obj)
    return found


# Matches ID-like tokens: account IDs (ACC_A, ACC-4471, ACC102), transaction
# IDs (T1, TXN-88213), rule names, etc. - anything that looks like an
# identifier rather than an ordinary English word, so we don't flag words
# like "The" or "Account" as ungrounded.
_ID_PATTERN = re.compile(r"\b[A-Z]{2,}[A-Z0-9_-]*\b")


def check_account_ids(text: str, evidence: dict) -> list:
    """
    Return a list of ID-like tokens (account IDs, transaction IDs, rule
    names) found in `text` that do NOT appear anywhere in `evidence`.
    Empty list = every identifier in the output traces back to the
    source data.
    """
    evidence_strings = _flatten_strings(evidence)
    candidates = set(_ID_PATTERN.findall(text))

    ungrounded = [c for c in candidates if c not in evidence_strings]
    return ungrounded


def check_grounded(text: str, evidence: dict) -> dict:
    """
    Run both grounding checks (numbers + account/transaction IDs) and
    return a single combined result. Never silently passes - always
    reports what it found, even if empty.

    Returns:
        {
            "grounded": <True/False>,
            "ungrounded_numbers": [...],
            "ungrounded_ids": [...]
        }
    """
    ungrounded_numbers = check_grounding(text, evidence)
    ungrounded_ids = check_account_ids(text, evidence)

    return {
        "grounded": len(ungrounded_numbers) == 0 and len(ungrounded_ids) == 0,
        "ungrounded_numbers": ungrounded_numbers,
        "ungrounded_ids": ungrounded_ids,
    }


# ---------------------------------------------------------------------------
# 5. THE FUNCTION
# ---------------------------------------------------------------------------

def explain_evidence(evidence: dict, api_key: str = None) -> dict:
    """
    Convert one account's fraud-evidence object into a plain-English
    compliance paragraph. Raises ValueError if required fields are
    missing rather than letting the model quietly paper over the gap.

    Returns:
        {
            "summary": <the paragraph>,
            "grounded": <True/False>,
            "ungrounded_numbers": [<numbers in the text with no source>],
            "ungrounded_ids": [<account/txn IDs in the text with no source>]
        }
    A caller should treat grounded == False as "do not show this to a
    compliance officer without review."
    """
    problems = check_evidence(evidence)
    if problems:
        raise ValueError(f"Cannot generate explanation - problems: {problems}")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        evidence_json=json.dumps(evidence, indent=2, default=_json_default)
    )

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key or os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 300,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        },
    )
    response.raise_for_status()
    data = response.json()

    text_blocks = [b["text"] for b in data["content"] if b["type"] == "text"]
    summary = "\n".join(text_blocks).strip()

    grounding = check_grounded(summary, evidence)

    return {
        "summary": summary,
        "grounded": grounding["grounded"],
        "ungrounded_numbers": grounding["ungrounded_numbers"],
        "ungrounded_ids": grounding["ungrounded_ids"],
    }


def explain_findings(evidence: dict, api_key: str = None) -> dict:
    """
    Public entry point: calls the Claude API with the FraudLens prompt
    template and returns the explanation paragraph (plus grounding check).
    This is just a named wrapper around explain_evidence() - same logic,
    kept as a separate name since that's the interface other parts of the
    app (or teammates) are expected to call.
    """
    return explain_evidence(evidence, api_key=api_key)


def explain_account(account_id: str, fraud_patterns_result: dict, api_key: str = None) -> dict:
    """
    Convenience wrapper that plugs directly into Member B's real output.

    Usage:
        result = detect_fraud_patterns(transactions, accounts=accounts)
        summary = explain_account("ACC_A", result)

    Raises KeyError if account_id has no hits in fraud_patterns_result
    (i.e. it was never flagged - there's nothing to explain).
    """
    account_result = fraud_patterns_result["accounts"][account_id]
    evidence = {"account": account_id, **account_result}
    return explain_evidence(evidence, api_key=api_key)


if __name__ == "__main__":
    try:
        result = explain_evidence(EXAMPLE_EVIDENCE)
        print(result["summary"])
        if not result["grounded"]:
            print(f"\n[WARNING] Ungrounded numbers: {result['ungrounded_numbers']}")
            print(f"[WARNING] Ungrounded IDs: {result['ungrounded_ids']}")
    except ValueError as e:
        print(f"Blocked: {e}")
