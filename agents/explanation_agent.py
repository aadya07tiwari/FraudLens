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

Section 6 (generate_report) takes that same evidence object plus the
explanation paragraph and formats both into a Markdown report. It's
pure formatting - no model call, no new claims - so it never needs to
raise ValueError the way explain_evidence() does; there's nothing to
validate that check_evidence() hasn't already covered upstream.
"""

import json
import os
import re
from datetime import datetime, date
from typing import Any, Dict, List, Union
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


# ---------------------------------------------------------------------------
# 6. REPORT GENERATION
#    Pure formatting: no model call, no new claims. Takes the same
#    evidence object explain_account() builds, plus the explanation
#    paragraph explain_findings() already produced, and lays both out as
#    a Markdown report. Field names below match fraud_detection_agent.py's
#    real evidence dicts exactly (see its module docstring / __main__):
#      - circular_transfer   -> "accounts_involved" (list), no absolute timestamp
#      - velocity_fraud      -> "account" (str), "window_start"/"window_end"
#      - mule_account        -> "account" (str), "created_at" + "contributing_transactions"
#      - high_risk_transfer  -> "account" (str), no absolute timestamp
# ---------------------------------------------------------------------------

# Risk bands only ever map to human-review/escalation actions - never an
# automated account action (no auto-freeze, auto-block, etc.).
_RISK_BANDS = [
    (90, "Critical"),
    (70, "High"),
    (40, "Medium"),
    (0, "Low"),
]

_RECOMMENDED_ACTIONS = {
    "Critical": [
        "Flag for immediate manual review by a senior fraud analyst",
        "Escalate to the compliance/investigations team",
        "Submit a manual hold request to the account's risk team (do not auto-freeze)",
        "Cross-check counterparties against known mule-account watchlists",
    ],
    "High": [
        "Flag for manual review within 24 hours",
        "Escalate to a fraud analyst for deeper investigation",
        "Request additional identity/transaction verification from the account holder",
    ],
    "Medium": [
        "Flag for manual review during the next standard review cycle",
        "Monitor the account for repeat pattern triggers over the next 30 days",
    ],
    "Low": [
        "Log for reference; no immediate action required",
        "Include in periodic batch review if similar patterns recur",
    ],
}


def _risk_label(risk_score: Union[int, float]) -> str:
    for threshold, label in _RISK_BANDS:
        if risk_score >= threshold:
            return label
    return "Low"


def _fmt_ts(value: Any) -> str:
    """Format a timestamp-ish value for display; anything else -> str()."""
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    return str(value)


def _extract_accounts(primary_account: Any, evidence_list: List[Dict]) -> List[str]:
    """
    Collect every account id mentioned across the evidence entries.
    Matches fraud_detection_agent.py's real keys:
      - "account"           -> velocity_fraud, mule_account, high_risk_transfer (str)
      - "accounts_involved" -> circular_transfer (list of 3)
    """
    accounts = []
    if primary_account:
        accounts.append(str(primary_account))

    for item in evidence_list or []:
        if not isinstance(item, dict):
            continue
        if item.get("account"):
            accounts.append(str(item["account"]))
        if item.get("accounts_involved"):
            accounts.extend(str(a) for a in item["accounts_involved"])

    seen = set()
    ordered = []
    for a in accounts:
        if a not in seen:
            seen.add(a)
            ordered.append(a)
    return ordered


def _extract_timeline(evidence_list: List[Dict]) -> List[Dict]:
    """
    Build a chronological list of events from evidence entries.

    Only two of the four detectors carry an absolute timestamp on the
    evidence dict itself:
      - velocity_fraud -> "window_start" / "window_end"
      - mule_account   -> "created_at" is account creation, not the
                          event itself; the more representative event
                          time is the last entry in
                          "contributing_transactions"
    circular_transfer and high_risk_transfer evidence dicts only carry
    elapsed/relative minutes, no absolute timestamp - those go in the
    untimed bucket rather than being guessed at.
    """
    timed, untimed = [], []

    for item in evidence_list or []:
        if not isinstance(item, dict):
            continue
        desc = item.get("evidence") or str(item)
        pattern = item.get("pattern")

        ts_val = None
        if pattern == "velocity_fraud":
            ts_val = item.get("window_start")
        elif pattern == "mule_account":
            contributing = item.get("contributing_transactions") or []
            if contributing:
                ts_val = contributing[-1].get("timestamp")
            else:
                ts_val = item.get("created_at")

        entry = {"pattern": pattern, "description": desc, "raw_ts": ts_val}
        (timed if ts_val is not None else untimed).append(entry)

    def sort_key(e):
        ts = e["raw_ts"]
        return ts.isoformat() if isinstance(ts, (datetime, date)) else str(ts)

    timed.sort(key=sort_key)
    return timed + untimed


def generate_report(evidence: Dict, explanation: str, risk_score: Union[int, float]) -> str:
    """
    Format one account's evidence + Claude's grounded explanation into a
    Markdown report with sections: Fraud Risk Level, Accounts Involved,
    Evidence, Timeline, Recommended Actions.

    Parameters
    ----------
    evidence : dict
        Same shape explain_account() builds, e.g.:
        {
            "account": "ACC_MULE",
            "risk_score": 35,
            "rules_fired": ["mule_account"],
            "evidence": [ {...one detector's evidence dict...}, ... ]
        }
    explanation : str
        The grounded paragraph from explain_findings()/explain_evidence()
        (its "summary" field).
    risk_score : int
        0-100. Passed separately so this function has no hidden
        dependency on it also being inside `evidence`.

    Returns
    -------
    str : Markdown report.
    """
    account_id = evidence.get("account")
    rules_fired = evidence.get("rules_fired") or []
    evidence_list = evidence.get("evidence") or []

    risk_label = _risk_label(risk_score)
    accounts = _extract_accounts(account_id, evidence_list)
    timeline = _extract_timeline(evidence_list)

    lines = []

    lines.append(f"# Fraud Report — {account_id or 'Unknown Account'}")
    lines.append("")

    lines.append("## Fraud Risk Level")
    lines.append("")
    lines.append(f"**{risk_label}** — risk score {risk_score}/100")
    if rules_fired:
        lines.append("")
        lines.append("Rules fired: " + ", ".join(str(r) for r in rules_fired))
    lines.append("")

    lines.append("## Accounts Involved")
    lines.append("")
    if accounts:
        lines.extend(f"- {a}" for a in accounts)
    else:
        lines.append("- No account identifiers found in evidence.")
    lines.append("")

    lines.append("## Evidence")
    lines.append("")
    if evidence_list:
        for item in evidence_list:
            if isinstance(item, dict):
                pattern = item.get("pattern")
                desc = item.get("evidence") or str(item)
            else:
                pattern, desc = None, str(item)
            lines.append(f"- **{pattern}**: {desc}" if pattern else f"- {desc}")
    else:
        lines.append("- No supporting evidence entries were provided.")
    lines.append("")

    if explanation:
        lines.append("**Summary:** " + explanation.strip())
        lines.append("")

    lines.append("## Timeline")
    lines.append("")
    if timeline:
        for entry in timeline:
            ts_display = _fmt_ts(entry["raw_ts"]) if entry["raw_ts"] is not None else "Time not recorded"
            pattern = f" ({entry['pattern']})" if entry["pattern"] else ""
            lines.append(f"- `{ts_display}`{pattern}: {entry['description']}")
    else:
        lines.append("- No timestamped events available.")
    lines.append("")

    lines.append("## Recommended Actions")
    lines.append("")
    for a in _RECOMMENDED_ACTIONS.get(risk_label, _RECOMMENDED_ACTIONS["Low"]):
        lines.append(f"- {a}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 7. REPORT EXPORT
#    Turns generate_report()'s Markdown string into a downloadable file.
#    Pure formatting on top of pure formatting - no new claims, no model
#    call, and it only parses the specific Markdown constructs
#    generate_report() actually emits (h1 "# ", h2 "## ", bullets "- ",
#    bold "**text**", backtick spans "`text`"). It is not a general
#    Markdown-to-PDF converter.
#
#    fmt="md"  -> writes the Markdown string as-is (fastest MVP option)
#    fmt="txt" -> writes a plain-text version with the markup stripped
#    fmt="pdf" -> renders a lightly styled PDF (headings, bullets, a
#                 colored risk-level label) via reportlab
# ---------------------------------------------------------------------------

_RISK_COLORS = {
    "Critical": "#B91C1C",  # red
    "High": "#C2410C",      # orange
    "Medium": "#B45309",    # amber
    "Low": "#15803D",       # green
}


def _strip_markdown(report_md: str) -> str:
    """Best-effort plain-text version of the report for fmt='txt'."""
    lines = []
    for line in report_md.split("\n"):
        line = re.sub(r"^#{1,6}\s*", "", line)          # headings
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)      # bold
        line = re.sub(r"`([^`]+)`", r"\1", line)          # code spans
        lines.append(line)
    return "\n".join(lines)


def _inline_markup(text: str) -> str:
    """Convert the report's Markdown inline syntax into reportlab's XML markup."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)               # bold
    text = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', text)  # code
    for label, hex_color in _RISK_COLORS.items():
        text = text.replace(f"<b>{label}</b>", f'<font color="{hex_color}"><b>{label}</b></font>')
    return text


def _markdown_report_to_pdf(report_md: str, output_path: str) -> str:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FraudLensTitle", parent=styles["Title"],
        textColor=colors.HexColor("#1E293B"), fontSize=18, spaceAfter=4,
    )
    h2_style = ParagraphStyle(
        "FraudLensH2", parent=styles["Heading2"],
        textColor=colors.HexColor("#334155"), spaceBefore=14, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "FraudLensBody", parent=styles["Normal"], fontSize=10, leading=14,
    )

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    story = []
    bullet_buffer = []

    def flush_bullets():
        if bullet_buffer:
            story.append(ListFlowable(
                [ListItem(Paragraph(_inline_markup(b), body_style), spaceAfter=3)
                 for b in bullet_buffer],
                bulletType="bullet", leftIndent=18,
            ))
            bullet_buffer.clear()

    for raw_line in report_md.split("\n"):
        line = raw_line.rstrip()

        if line.startswith("# "):
            flush_bullets()
            story.append(Paragraph(_inline_markup(line[2:]), title_style))
            story.append(HRFlowable(width="100%", color=colors.HexColor("#CBD5E1"), thickness=1))
            story.append(Spacer(1, 8))
        elif line.startswith("## "):
            flush_bullets()
            story.append(Paragraph(_inline_markup(line[3:]), h2_style))
        elif line.startswith("- "):
            bullet_buffer.append(line[2:])
        elif line.strip() == "":
            flush_bullets()
            story.append(Spacer(1, 4))
        else:
            flush_bullets()
            story.append(Paragraph(_inline_markup(line), body_style))

    flush_bullets()
    doc.build(story)
    return output_path


def export_report(report_md: str, output_path: str, fmt: str = "pdf") -> str:
    """
    Write generate_report()'s Markdown output to a downloadable file.

    Parameters
    ----------
    report_md : str
        Output of generate_report().
    output_path : str
        Where to write the file. Its extension is corrected to match
        `fmt` if they don't already match.
    fmt : str
        One of "pdf", "md", "txt". Default "pdf". If reportlab isn't
        installed and fmt="pdf", raises ImportError with a suggestion to
        install it or fall back to fmt="md"/"txt" for a quick MVP export.

    Returns
    -------
    str : the path actually written to.
    """
    fmt = fmt.lower().lstrip(".")
    if fmt not in ("pdf", "md", "txt"):
        raise ValueError(f"Unsupported fmt {fmt!r} - use 'pdf', 'md', or 'txt'.")

    base, _ = os.path.splitext(output_path)
    output_path = f"{base}.{fmt}"

    if fmt == "md":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        return output_path

    if fmt == "txt":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(_strip_markdown(report_md))
        return output_path

    # fmt == "pdf"
    try:
        return _markdown_report_to_pdf(report_md, output_path)
    except ImportError as e:
        raise ImportError(
            "PDF export needs reportlab (`pip install reportlab`). "
            "For a quick MVP export without it, call "
            "export_report(report_md, output_path, fmt='md') or fmt='txt' instead."
        ) from e


if __name__ == "__main__":
    try:
        result = explain_evidence(EXAMPLE_EVIDENCE)
        print(result["summary"])
        if not result["grounded"]:
            print(f"\n[WARNING] Ungrounded numbers: {result['ungrounded_numbers']}")
            print(f"[WARNING] Ungrounded IDs: {result['ungrounded_ids']}")

        report_md = generate_report(
            evidence=EXAMPLE_EVIDENCE,
            explanation=result["summary"],
            risk_score=EXAMPLE_EVIDENCE["risk_score"],
        )
        print("\n" + "=" * 60)
        print(report_md)

        pdf_path = export_report(report_md, "fraud_report_ACC_A", fmt="pdf")
        print(f"\nWrote {pdf_path}")
    except ValueError as e:
        print(f"Blocked: {e}")