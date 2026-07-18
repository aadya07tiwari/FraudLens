"""
NL-to-SQL Agent
---------------
Takes the structured intent JSON from the Intent Agent and produces a
SAFE, read-only SQL query against the `transactions` table, then executes
it and returns the results.

Safety model (defense in depth):
1. Prompt tells the LLM the exact schema and that only SELECT is allowed.
2. Generated SQL is checked against an allow-list / deny-list of keywords
   before it ever touches the database.
3. The SQLite connection itself is opened in read-only mode (uri=...&mode=ro).
4. A LIMIT is enforced/injected server-side regardless of what the LLM wrote.
"""

import os
import re
import sqlite3

import pandas as pd

from .claude_client import call_claude

SCHEMA_DESCRIPTION = """
Table: transactions
Columns:
  - step              INTEGER  (time unit, 1 step = 1 hour)
  - type               TEXT     (one of CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER)
  - amount             REAL
  - nameOrig           TEXT     (origin account id)
  - oldbalanceOrg      REAL
  - newbalanceOrig     REAL
  - nameDest           TEXT     (destination account id)
  - oldbalanceDest     REAL
  - newbalanceDest     REAL
  - isFraud            INTEGER  (1 = known fraud, 0 = not)
  - isFlaggedFraud     INTEGER  (1 = PaySim's own rule flagged it, 0 = not)
"""

SQL_SYSTEM_PROMPT = f"""You are the NL-to-SQL Agent for FraudLens.

You will be given a structured JSON "intent" object describing what the \
user wants to know about financial transactions. You must write a single \
SQLite SELECT query against this schema:

{SCHEMA_DESCRIPTION}

STRICT RULES:
- Output ONLY the raw SQL query. No markdown fences, no explanation, no \
trailing semicolon commentary.
- The query MUST start with SELECT. Never use INSERT, UPDATE, DELETE, DROP, \
ALTER, CREATE, ATTACH, PRAGMA, or any multi-statement query.
- Only reference the `transactions` table and the columns listed above.
- Always include a LIMIT clause. If the intent implies a single aggregate \
number, LIMIT 1 is appropriate; otherwise default to LIMIT 100 unless the \
user clearly wants fewer/more (never exceed 500).
- If intent.entities.fraud_only is true, add a WHERE isFraud = 1 condition \
(combined with AND if other filters exist).
- If intent.entities.amount_filter is set, translate it into a WHERE clause \
on `amount`.
- If intent.entities.time_range is set, translate it into a WHERE clause on \
`step` (BETWEEN start_step AND end_step).
- If intent.entities.transaction_types is non-empty, filter `type IN (...)`.
- If intent.entities.account_ids is non-empty, filter on nameOrig or \
nameDest matching any of them.
- If intent.metrics contains aggregate functions like "count", "sum(amount)", \
"avg(amount)", reflect them in the SELECT clause with sensible aliases.

Return ONLY the SQL query text.
"""

# Keywords that must never appear in generated SQL, regardless of what the
# model produced. This is a defense-in-depth check, not the only check.
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|"
    r"REPLACE|TRUNCATE|GRANT|REVOKE|VACUUM|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


class UnsafeSQLError(Exception):
    pass


def generate_sql(intent: dict, max_row_limit: int = 200) -> str:
    """Calls the LLM to turn an intent dict into a SQL string, then validates it."""
    import json as _json

    user_prompt = f"Intent JSON:\n{_json.dumps(intent, indent=2)}"
    raw_sql = call_claude(
        system_prompt=SQL_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=800,
        temperature=0.0,
    )
    sql = _clean_sql(raw_sql)
    validate_sql(sql)
    sql = enforce_row_limit(sql, max_row_limit)
    return sql


def _clean_sql(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(sql)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    cleaned = cleaned.rstrip(";").strip()
    return cleaned


def validate_sql(sql: str) -> None:
    """Raises UnsafeSQLError if the query fails any safety check."""
    stripped = sql.strip()

    if not re.match(r"^\s*SELECT\b", stripped, re.IGNORECASE):
        raise UnsafeSQLError("Only SELECT queries are permitted.")

    if ";" in stripped:
        raise UnsafeSQLError("Multiple statements are not permitted.")

    if _FORBIDDEN_KEYWORDS.search(stripped):
        raise UnsafeSQLError("Query contains a forbidden keyword.")

    if "transactions" not in stripped.lower():
        raise UnsafeSQLError("Query must reference the transactions table.")

    # Very light table-scope check: disallow references to sqlite_master or
    # other tables/pragmas that could leak schema/data outside scope.
    if re.search(r"\bsqlite_master\b", stripped, re.IGNORECASE):
        raise UnsafeSQLError("Query must not reference sqlite_master.")


def enforce_row_limit(sql: str, max_row_limit: int) -> str:
    """Ensures a LIMIT clause exists and never exceeds max_row_limit."""
    match = re.search(r"\bLIMIT\s+(\d+)\b", sql, re.IGNORECASE)
    if match:
        current_limit = int(match.group(1))
        if current_limit > max_row_limit:
            sql = re.sub(r"\bLIMIT\s+\d+\b", f"LIMIT {max_row_limit}", sql, flags=re.IGNORECASE)
    else:
        sql = f"{sql} LIMIT {max_row_limit}"
    return sql


def run_query(sql: str, db_path: str) -> pd.DataFrame:
    """Executes a validated SELECT query against a read-only SQLite connection."""
    validate_sql(sql)  # defense in depth: re-check right before execution

    abs_path = os.path.abspath(db_path)
    uri = f"file:{abs_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df
