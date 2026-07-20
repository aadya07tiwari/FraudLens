# FraudLens AI

**Conversational Fraud Investigation Agent**

> Ask questions in plain English. Uncover fraud in seconds.

Hackathon Product Proposal — 2026
Track: AI Data Analyst Agent — Autonomous Agent for Data Exploration & Visualization

---

## Overview

FraudLens AI lets a bank investigator ask fraud questions in plain English — *"Which accounts show circular money transfers this week?"* — and get back a grounded answer: the SQL it ran, the fraud pattern it detected, a plain-English explanation, a network graph, and a downloadable investigation report.

It replaces hours of manual SQL-writing and dashboard-hopping with a single conversation.

**Core positioning:** FraudLens AI is the only investigation tool that answers in your words, shows its work, and never claims a fraud pattern it can't point to in the data.

## The Problem

Banks and fintechs process millions of transactions a day. Fraud investigators currently:

- Write complex, hand-tuned SQL for every new hypothesis they want to test.
- Switch between multiple dashboards and tools to piece together a single account's story.
- Spend hours manually spotting patterns like circular money-laundering rings, hidden in raw transaction tables.
- Struggle to explain a fraud score to a compliance officer or auditor in terms a non-technical reviewer can act on.

The result: slow fraud response, buried insights, and decisions that are hard to justify after the fact.

## The Solution

Ask a question. FraudLens AI parses intent, writes and validates the SQL, runs it against the transaction database, checks the results against a fraud-pattern engine (circular transfers, velocity spikes, mule accounts, high-risk transfers), and explains the finding in plain English — grounded in the exact numbers it computed, never a free-form guess. The result renders as a network graph, a risk score, and a one-click investigation report.

## Target Users & Objectives

**Target users:** Bank fraud investigators, fintech compliance teams, and auditors who currently rely on manual SQL and static dashboards.

**Key objectives**

- Correctly translate at least 80% of test questions into valid, safe SQL.
- Reliably detect at least two classic fraud patterns — circular transfers and rapid high-value transfers — on the test dataset.
- Every explanation must be traceable back to real computed numbers — zero hallucinated fraud claims.
- Deliver a working demo with a live-generated graph and report, built in under two weeks.

## Multi-Agent Architecture

FraudLens AI runs seven specialised agents, orchestrated so each hands off a clean, structured output to the next. The MVP runs the pipeline as a straight sequence of Claude calls and Python functions; a stretch goal migrates this to a full LangGraph multi-agent graph.

### 1. Intent Agent
Understands the user's question, extracts the fraud type, time range, and named entities (account IDs, locations, transaction types), and converts the query into structured JSON that every downstream agent can consume.

```
"Find money laundering accounts from last 30 days" →
{ "task": "fraud_detection", "fraud_type": "money_laundering", "time_period": "30_days" }
```

### 2. NL-to-SQL Agent
Reads the database schema, generates a safe SQL query from the structured intent, and validates it before execution — parameterised queries only, read-only connection, a query allow-list, and a row-limit guard so no query can lock or damage the table.

### 3. Fraud Detection Agent
Implements transparent rule-based checks over the query results, combined into a single risk score:

- **Money laundering** — circular transfers, layering patterns, rapid fund movement across a short chain of accounts.
- **Velocity fraud** — too many transactions from one account in too short a window.
- **Mule accounts** — newly created accounts that suddenly receive unusually large sums.
- **High-risk transfers** — transaction amounts that sit well outside an account's normal behaviour.

### 4. Network Analysis Agent
Builds a transaction graph with NetworkX — accounts as nodes, transfers as edges — and runs cycle detection to catch circular money movement (MVP targets simple 3-hop cycles, A → B → C → A, within a time window), plus centrality metrics to surface accounts at the middle of a suspicious cluster.

### 5. Visualization Agent
Renders the flagged transaction network and supporting charts with Plotly: the graph with the suspicious cycle highlighted, a risk-by-account view, and — as the product matures — a fraud heatmap by city/state and a timeline replay of money movement.

