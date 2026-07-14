"""
paysim_eval.py

FraudLens AI — Fraud Detection Agent (Member B)
Evaluation harness: builds a labeled test set from PaySim and reports
precision/recall for the rule-based detectors, for the project's stated
success metric ("reliably detect classic fraud patterns on the test set").

HOW TO USE
----------
1. Download PaySim from Kaggle: "Synthetic Financial Datasets For Fraud
   Detection" (search that title on kaggle.com — this script cannot
   download it for you, no network access to Kaggle from this environment).
2. Set PAYSIM_CSV_PATH below to point at the downloaded CSV.
3. Run: python3 paysim_eval.py

IF NO FILE IS FOUND, this script falls back to a small SYNTHETIC
PaySim-shaped sample so you can confirm the harness itself works end to
end. Numbers from the synthetic fallback are NOT real accuracy — they
only prove the code runs correctly. Swap in the real CSV for numbers
you can actually report.

IMPORTANT CAVEATS FOR YOUR WRITEUP
------------------------------------
- Mule-account detection is SKIPPED in this evaluation. PaySim has no
  account creation date field at all, so there's no way to check "was
  this account new" from the raw data. This isn't a bug in the eval —
  it's a real gap between what PaySim provides and what the mule
  detector needs. Document this as a known limitation.
- PaySim's `isFraud` label reflects ITS OWN fraud simulation (large
  TRANSFER immediately drained via CASH_OUT), which doesn't necessarily
  look like a circular ring, a velocity burst, or a statistical outlier
  relative to that specific account's own history. So precision/recall
  here measures "does our detector agree with PaySim's fraud
  definition" — a meaningful first check, but not proof the detectors
  would catch every real-world fraud pattern.
- PaySim's `step` field is hours since simulation start (1 step = 1
  hour, per the dataset's own documentation), not a calendar timestamp.
  This script converts step -> an arbitrary datetime baseline so our
  detectors (which expect real timestamps) can run unmodified.
"""

import random
from datetime import datetime, timedelta
from collections import defaultdict

from fraud_detection_agent import detect_fraud_patterns

PAYSIM_CSV_PATH = "/mnt/user-data/uploads/paysim.csv"  # <-- point this at your download

SAMPLE_ROWS = 20000      # how many PaySim rows to load as the "population"
                          # (detectors need surrounding history, not just
                          # the 15-20 test rows in isolation)
N_FRAUD_CASES = 8        # accounts pulled from isFraud==1 rows
N_EASY_NORMAL = 5        # small, unremarkable normal transactions
N_HARD_NORMAL = 5        # large but legitimately-labeled transactions —
                          # these specifically stress-test false positives
RANDOM_SEED = 42
FLAG_THRESHOLD = 0       # an account counts as "predicted fraud" if its
                          # risk_score is strictly greater than this


def load_paysim(path, sample_rows):
    """Load PaySim CSV via pandas. Returns None if the file isn't found,
    so the caller can fall back to synthetic data instead of crashing."""
    try:
        import pandas as pd
    except ImportError:
        raise SystemExit(
            "pandas is required. Install with: "
            "pip install pandas --break-system-packages"
        )

    import os
    if not os.path.exists(path):
        return None

    df = pd.read_csv(path, nrows=sample_rows)
    return df


