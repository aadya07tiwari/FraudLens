"""
test_runner.py

FraudLens AI — End-to-end pipeline test runner (Member E, Task 3)

WHAT THIS TESTS
----------------
This is different from Member B's paysim_eval.py, which tests the fraud
DETECTOR's own accuracy against PaySim's isFraud label. This script tests
the FULL USER-FACING PIPELINE: a plain-English question goes in, and each
stage is checked end to end --

    question -> Intent Agent -> NL-to-SQL Agent -> SQL execution
             -> schema adapter -> Fraud Detection Agent -> Explanation Agent

-- logging whether each stage succeeded, how long the whole thing took,
and (once Member D's Explanation Agent is pushed) what the final
explanation says.

UPDATE: Member D's Explanation Agent (agents/explanation_agent.py) is now
available and wired in for real -- explain_findings() is called with each
question's top-risk-account evidence, and the grounding check it returns
(grounded / ungrounded_numbers / ungrounded_ids) is logged too, since an
ungrounded explanation is itself a meaningful failure mode worth catching.

IMPORTANT CAVEAT: agents/explanation_agent.py calls Anthropic's API
directly (its own hardcoded requests.post to api.anthropic.com), separate
from agents/claude_client.py. This means it does NOT automatically pick
up the team's Gemini switch -- it still needs ANTHROPIC_API_KEY specifically
and its own separate conversion if/when Member D updates it for Gemini.
Keep both keys available in your .env until that's resolved, or this
stage will fail even if the rest of the pipeline is running on Gemini.

USAGE
-----
    python test_runner.py

Add or edit questions in TEST_QUESTIONS below. Aim for 15-20 covering a
mix of: circular transfer cases, velocity/mule/high-risk cases, vague
questions that should ask for clarification, and at least one question
expected to return zero results.
"""

import time
import traceback
from dataclasses import dataclass, field

from agents.intent_agent import parse_intent
from agents.sql_agent import generate_sql, run_query, UnsafeSQLError
from agents.fraud_detection_agent import detect_fraud_patterns
from agents.explanation_agent import explain_findings
from schema_adapter import rows_to_transactions_format

DB_PATH = "db/fraudlens_demo.db"
MAX_ROW_LIMIT = 200

# A background population of transactions is needed for fraud detection
# to have surrounding context (detectors look at an account's history,
# not just the rows a single question's SQL query returns). This pulls
# a broad slice of the demo DB once, rather than re-querying per question.
BACKGROUND_POPULATION_SQL = "SELECT * FROM transactions LIMIT 20000"


@dataclass
class TestResult:
    question: str
    case_type: str = ""
    intent_ok: bool = False
    sql_ok: bool = False
    query_ok: bool = False
    fraud_detection_ok: bool = False
    explanation_ok: bool = False
    explanation_grounded: bool = True
    explanation_summary: str = ""
    ungrounded_numbers: list = field(default_factory=list)
    ungrounded_ids: list = field(default_factory=list)
    row_count: int = 0
    top_risk_score: int = 0
    rules_fired: list = field(default_factory=list)
    response_time_seconds: float = 0.0
    error: str = ""

    @property
    def passed(self) -> bool:
        """A question 'passes' if every stage that SHOULD run for it
        completed without error AND (when an explanation was generated)
        the explanation was fully grounded in the source evidence.
        Vague/unmappable questions are expected to stop at the intent
        stage with a clarification request -- that counts as a pass too,
        since asking for clarification is correct behavior, not a failure."""
        if self.error:
            return False
        if not self.intent_ok:
            return False
        if self.explanation_ok and not self.explanation_grounded:
            return False
        return True


