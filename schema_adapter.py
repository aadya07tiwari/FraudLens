"""
Schema adapter — translates rows from our `transactions` table (nameOrig,
nameDest, amount, step, isFraud, isFlaggedFraud, ...) into the shape both
Member C's visualization functions AND Member B's fraud detectors expect
(txn_id, sender, receiver, amount, timestamp, [location, is_flagged]).

Both B and C independently settled on the same sender/receiver/timestamp
naming, so one adapter now serves both — no need for two separate
conversion functions.
"""

from datetime import datetime, timedelta

import pandas as pd

_REFERENCE_START = datetime(2026, 1, 1)


def step_to_timestamp(step: int) -> datetime:
    return _REFERENCE_START + timedelta(hours=int(step))


def rows_to_transactions_format(df: pd.DataFrame, location_map: dict | None = None) -> list[dict]:
    records = []
    for idx, row in df.iterrows():
        location = "Unknown"
        if location_map:
            location = location_map.get(row["nameOrig"], "Unknown")

        txn_id = str(row["id"]) if "id" in row and pd.notna(row["id"]) else f"row_{idx}"

        records.append({
            "txn_id": txn_id,
            "sender": row["nameOrig"],
            "receiver": row["nameDest"],
            "amount": float(row["amount"]),
            "timestamp": step_to_timestamp(row["step"]),
            "location": location,
            "is_flagged": bool(row["isFraud"]) or bool(row["isFlaggedFraud"]),
        })
    return records


rows_to_member_c_format = rows_to_transactions_format


if __name__ == "__main__":
    sample = pd.DataFrame([
        {"step": 1, "type": "TRANSFER", "amount": 1500.0, "nameOrig": "C111",
         "oldbalanceOrg": 5000.0, "newbalanceOrig": 3500.0, "nameDest": "C222",
         "oldbalanceDest": 0.0, "newbalanceDest": 1500.0, "isFraud": 1, "isFlaggedFraud": 0},
    ])
    out = rows_to_transactions_format(sample)
    for r in out:
        print(r)