### 6. Explanation Agent
Never invents the fraud logic — takes the numbers the Fraud Detection and Network Analysis agents already computed and turns them into a plain-English paragraph a compliance officer can read and verify.

> Instead of "fraud score = 0.92," the agent says: *Account A transferred ₹2.5 lakh to Account B. Account B moved 95% of that sum to Account C within 15 minutes. Account C returned the funds to Account A — a circular pattern consistent with money laundering.*

### 7. Report Agent
Compiles the fraud risk level, accounts involved, supporting evidence, a timeline, and recommended next steps into a clean, downloadable investigation report — markdown/text for the MVP, with a polished PDF-style layout as a fast follow.

## Flagship Features

- **Fraud Chat** — ask "Why was ACC102 flagged?" and get a reasoned, evidence-backed answer in the same conversation.
- **Fraud Heatmap** — surfaces cities and states with the highest concentration of suspicious activity.
- **Timeline Replay** — a visual replay of how money moved between accounts over time.
- **Real-Time Fraud Alerts** *(stretch goal)* — checks new transactions for amount spikes, location mismatches, new beneficiaries, and rapid transfers, raising alerts instantly.

**Why it matters:** FraudLens AI's explanation is never allowed to say anything the pattern-detection code hasn't already computed and verified — the model explains the evidence, it doesn't invent it.

## Tech Stack

The build starts small: get the full pipeline working end to end on Streamlit and SQLite before reaching for anything heavier.

| Layer | Technology | Notes |
|---|---|---|
| Chat UI | Streamlit | Fastest path to a working chat interface for the hackathon timeline |
| LLM Layer | Anthropic Claude 3.5 / Claude 4 | NL → SQL + intent parsing, and turning computed signals into plain English |
| Data & Queries | Pandas / SQLite (sqlite3) | Loads PaySim transactions; simple, zero-setup local database |
| Graph & Patterns | NetworkX | Detects transfer cycles and builds the account-transaction graph |
| Visualization | Plotly | Renders the network graph, risk views, and (later) the heatmap |
| Vector store | Not used in core pipeline | Structured transaction data, not documents; optional stretch: ChromaDB for past investigation notes |
| Deployment | Hugging Face Spaces | Free, simple git-push deploy for the demo build |
| Stretch architecture | PostgreSQL + FastAPI + React + LangGraph | Swap in once the Streamlit version works end to end — don't start here |

**Additional tools & data:**

- PaySim dataset (Kaggle) — synthetic mobile-money transactions, already labelled fraud / not-fraud.
- IBM Credit Card Fraud dataset — reference / companion dataset.
- NetworkX + Plotly for all graph algorithms and visualisation.

## Success Metrics

- ≥ 80% correct SQL generation on the test question set.
- Correctly flags the known fraud cases planted in PaySim's test split.
- Every displayed explanation matches the underlying computed pattern — no exceptions.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| False positives (flagging legitimate transfers) | Explanation must cite exact computed values (amounts, timing, hop count) so a human can verify before acting |
| LLM invents fraud reasoning not backed by data | The explanation step only summarises numbers already computed by the pattern-detection code; the model never invents the fraud logic itself |
| Circular-detection algorithm misses complex rings | Start with simple 3-hop cycles, documented as a known v1 limitation |

## Responsible AI Considerations

- The system only recommends investigation — it never auto-freezes an account. A human stays in the loop for every action.
- Explanations are grounded in computed data, not LLM-generated claims, as a direct hallucination mitigation.
- Uses only synthetic / public datasets (PaySim, IBM fraud dataset) — no real customer data, documented in the report.
- The team checks whether the model flags accounts differently by region or account type in the test set, to surface potential bias early.

## Two-Week Build Roadmap

"Vibecoding" approach: describe what's needed to Claude / Claude Code in plain English, get working code fast, run and understand it, then ask for the next piece. Every day ends with something that actually runs.

### Week 1 — Core Pipeline

