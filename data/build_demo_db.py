"""
Build a curated, deployment-sized subset of the PaySim dataset.

Keeps ALL real fraud rows (isFraud=1) plus a random sample of normal
transactions, so the deployed demo always has genuine fraud cases to
find -- without committing the full 470MB+ dataset to git.

Usage:
    python data/build_demo_db.py --csv ./data/PS_20174392719_1491204439457_log.csv \
                                  --out ./db/fraudlens_demo.db \
                                  --normal-sample 75000

The output file is small enough to commit to git (well under GitHub's
100MB per-file limit) and is meant to be the DB used in the deployed
Streamlit Cloud app.
"""

import argparse
import os
import sqlite3
import sys

import pandas as pd

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")

EXPECTED_COLUMNS = [
    "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
    "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud",
]


def build_schema(conn: sqlite3.Connection):
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()


def build_subset(csv_path: str, out_path: str, normal_sample: int, seed: int = 42):
    if not os.path.exists(csv_path):
        print(f"CSV not found at: {csv_path}", file=sys.stderr)
        sys.exit(1)

    print("Reading full CSV (this scans the whole file once)...")
    df = pd.read_csv(csv_path)

    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        print(f"CSV is missing expected PaySim columns: {missing}", file=sys.stderr)
        sys.exit(1)

    df = df[EXPECTED_COLUMNS]

    fraud_rows = df[df["isFraud"] == 1]
    normal_rows = df[df["isFraud"] == 0]

    print(f"Total fraud rows found: {len(fraud_rows):,}")
    print(f"Total normal rows available: {len(normal_rows):,}")

    sample_size = min(normal_sample, len(normal_rows))
    normal_sampled = normal_rows.sample(n=sample_size, random_state=seed)

    subset = pd.concat([fraud_rows, normal_sampled]).sample(frac=1, random_state=seed)  # shuffle
    subset = subset.reset_index(drop=True)

    print(f"Final subset size: {len(subset):,} rows "
          f"({len(fraud_rows):,} fraud + {sample_size:,} normal)")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)

    conn = sqlite3.connect(out_path)
    build_schema(conn)
    subset.to_sql("transactions", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\nDone. Wrote {out_path} ({size_mb:.1f} MB)")

    if size_mb > 90:
        print("WARNING: file is close to GitHub's 100MB limit. "
              "Consider lowering --normal-sample.", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to the full PaySim CSV")
    parser.add_argument("--out", default="./db/fraudlens_demo.db",
                         help="Output path for the curated demo DB")
    parser.add_argument("--normal-sample", type=int, default=75000,
                         help="Number of non-fraud rows to include (default: 75000)")
    args = parser.parse_args()
    build_subset(args.csv, args.out, args.normal_sample)
