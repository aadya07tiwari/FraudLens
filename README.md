# FraudLens — Member A Deliverables

This covers the parts of FraudLens owned by Member A:

1. **Intent Agent** (`agents/intent_agent.py`) — turns a natural-language
   question into structured JSON (task type, entities, filters, metrics).
2. **NL-to-SQL Agent** (`agents/sql_agent.py`) — turns that JSON into a
   safe, read-only, row-limited SQL query, validates it, and executes it.
3. **Streamlit chat frontend** (`app.py`) — chat UI showing the intent
   JSON, generated SQL, and result table for full transparency.

## 1. Setup

```bash
cd fraudlens_member_a
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and paste your ANTHROPIC_API_KEY
```

## 2. Build the database

You need PaySim data loaded into SQLite before running the app. Two options:

**Quick demo (no download needed)** — generates 5,000 synthetic rows:
```bash
python data/setup_db.py --sample
```

**Real dataset** — download "Synthetic Financial Datasets For Fraud
Detection" (PaySim) from Kaggle, then:
```bash
python data/setup_db.py --csv path/to/PS_20174392719_1491204439457_log.csv
```

Both create `db/fraudlens.db`. Use `--reset` to rebuild from scratch.

## 3. Run the app

```bash
streamlit run app.py
```

Open the local URL Streamlit prints (usually http://localhost:8501).

## 4. Try it

Example questions:
- "How many transactions are flagged as fraud?"
- "Show the top 10 largest TRANSFER transactions marked as fraud"
- "What's the average amount for CASH_OUT transactions between step 1 and 100?"
- "List all transactions involving account C1231006815"

Each response shows:
- The **Intent JSON** the Intent Agent produced
- The **generated SQL** the NL-to-SQL Agent wrote
- The **result table**

## Safety design (NL-to-SQL Agent)

- Prompt restricts Claude to `SELECT`-only queries against a single table.
- Generated SQL is checked against a forbidden-keyword list (`INSERT`,
  `UPDATE`, `DELETE`, `DROP`, `ALTER`, `PRAGMA`, `ATTACH`, etc.) before
  execution.
- Multi-statement queries (`;`) are rejected.
- The SQLite connection itself is opened `mode=ro` (read-only at the OS/DB
  driver level), so even a validation bypass can't mutate data.
- A row-limit cap (`MAX_ROW_LIMIT` in `.env`, default 200) is enforced
  server-side regardless of what SQL Claude generates.

## File structure

```
fraudlens_member_a/
├── agents/
│   ├── claude_client.py   # shared Anthropic API wrapper
│   ├── intent_agent.py    # NL question -> intent JSON
│   └── sql_agent.py       # intent JSON -> safe SQL -> results
├── data/
│   └── setup_db.py        # builds SQLite DB from PaySim CSV or synthetic sample
├── db/
│   └── schema.sql         # transactions table schema
├── app.py                 # Streamlit chat UI
├── requirements.txt
├── .env.example
└── README.md
```

## Integration notes for the rest of the team

- `parse_intent(question: str) -> dict` and `generate_sql(intent: dict) -> str`
  / `run_query(sql, db_path) -> pd.DataFrame` are the two public functions
  other members' code can import from `agents/`.
- The intent JSON shape is documented at the top of `intent_agent.py` —
  useful if another agent (e.g. an explanation/reporting agent) needs to
  consume it too.