| Day | Focus | Deliverable |
|---|---|---|
| 1–2 | Load PaySim into SQLite | CSV loaded into a queryable table; first 10 rows verified |
| 3–4 | Build the NL→SQL step | Function sends question + schema to Claude, returns a valid SQL query; tested on 5 questions |
| 5 | Build the fraud pattern detector | NetworkX function detecting 3-hop circular transfers within a time window |
| 6 | Add velocity & high-value rules | Simple rule-based checks for rapid transfers and abnormal amounts |
| 7 | Wire the pipeline together | Question → SQL → results → pattern check → raw findings; 15–20-question test set built |

### Week 2 — Explanation, Visuals, UI, Deploy

| Day | Focus | Deliverable |
|---|---|---|
| 8 | Build the explanation step | Second Claude call turns computed pattern data into a plain-English paragraph |
| 9 | Build the network graph | NetworkX + Plotly graph with the flagged cycle highlighted |
| 10 | Build the report generator | Findings formatted into a clean markdown/text investigation report |
| 11 | Assemble the Streamlit app | Chat input, generated SQL shown to user, graph, explanation, downloadable report |
| 12 | Run the full test set | Accuracy and timing recorded — these become the success-metric numbers |
| 13 | Deploy to Hugging Face Spaces | Live version running; bugs found in production fixed |
| 14 | Rehearse the demo | Best 2–3 questions picked, 3–4-minute walkthrough rehearsed end to end |

## Team & Work Division — 5 Members

Each member owns one clear stage of the pipeline end to end.

**Member A — Conversational Layer Lead**
Intent Agent, NL-to-SQL Agent, Streamlit chat UI, Claude API integration.
*Demo role: opening — live question typed, structured intent and generated SQL shown on screen.*

**Member B — Fraud Detection Lead**
Fraud Detection Agent, risk scoring logic, test-question set design (including planted fraud cases from PaySim).
*Demo role: the moment a fraud pattern is flagged and the risk score appears.*

**Member C — Network & Visualization Lead**
Network Analysis Agent, Visualization Agent, fraud heatmap and timeline replay (stretch features).
*Demo role: the network graph reveal — suspicious cycle highlighted live.*

**Member D — Explanation & Reporting Lead**
Explanation Agent, Report Agent, Responsible-AI documentation (hallucination guardrails, human-in-the-loop framing).
*Demo role: the explanation read-out and downloadable report walkthrough.*

**Member E — Data, Platform & Delivery Lead**
Database setup and PaySim data loading (SQLite → PostgreSQL stretch), deployment to Hugging Face Spaces, success-metrics tracking and demo rehearsal coordination.
*Demo role: deploy/live-demo handling; closes with success metrics and roadmap.*

## Why This Wins

Most hackathon teams building a "fraud AI" will wire a chatbot to a dashboard and call it agentic. Very few will build a system where every claim the model makes is traceable back to a number it actually computed — where the SQL is shown, the pattern is verifiable, and the explanation can't drift into invented reasoning. That is the gap FraudLens AI occupies.

**What judges will remember**

- The only tool that shows its work — generated SQL, computed pattern, and explanation, all visible in one screen.
- A hallucination guardrail built into the architecture itself, not bolted on as a disclaimer.
- A real, labelled dataset (PaySim) and real detected fraud rings in the live demo — not synthetic toy data invented for the pitch.
- A working, deployed product after two weeks, not a slide deck of ambitions.

### Demo Flow (3–4 minutes)

1. Ask a real question from the test set — lead with one that surfaces a genuine detected fraud ring.
2. Show the generated SQL, so the audience sees there's no hidden magic.
3. Show the network graph with the flagged cycle highlighted.
4. Read the plain-English explanation aloud, then open the downloadable investigation report.

## Supporting Materials

- GitHub repo (created at kickoff), e.g. `github.com/yourteam/fraudlens-ai`
- System architecture diagram (agent pipeline)
- Dataset: PaySim Synthetic Mobile Money Transactions (Kaggle)
- Reference dataset: IBM Credit Card Fraud Dataset

---

*Ask in plain English. Show the evidence. Trust the answer.*