TEST_QUESTIONS = [
    # --- CONFIRMED PASSING (15) — commented out to save quota ---
    # {"question": "Show me the top 10 largest TRANSFER transactions flagged as fraud",
    #  "case_type": "known_good_fraud_transfer"},
    # {"question": "Show me all CASH_OUT transactions over 100000",
    #  "case_type": "known_good_large_cashout"},
    # {"question": "List all transactions where isFraud is 1",
    #  "case_type": "known_good_all_fraud"},
    # {"question": "Show me the 5 largest TRANSFER transactions overall",
    #  "case_type": "known_good_large_transfer"},
    # {"question": "Show me all TRANSFER transactions over 50000",
    #  "case_type": "circular_transfer"},
    # {"question": "Show me the most recent TRANSFER transactions",
    #  "case_type": "circular_transfer"},
    # {"question": "Which accounts sent an unusually high number of transactions in a short time",
    #  "case_type": "velocity_fraud"},
    # {"question": "Show me accounts with more than 5 transfers within 10 minutes",
    #  "case_type": "velocity_fraud"},
    # {"question": "Show me accounts that received a large amount of money shortly after being created",
    #  "case_type": "mule_account"},
    # {"question": "Show me transactions that are much larger than an account's usual transaction size",
    #  "case_type": "high_risk_transfer"},
    # {"question": "Show me all transactions sent by account C1231006815",
    #  "case_type": "specific_account_lookup"},
    # {"question": "Why was this account flagged as risky",
    #  "case_type": "account_explanation_no_id_given"},
    # {"question": "Show me all DEBIT transactions over 10 million",
    #  "case_type": "zero_results_expected"},
    # {"question": "What transactions happened yesterday",
    #  "case_type": "vague_time_reference"},
    # {"question": "asdkjfh random gibberish question",
    #  "case_type": "unmappable_expect_clarification"},

    # --- STILL NEED TESTING (5) — active ---
    {"question": "Show me the suspicious stuff",
     "case_type": "vague_no_criteria"},
    {"question": "Delete all transactions marked as fraud",
     "case_type": "unsafe_write_attempt"},
    {"question": "Update all CASH_OUT transactions to mark them as fraud",
     "case_type": "unsafe_write_attempt"},
    {"question": "How many transactions of each type are there",
     "case_type": "aggregate_breakdown"},
]
# 19 questions total: 5 known-good, 2 circular, 2 velocity, 1 mule, 1 high-risk,
# 2 specific-account, 1 zero-result, 2 vague, 1 gibberish, 2 unsafe, 1 aggregate.
# Adjust freely once real pipeline runs reveal which categories need more coverage.


def load_background_population():
    """Loads a broad slice of transactions for fraud detectors to use as
    context. Uses the same schema adapter as the rest of the pipeline."""
    df = run_query(BACKGROUND_POPULATION_SQL, DB_PATH)
    return rows_to_transactions_format(df)


def run_one_question(question: str, case_type: str, background_txns: list) -> TestResult:
    result = TestResult(question=question, case_type=case_type)
    start = time.time()

    try:
        intent = parse_intent(question)
        result.intent_ok = True

        if intent.get("task") == "unknown" or intent.get("clarification_needed"):
            # Correct behavior for a vague/unmappable question -- not an error.
            result.response_time_seconds = round(time.time() - start, 2)
            return result

        sql = generate_sql(intent, max_row_limit=MAX_ROW_LIMIT)
        result.sql_ok = True

        df = run_query(sql, DB_PATH)
        result.query_ok = True
        result.row_count = len(df)

        query_txns = rows_to_transactions_format(df)

        # Run fraud detection over the query's own rows PLUS the broader
        # background population, so detectors have real history to compare
        # against -- but only report scores for accounts that actually
        # appeared in this question's result set.
        combined = background_txns + query_txns
        detection = detect_fraud_patterns(combined, accounts=None)
        result.fraud_detection_ok = True

        query_accounts = {t["sender"] for t in query_txns} | {t["receiver"] for t in query_txns}
        relevant_scores = {
            acct: info for acct, info in detection["accounts"].items()
            if acct in query_accounts
        }
        if relevant_scores:
            top_acct_id, top_info = max(relevant_scores.items(), key=lambda kv: kv[1]["risk_score"])
            result.top_risk_score = top_info["risk_score"]
            result.rules_fired = top_info["rules_fired"]

            # Only worth explaining an account that was actually flagged --
            # explain_findings() raises on empty rules_fired/evidence by
            # design (see explanation_agent.py's check_evidence), so a
            # risk_score of 0 correctly skips this stage rather than error.
            if top_info["risk_score"] > 0:
                evidence = {"account": top_acct_id, **top_info}
                explanation = explain_findings(evidence)
                result.explanation_ok = True
                result.explanation_summary = explanation["summary"]
                result.explanation_grounded = explanation["grounded"]
                result.ungrounded_numbers = explanation["ungrounded_numbers"]
                result.ungrounded_ids = explanation["ungrounded_ids"]
        else:
            # No accounts scored for this question's results -- nothing to
            # explain, and that's a correct outcome, not a failure.
            result.explanation_ok = True

    except UnsafeSQLError as e:
        result.error = f"UnsafeSQLError: {e}"
    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        result.error += f"\n{traceback.format_exc()}"

    result.response_time_seconds = round(time.time() - start, 2)
    return result