def paysim_df_to_transactions(df, base=datetime(2026, 1, 1)):
    """
    Convert PaySim rows into this project's transaction schema.

    IMPORTANT APPROXIMATION: PaySim's `step` field only has 1-hour
    resolution. Naively converting step -> timestamp makes every
    transaction within the same step collapse to the SAME timestamp —
    which breaks every detector in this project, since all of them
    (circular transfers, velocity, high-risk) depend on strict time
    ordering to work at all. A fraud ring that completes within a
    single PaySim hour would otherwise be structurally invisible to
    these detectors, not because the logic is wrong, but because the
    timestamp data has no sub-hour resolution to reason about.

    The approximation used here: transactions sharing a step are
    assumed to have occurred in the CSV's row order, and are spaced 1
    second apart purely to give them a strict order. This is NOT a
    verified fact about PaySim's row ordering — it's a documented
    assumption. Consequence: elapsed-time NUMBERS reported by the
    detectors (e.g. "20 minutes apart") are not literally accurate for
    same-step transactions — only the relative ORDER is meaningful.
    Cross-step timing (different hours) is exact, since that comes
    directly from PaySim's own step field.
    """
    transactions = []
    step_counters = defaultdict(int)

    for idx, row in df.iterrows():
        step = int(row["step"])
        sub_step_offset = step_counters[step]
        step_counters[step] += 1

        timestamp = base + timedelta(hours=step, seconds=sub_step_offset)

        transactions.append({
            "txn_id": f"P{idx}",
            "sender": row["nameOrig"],
            "receiver": row["nameDest"],
            "amount": float(row["amount"]),
            "timestamp": timestamp,
        })
    return transactions


def build_test_set(df, rng):
    """
    Build a 15-20 case test set of ACCOUNTS (not individual transactions),
    since risk scoring in detect_fraud_patterns operates per-account:
      - N_FRAUD_CASES accounts that appear as the sender in an isFraud==1
        transaction (expected: SHOULD be flagged)
      - N_EASY_NORMAL accounts with small, unremarkable transactions
        (expected: should NOT be flagged)
      - N_HARD_NORMAL accounts with large but legitimately-labeled
        transactions (expected: should NOT be flagged — these are the
        cases most likely to trip a false positive, so they matter most)
    """
    fraud_df = df[df["isFraud"] == 1]
    normal_df = df[df["isFraud"] == 0]

    fraud_accounts = fraud_df["nameOrig"].drop_duplicates().tolist()
    rng.shuffle(fraud_accounts)
    fraud_accounts = fraud_accounts[:N_FRAUD_CASES]

    # "easy" negatives: below-median amount, common PAYMENT-type activity
    median_amount = normal_df["amount"].median()
    easy_pool = normal_df[normal_df["amount"] <= median_amount]["nameOrig"].drop_duplicates().tolist()
    rng.shuffle(easy_pool)
    easy_normal_accounts = easy_pool[:N_EASY_NORMAL]

    # "hard" negatives: large amounts, still legitimately isFraud==0 —
    # the accounts most likely to falsely trip velocity / high-risk rules
    high_amount_threshold = normal_df["amount"].quantile(0.95)
    hard_pool = normal_df[normal_df["amount"] >= high_amount_threshold]["nameOrig"].drop_duplicates().tolist()
    rng.shuffle(hard_pool)
    hard_normal_accounts = hard_pool[:N_HARD_NORMAL]

    test_set = (
        [{"account_id": a, "expected": "fraud", "case_type": "planted_fraud"} for a in fraud_accounts]
        + [{"account_id": a, "expected": "normal", "case_type": "easy_normal"} for a in easy_normal_accounts]
        + [{"account_id": a, "expected": "normal", "case_type": "hard_normal_large_amount"} for a in hard_normal_accounts]
    )
    return test_set


def make_synthetic_fallback(rng):
    """
    Small synthetic PaySim-shaped dataset, used ONLY when the real CSV
    isn't found. This proves the harness runs correctly — it does NOT
    produce real accuracy numbers. Swap in the real file for those.
    """
    import pandas as pd

    rows = []
    idx = 0

    # a handful of "fraud" accounts with a clear circular pattern.
    # All 3 hops share the same PaySim step deliberately — this is the
    # realistic case (a fast laundering ring completing within one hour)
    # that the sub-step ordering fix in paysim_df_to_transactions exists
    # to make detectable at all.
    for i in range(4):
        step = i * 24
        a, b, c = f"C_FRAUD_{i}_A", f"C_FRAUD_{i}_B", f"C_FRAUD_{i}_C"
        for (s, r, amt) in [(a, b, 200000), (b, c, 190000), (c, a, 180000)]:
            rows.append({
                "step": step,
                "nameOrig": s, "nameDest": r, "amount": amt, "isFraud": 1,
            })
            idx += 1

    # a handful of normal accounts with small payments
    for i in range(10):
        rows.append({
            "step": rng.randint(0, 500),
            "nameOrig": f"C_NORMAL_{i}", "nameDest": f"C_MERCHANT_{i % 3}",
            "amount": rng.uniform(500, 3000), "isFraud": 0,
        })

    # a few normal accounts with large but legitimate amounts
    for i in range(5):
        rows.append({
            "step": rng.randint(0, 500),
            "nameOrig": f"C_BIGSPENDER_{i}", "nameDest": f"C_MERCHANT_{i % 3}",
            "amount": rng.uniform(80000, 150000), "isFraud": 0,
        })

    return pd.DataFrame(rows)


