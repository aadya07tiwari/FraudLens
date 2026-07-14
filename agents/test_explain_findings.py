"""
Test script for explain_findings() against all three pattern types.

Run with:
    export ANTHROPIC_API_KEY=sk-ant-...     (Mac/Linux)
    $env:ANTHROPIC_API_KEY="sk-ant-..."     (Windows PowerShell)
    python test_explain_findings.py

Each evidence object below matches the REAL output shape produced by
fraud_detection_agent.py's detectors (pulled from that file's own
__main__ sample data), wrapped in the per-account structure that
detect_fraud_patterns() actually returns.
"""

from explanation_agent import explain_findings

# ---------------------------------------------------------------------
# 1. Circular transfer (from detect_circular_transfers_nx sample data)
# ---------------------------------------------------------------------
CIRCULAR_TRANSFER_EVIDENCE = {
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

# ---------------------------------------------------------------------
# 2. Velocity fraud (from detect_velocity_fraud sample data: ACC_H,
#    transactions V0-V5, amounts 1000*i for i in 0..5)
# ---------------------------------------------------------------------
VELOCITY_FRAUD_EVIDENCE = {
    "account": "ACC_H",
    "risk_score": 15,
    "rules_fired": ["velocity_fraud"],
    "evidence": [
        {
            "pattern": "velocity_fraud",
            "account": "ACC_H",
            "count": 6,
            "window_minutes": 10,
            "window_start": "2026-07-01T09:00:00",
            "window_end": "2026-07-01T09:05:00",
            "actual_span_minutes": 5.0,
            "transactions": [
                {"txn_id": "V0", "sender": "ACC_H", "receiver": "ACC_0", "amount": 0, "timestamp": "2026-07-01T09:00:00"},
                {"txn_id": "V1", "sender": "ACC_H", "receiver": "ACC_1", "amount": 1000, "timestamp": "2026-07-01T09:01:00"},
                {"txn_id": "V2", "sender": "ACC_H", "receiver": "ACC_2", "amount": 2000, "timestamp": "2026-07-01T09:02:00"},
                {"txn_id": "V3", "sender": "ACC_H", "receiver": "ACC_3", "amount": 3000, "timestamp": "2026-07-01T09:03:00"},
                {"txn_id": "V4", "sender": "ACC_H", "receiver": "ACC_4", "amount": 4000, "timestamp": "2026-07-01T09:04:00"},
                {"txn_id": "V5", "sender": "ACC_H", "receiver": "ACC_5", "amount": 5000, "timestamp": "2026-07-01T09:05:00"},
            ],
            "evidence": (
                "ACC_H sent 6 transactions in 5.0 minutes "
                "(threshold: more than 5 within 10 minutes), "
                "totalling 15,000.00."
            ),
        }
    ],
}

# ---------------------------------------------------------------------
# 3. Mule account (from detect_mule_accounts sample data: ACC_MULE)
# ---------------------------------------------------------------------
MULE_ACCOUNT_EVIDENCE = {
    "account": "ACC_MULE",
    "risk_score": 35,
    "rules_fired": ["mule_account"],
    "evidence": [
        {
            "pattern": "mule_account",
            "account": "ACC_MULE",
            "created_at": "2026-07-01T00:00:00",
            "total_received": 150000,
            "age_days": 7,
            "amount_threshold": 100000,
            "account_age_at_last_txn_days": 2.0,
            "contributing_transactions": [
                {"txn_id": "M1", "sender": "ACC_X", "receiver": "ACC_MULE", "amount": 90000, "timestamp": "2026-07-02T00:00:00"},
                {"txn_id": "M2", "sender": "ACC_Y", "receiver": "ACC_MULE", "amount": 60000, "timestamp": "2026-07-03T00:00:00"},
            ],
            "evidence": (
                "ACC_MULE was created on 2026-07-01 and received "
                "150,000.00 across 2 transaction(s) within 2.0 days "
                "of opening (threshold: 100,000.00 within 7 days)."
            ),
        }
    ],
}


TEST_CASES = [
    ("Circular transfer", CIRCULAR_TRANSFER_EVIDENCE),
    ("Velocity fraud", VELOCITY_FRAUD_EVIDENCE),
    ("Mule account", MULE_ACCOUNT_EVIDENCE),
]


if __name__ == "__main__":
    for label, evidence in TEST_CASES:
        print(f"=== {label} ===")
        try:
            result = explain_findings(evidence)
            print(result["summary"])
            if not result["grounded"]:
                print(f"[WARNING] Ungrounded numbers: {result['ungrounded_numbers']}")
                print(f"[WARNING] Ungrounded IDs: {result['ungrounded_ids']}")
        except Exception as e:
            print(f"[ERROR] {e}")
        print()
