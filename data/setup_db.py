"""
FraudLens - DB setup script
----------------------------
Loads the PaySim CSV dataset into a local SQLite database that the
NL-to-SQL agent will query.

Usage:
    python data/setup_db.py --csv path/to/PS_20174392719_1491204439457_log.csv

Download the PaySim dataset (Kaggle: "Synthetic Financial Datasets For Fraud
Detection") and pass its path with --csv. If you just want to try the app
without the full ~470MB dataset, use --sample to generate a small synthetic
sample instead.
"""

import argparse
import os
import sqlite3
import sys
import random

import pandas as pd

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "fraudlens.db")

EXPECTED_COLUMNS = [
    "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
    "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud",
]


def build_schema(conn: sqlite3.Connection):
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()


def load_csv(conn: sqlite3.Connection, csv_path: str, chunksize: int = 50_000):
    if not os.path.exists(csv_path):
        print(f"CSV not found at: {csv_path}", file=sys.stderr)
        sys.exit(1)

    total_rows = 0
    for chunk in pd.read_csv(csv_path, chunksize=chunksize):
        missing = set(EXPECTED_COLUMNS) - set(chunk.columns)
        if missing:
            print(f"CSV is missing expected PaySim columns: {missing}", file=sys.stderr)
            sys.exit(1)
        chunk = chunk[EXPECTED_COLUMNS]
        chunk.to_sql("transactions", conn, if_exists="append", index=False)
        total_rows += len(chunk)
        print(f"  loaded {total_rows:,} rows so far...", end="\r")

    print(f"\nDone. Loaded {total_rows:,} rows into 'transactions'.")


def generate_sample(conn: sqlite3.Connection, n_rows: int = 5000, seed: int = 42):
    """Generates a small synthetic PaySim-like sample so the app is runnable
    without downloading the full dataset."""
    random.seed(seed)
    types = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
    rows = []
    for i in range(n_rows):
        t = random.choice(types)
        amount = round(random.uniform(1, 200_000), 2)
        old_orig = round(random.uniform(0, 300_000), 2)
        new_orig = max(0.0, round(old_orig - amount, 2)) if t in ("CASH_OUT", "TRANSFER", "PAYMENT", "DEBIT") else round(old_orig + amount, 2)
        old_dest = round(random.uniform(0, 300_000), 2)
        new_dest = round(old_dest + amount, 2)
        is_fraud = 1 if (t in ("CASH_OUT", "TRANSFER") and amount > 150_000 and random.random() < 0.35) else 0
        is_flagged = 1 if (t == "TRANSFER" and amount > 200_000) else 0
        rows.append((
            random.randint(1, 743), t, amount,
            f"C{random.randint(10_000_000, 99_999_999)}", old_orig, new_orig,
            f"C{random.randint(10_000_000, 99_999_999)}", old_dest, new_dest,
            is_fraud, is_flagged,
        ))

    df = pd.DataFrame(rows, columns=EXPECTED_COLUMNS)
    df.to_sql("transactions", conn, if_exists="append", index=False)
    print(f"Generated {n_rows:,} synthetic sample rows into 'transactions'.")


def main():
    parser = argparse.ArgumentParser(description="Set up the FraudLens SQLite DB from PaySim data.")
    parser.add_argument("--csv", type=str, default=None, help="Path to the PaySim CSV file.")
    parser.add_argument("--sample", action="store_true", help="Generate a small synthetic sample instead of using a CSV.")
    parser.add_argument("--sample-rows", type=int, default=5000, help="Number of rows for --sample (default: 5000).")
    parser.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help="Output SQLite DB path.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate the transactions table first.")
    args = parser.parse_args()

    if not args.csv and not args.sample:
        parser.error("Provide either --csv <path> or --sample")

    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    conn = sqlite3.connect(args.db)

    if args.reset:
        conn.execute("DROP TABLE IF EXISTS transactions;")
        conn.commit()

    build_schema(conn)

    if args.sample:
        generate_sample(conn, n_rows=args.sample_rows)
    else:
        load_csv(conn, args.csv)

    conn.close()
    print(f"SQLite DB ready at: {args.db}")


if __name__ == "__main__":
    main()
