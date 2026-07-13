# FraudLens AI — Demo Script (Draft Skeleton)

**Target length:** 3–4 minutes
**Status:** Structural draft — final test questions to be locked in once Member B's fraud detection and Member D's explanation/report are wired into the pipeline.

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
6. *(once wired)* Show the **Explanation Agent's** plain-English summary (Member D)
7. *(once wired)* Show the generated **report** (risk level, evidence, recommended action)

---

## Choosing the actual test questions — criteria (to finalize once B/D are ready)

Pick 2–3 questions from your 15–20 question test set that:
- **Have a real, correctly-detected fraud case** — not just any question, one where the detector actually found something interesting (a circular transfer ring, a mule account, etc.)
- **Cover different detection types** — don't show two circular-transfer examples back to back; show variety (e.g. one circular transfer, one velocity fraud or mule account)
- **Produce a clean/readable SQL query and a reasonably sized result table** — avoid a question that returns thousands of rows or an ugly, hard-to-read query on screen
- **Run reasonably fast** — avoid the slowest questions in your test set for the live demo (note actual response times from your Day 3 test-runner report once it exists)

*(Placeholder — fill in once finalized:)*
- **Question 1:** _[TBD — pick from test set once B/D are live]_
- **Question 2:** _[TBD]_
- **Question 3 (optional):** _[TBD]_

---

## Fallback plan — if the live Claude API call is slow or fails during the demo

- **Have a pre-recorded screen capture or screenshots** of each question's full click-through (intent → SQL → graph → explanation → report) ready as backup slides
- If a live call hangs, narrate: *"While that's processing, let me show you what this looks like when it completes"* and switch to the backup screenshots rather than sitting in silence
- Consider having the app **pre-warmed** — visit the live URL ~15–20 minutes before presenting so Streamlit Cloud's app isn't cold-starting during the actual demo
- If the whole live app fails outright, have the backup screenshots/recording as a full substitute — rehearse being able to present the entire flow narratively without the live app if needed

---

## Closing line ideas (pick/adapt one)

- Emphasize the **transparency** angle: every step (intent, SQL, evidence, explanation) is shown, not a black box
- Emphasize the **explainability guardrail**: the Explanation Agent can only reference numbers actually present in the evidence — no hallucinated fraud reasoning
- Mention it's built entirely on **public, synthetic data** (PaySim) — no real user data risk
- Note the **human-in-the-loop** design: recommended actions are things like "flag for review," never an automatic account freeze

---

**Next update to this doc:** once Member B and D push their code and your Day 3 test-runner produces real accuracy/response-time numbers, come back and fill in the actual 2–3 test questions and their real response times.
