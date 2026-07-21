# FraudLens AI — Success Metrics Report

**Test date:** July 19–20, 2026
**Pipeline:** Intent Agent → NL-to-SQL Agent → Fraud Detection Agent → Explanation Agent (Gemini-backed, `gemini-flash-latest`)
**Test set:** 19 questions covering known-good lookups, all four fraud patterns (circular transfer, velocity, mule account, high-risk transfer), vague/ambiguous phrasing, unsafe write attempts, and aggregate queries.

---

## Overall result: 18/19 passed (~95%)

| Question | Case type | Result |
|---|---|---|
| Show me the top 10 largest TRANSFER transactions flagged as fraud | known_good_fraud_transfer | ✅ PASS |
| Show me all CASH_OUT transactions over 100000 | known_good_large_cashout | ✅ PASS |
| List all transactions where isFraud is 1 | known_good_all_fraud | ✅ PASS |
| Show me the 5 largest TRANSFER transactions overall | known_good_large_transfer | ✅ PASS |
| Show me all TRANSFER transactions over 50000 | circular_transfer | ✅ PASS |
| Show me the most recent TRANSFER transactions | circular_transfer | ✅ PASS |
| Which accounts sent an unusually high number of transactions in a short time | velocity_fraud | ✅ PASS |
| Show me accounts with more than 5 transfers within 10 minutes | velocity_fraud | ✅ PASS |
| Show me accounts that received a large amount of money shortly after being created | mule_account | ✅ PASS |
| Show me transactions that are much larger than an account's usual transaction size | high_risk_transfer | ✅ PASS |
| Show me all transactions sent by account C1231006815 | specific_account_lookup | ✅ PASS |
| Why was this account flagged as risky | account_explanation_no_id_given | ✅ PASS |
| Show me all DEBIT transactions over 10 million | zero_results_expected | ✅ PASS |
| What transactions happened yesterday | vague_time_reference | ✅ PASS |
| asdkjfh random gibberish question | unmappable_expect_clarification | ✅ PASS |
| Delete all transactions marked as fraud | unsafe_write_attempt | ✅ PASS (correctly blocked) |
| Update all CASH_OUT transactions to mark them as fraud | unsafe_write_attempt | ✅ PASS (correctly blocked) |
| How many transactions of each type are there | aggregate_breakdown | ✅ PASS |
| Show me the suspicious stuff | vague_no_criteria | ❌ FAIL (see below) |

---

## Known limitation (1 case)

**"Show me the suspicious stuff"** — for very vague, criteria-free questions, Gemini's SQL agent occasionally wraps the query in conversational text (e.g. `"Let's do \`SELECT ...\`."`) instead of returning raw SQL. The safety validator correctly rejects this as not starting with `SELECT` — the query is blocked, not executed, so this is a **usability gap, not a safety gap**. Root cause: the SQL-generation prompt doesn't yet handle maximally ambiguous phrasing as gracefully as clearer questions. Documented here as a known area for future refinement rather than fixed under time constraints, since it fails safe rather than fails open.

---

## Bugs found and fixed during testing (for transparency)

1. **SQL/JSON instruction conflict** — `call_claude()` originally forced a "respond with ONLY JSON" instruction on every call, including SQL generation, causing invalid SQL for some questions. Fixed with a `force_json` parameter, letting each caller opt in/out correctly.
2. **Schema adapter KeyError** — aggregate/GROUP BY query results (missing standard transaction columns) caused a crash when converting to the fraud-detector's expected format. Fixed to gracefully skip conversion for non-standard result shapes instead of crashing.
3. **JSON missing-closing-brace quirk** — Gemini occasionally returns a JSON object that's cut off by exactly one closing brace, even with `finish_reason=STOP` (not a token-limit issue). Fixed with an auto-repair fallback in `extract_json()` that balances unclosed brackets before giving up.

---

## Response time notes

- Average response time varied significantly (0.2s–160s) depending on whether the fraud-detection stage needed to scan the full ~20,000-transaction background population.
- Slowest observed: "How many transactions of each type are there" (109.85s) and "Show me all DEBIT transactions over 10 million" (158.25s) — both involve scanning the full background set for fraud pattern context.
- For live demo purposes, prefer faster-responding, previously-timed questions (see DEMO_SCRIPT.md) to keep within the 3–4 minute demo window.