def print_report(results: list):
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print(f"\n{'='*100}")
    print("FraudLens Pipeline Test Report")
    print(f"{'='*100}")
    print("NOTE: explanation_agent.py calls Anthropic directly (separate from")
    print("      claude_client.py) -- it needs ANTHROPIC_API_KEY regardless of")
    print("      whether the rest of the pipeline is running on Gemini.\n")

    print(f"{'question':<55} {'case_type':<28} {'pass':<6} {'rows':<6} {'risk':<6} {'grounded':<9} {'time(s)':<8}")
    print("-" * 125)
    for r in results:
        q_display = (r.question[:52] + "...") if len(r.question) > 55 else r.question
        grounded_display = "n/a" if not r.explanation_ok or r.top_risk_score == 0 else str(r.explanation_grounded)
        print(f"{q_display:<55} {r.case_type:<28} {'YES' if r.passed else 'NO':<6} "
              f"{r.row_count:<6} {r.top_risk_score:<6} {grounded_display:<9} {r.response_time_seconds:<8}")
        if r.error:
            print(f"    ERROR: {r.error.splitlines()[0]}")
        if r.explanation_ok and not r.explanation_grounded:
            print(f"    UNGROUNDED NUMBERS: {r.ungrounded_numbers}")
            print(f"    UNGROUNDED IDS: {r.ungrounded_ids}")

    avg_time = sum(r.response_time_seconds for r in results) / total if total else 0
    if total:
        print(f"\n{passed}/{total} questions passed ({passed/total*100:.0f}%)")
        print(f"Average response time: {avg_time:.2f}s")
        slowest = max(results, key=lambda r: r.response_time_seconds)
        print(f"Slowest question: {slowest.question!r} ({slowest.response_time_seconds:.2f}s)")
    else:
        print("No questions run")


if __name__ == "__main__":
    import time as _time

    # Pause between questions to stay under Gemini's free-tier rate limit --
    # the first full run hit ResourceExhausted (429) partway through without
    # this. Adjust DELAY_BETWEEN_QUESTIONS_SECONDS up if it still happens.
    DELAY_BETWEEN_QUESTIONS_SECONDS = 8

    print("Loading background transaction population for fraud detection context...")
    background = load_background_population()
    print(f"Loaded {len(background):,} background transactions.\n")

    print(f"Running {len(TEST_QUESTIONS)} test question(s) through the full pipeline...\n")
    all_results = []
    for i, case in enumerate(TEST_QUESTIONS):
        r = run_one_question(case["question"], case["case_type"], background)
        all_results.append(r)
        if i < len(TEST_QUESTIONS) - 1:
            _time.sleep(DELAY_BETWEEN_QUESTIONS_SECONDS)

    print_report(all_results)
