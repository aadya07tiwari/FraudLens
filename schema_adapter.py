"""
Schema adapter — translates rows from our `transactions` table (nameOrig,
nameDest, amount, step, isFraud, isFlaggedFraud, ...) into the shape
Member C's visualization functions expect (sender, receiver, amount,
timestamp, location, is_flagged), per README_member_c.md's documented
input format.

This exists because the two sides were built independently against
different field-naming assumptions -- rather than rewriting either
side, this adapter sits in between so both pieces of code keep working
exactly as written.

Usage:
    from schema_adapter import rows_to_member_c_format
    df = run_query(sql, db_path)          # Member A's SQL agent output
    records = rows_to_member_c_format(df)  # ready for graph_builder, etc.
"""

from datetime import datetime, timedelta

import pandas as pd

# PaySim's `step` is "1 step = 1 hour" from an arbitrary start point.
# We anchor it to a fixed reference datetime so Member C's timestamp-based
# sorting/plotting (e.g. timeline_replay.py) has something real to work
# with. The absolute date is arbitrary/synthetic -- only the relative
# ordering and spacing between steps is meaningful.
_REFERENCE_START = datetime(2026, 1, 1)


def step_to_timestamp(step: int) -> datetime:
    """Converts PaySim's integer `step` (hours since simulation start)
    into an actual datetime, so timestamp-based sorting/plotting works."""
    return _REFERENCE_START + timedelta(hours=int(step))


def rows_to_member_c_format(df: pd.DataFrame, location_map: dict | None = None) -> list[dict]:
    """
    Converts a DataFrame of rows from the `transactions` table into the
    list-of-dicts shape Member C's functions expect.

    Expected input columns (from db/schema.sql):
        step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig,
        nameDest, oldbalanceDest, newbalanceDest, isFraud, isFlaggedFraud

    Output dict shape (per README_member_c.md):
        sender, receiver, amount, timestamp, location, is_flagged

    `location_map` is optional -- since PaySim has no real location data
    (a known, documented limitation per Member C's README), pass a dict
    mapping account IDs to a synthetic location if you want the heatmap
    to have something to group by. If omitted, location is set to
    "Unknown" for every row -- update this once the team decides how to
    handle the synthetic-location limitation for the demo.
    """
    records = []
    for _, row in df.iterrows():
        location = "Unknown"
        if location_map:
            location = location_map.get(row["nameOrig"], "Unknown")

        records.append({
            "sender": row["nameOrig"],
            "receiver": row["nameDest"],
            "amount": float(row["amount"]),
            "timestamp": step_to_timestamp(row["step"]),
            "location": location,
            "is_flagged": bool(row["isFraud"]) or bool(row["isFlaggedFraud"]),
        })
    return records


if __name__ == "__main__":
    # Quick sanity check with a couple of fake rows, matching our real
    # DB column names, to confirm the conversion looks right.
    sample = pd.DataFrame([
        {"step": 1, "type": "TRANSFER", "amount": 1500.0, "nameOrig": "C111",
         "oldbalanceOrg": 5000.0, "newbalanceOrig": 3500.0, "nameDest": "C222",
         "oldbalanceDest": 0.0, "newbalanceDest": 1500.0, "isFraud": 1, "isFlaggedFraud": 0},
        {"step": 2, "type": "CASH_OUT", "amount": 1500.0, "nameOrig": "C222",
         "oldbalanceOrg": 1500.0, "newbalanceOrig": 0.0, "nameDest": "C333",
         "oldbalanceDest": 0.0, "newbalanceDest": 1500.0, "isFraud": 1, "isFlaggedFraud": 0},
    ])
    out = rows_to_member_c_format(sample)
    for r in out:
        print(r)
