# FraudLens AI — Demo Script

**Target length:** 3–4 minutes
**Status:** Finalized with real, tested questions (confirmed working end-to-end on the live Gemini-backed pipeline). Pending: Member A's max_tokens fix for aggregate-style questions, Member D's Gemini conversion final confirmation.

---

## Structure

1. **Opening (15–20 sec)** — one-line pitch: what FraudLens does and why it matters
2. **Question 1 — the "wow" case** (60–75 sec)
3. **Question 2 — a different fraud pattern type** (60–75 sec)
4. **Question 3 (optional, if time allows) — a clean/no-fraud question** to show it doesn't cry wolf (30–40 sec)
5. **Closing (15–20 sec)** — recap + what's next / Responsible AI note

---

## Click-through order for each question (per Member A's transparency design)

1. Type the question into the chat input
2. Let the **Intent JSON** expander show — briefly point out it correctly extracted task/fraud_type/entities
3. Show the **Generated SQL** expander — emphasize it's validated, read-only, safe
4. Show the **results table**
5. *(once wired)* Show the **network graph** (Member C) highlighting the flagged cycle/cluster
6. Show the **Explanation Agent's** plain-English summary (Member D) — now Gemini-backed, grounding-checked
7. Show the generated **report** (risk level, evidence, recommended action) — PDF/markdown export confirmed working

---

## Finalized test questions (confirmed working via real testing)

**Question 1 — opener, fraud-focused:**
> "Show me the top 10 largest TRANSFER transactions flagged as fraud"

Real 10,000,000-amount TRANSFER transactions, all correctly flagged (`isFraud=1`), sorted by amount. Strong, immediately convincing opener — confirmed ~120-140s response time (mostly the fraud-detection stage scanning the background population; consider narrating "the detector is cross-referencing this against the wider transaction history" during the wait).

**Question 2 — different data slice, ties into fraud detection over a broader set:**
> "Show me all TRANSFER transactions over 50000"

Returns 100 real rows; the fraud-detection stage (circular transfer, velocity, mule, high-risk) runs across this + background data, surfacing any real patterns present. Confirmed working.

**Question 3 (optional, if time allows) — a clean lookup, shows normal usage:**
> "Show me all CASH_OUT transactions over 100000"

100 real rows returned cleanly, fast, straightforward SQL — good contrast to Q1/Q2 if you want to show the app handles routine (non-flagged) questions smoothly too.

**Avoid for the live demo (known limitation, pending Member A's fix):**
- Aggregate/count-style questions (e.g. "how many transactions are flagged as fraud in total") — currently hit an intermittent JSON-parsing error due to a token-limit edge case. Fine once she pushes the `max_tokens` fix; until confirmed, don't risk these live.
- The literal phrase "circular chains of transfers" — the SQL agent can't directly express multi-hop cycle logic in one query (that's what the separate fraud-detection stage is for); use data-pull phrasing like Question 2 instead, which lets fraud detection do the actual cycle-finding.

---

## Fallback plan — if the live API call is slow or fails during the demo

- **Have a pre-recorded screen capture or screenshots** of each question's full click-through (intent → SQL → graph → explanation → report) ready as backup slides
- If a live call hangs, narrate: *"While that's processing, let me show you what this looks like when it completes"* and switch to the backup screenshots rather than sitting in silence
- Consider having the app **pre-warmed** — visit the live URL ~15–20 minutes before presenting so Streamlit Cloud's app isn't cold-starting during the actual demo
- **Known risk:** Gemini's free-tier daily quota is limited — confirm billing is enabled or quota is fresh before the demo slot, so a mid-demo `ResourceExhausted` error doesn't happen live
- If the whole live app fails outright, have the backup screenshots/recording as a full substitute — rehearse being able to present the entire flow narratively without the live app if needed

---

## Closing line ideas (pick/adapt one)

- Emphasize the **transparency** angle: every step (intent, SQL, evidence, explanation) is shown, not a black box
- Emphasize the **explainability guardrail**: the Explanation Agent can only reference numbers actually present in the evidence — no hallucinated fraud reasoning (confirmed via testing: a fabricated number was correctly flagged as ungrounded)
- Mention it's built entirely on **public, synthetic data** (PaySim) — no real user data risk
- Note the **human-in-the-loop** design: recommended actions are things like "flag for review," never an automatic account freeze