def evaluate(transactions, test_set):
    """Run detect_fraud_patterns once over the full population, then look
    up each test-set account's predicted label against its expected one."""
    result = detect_fraud_patterns(transactions, accounts=None)  # mule check skipped — see module docstring
    scored_accounts = result["accounts"]

    rows = []
    for case in test_set:
        acct = case["account_id"]
        info = scored_accounts.get(acct, {"risk_score": 0, "rules_fired": []})
        predicted = "fraud" if info["risk_score"] > FLAG_THRESHOLD else "normal"
        rows.append({
            **case,
            "predicted": predicted,
            "risk_score": info["risk_score"],
            "rules_fired": info["rules_fired"],
        })
    return rows


def print_report(rows):
    tp = sum(1 for r in rows if r["expected"] == "fraud" and r["predicted"] == "fraud")
    fn = sum(1 for r in rows if r["expected"] == "fraud" and r["predicted"] == "normal")
    fp = sum(1 for r in rows if r["expected"] == "normal" and r["predicted"] == "fraud")
    tn = sum(1 for r in rows if r["expected"] == "normal" and r["predicted"] == "normal")

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) and precision == precision and recall == recall else float("nan"))

    print(f"{'account_id':<20} {'expected':<8} {'predicted':<9} {'score':<6} {'case_type':<24} rules_fired")
    print("-" * 100)
    for r in rows:
        print(f"{str(r['account_id']):<20} {r['expected']:<8} {r['predicted']:<9} "
              f"{r['risk_score']:<6} {r['case_type']:<24} {r['rules_fired']}")

    print("\nConfusion matrix:")
    print(f"  TP={tp}  FN={fn}")
    print(f"  FP={fp}  TN={tn}")
    print(f"\nPrecision: {precision:.2f}" if precision == precision else "\nPrecision: undefined (no predicted-fraud cases)")
    print(f"Recall:    {recall:.2f}" if recall == recall else "Recall:    undefined (no actual-fraud cases)")
    print(f"F1:        {f1:.2f}" if f1 == f1 else "F1:        undefined")


if __name__ == "__main__":
    rng = random.Random(RANDOM_SEED)

    df = load_paysim(PAYSIM_CSV_PATH, SAMPLE_ROWS)
    if df is None:
        print(f"!! PaySim CSV not found at {PAYSIM_CSV_PATH}")
        print("!! Falling back to SYNTHETIC data — this only proves the")
        print("!! harness runs correctly. It is NOT a real accuracy number.")
        print("!! Download PaySim from Kaggle and update PAYSIM_CSV_PATH")
        print("!! to get numbers you can actually report.\n")
        df = make_synthetic_fallback(rng)
    else:
        print(f"Loaded {len(df)} rows from {PAYSIM_CSV_PATH}\n")

    test_set = build_test_set(df, rng)
    print(f"Built a {len(test_set)}-case test set "
          f"({sum(1 for c in test_set if c['expected']=='fraud')} fraud, "
          f"{sum(1 for c in test_set if c['expected']=='normal')} normal)\n")

    transactions = paysim_df_to_transactions(df)
    print(f"Running detectors over {len(transactions)} transactions "
          f"(this can take a moment on the full sample)...\n")

    rows = evaluate(transactions, test_set)
    print_report(rows)