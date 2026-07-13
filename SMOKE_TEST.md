# FraudLens AI — Pre-Demo Smoke Test Checklist

Run this checklist against the **live deployed app** (Streamlit Cloud), not your local machine — the goal is to catch bugs that only show up in production (missing env vars, path issues, cold-start behavior, etc.). Run it at least once with a real buffer of time before the actual demo, not same-day.

---

## 1. Deployment health
- [ ] App loads at the live URL without a build/deploy error
- [ ] No red error banner on initial page load
- [ ] Sidebar renders correctly (About section, DB path, row limit cap)
- [ ] `db/fraudlens.db` warning does NOT appear (confirms the DB shipped/loaded correctly in prod, not just locally)

## 2. Environment & secrets
- [ ] `ANTHROPIC_API_KEY` is set correctly in Streamlit Cloud's Secrets (not just in your local `.env`)
- [ ] No "missing API key" or auth errors when a question is submitted
- [ ] `DB_PATH` and `MAX_ROW_LIMIT` env vars (if used) resolve to the expected values in prod

## 3. Core pipeline — happy path
- [ ] Submit a simple, known-good question (e.g. "Show me the top 10 largest TRANSFER transactions flagged as fraud")
- [ ] Intent JSON expander shows sensible structured output
- [ ] Generated SQL expander shows a valid, safe SELECT query
- [ ] Results table renders with real data (not empty, not an error)
- [ ] Response time feels reasonable (note actual seconds — this matters for the demo fallback plan)

## 4. Edge cases / error handling
- [ ] Ask a vague/unmappable question — confirm it asks for clarification instead of crashing
- [ ] Try a question that might tempt an unsafe query (e.g. asking to "delete" or "update" something) — confirm `UnsafeSQLError` blocks it gracefully, doesn't crash the app
- [ ] Refresh the page mid-conversation — confirm chat history behavior is acceptable (resets cleanly, no broken state)
- [ ] Click "Clear chat" — confirm it actually clears and doesn't error

## 5. Visual / graph / report components (once wired in)
- [ ] Network graph renders (Member C's component) without errors
- [ ] Fraud heatmap renders correctly
- [ ] Timeline replay works for a flagged cycle
- [ ] Explanation Agent output (Member D) displays and reads sensibly
- [ ] Generated report downloads/renders correctly

## 6. Performance & reliability
- [ ] Ask 3–4 questions back to back — confirm no slowdown or memory issues
- [ ] Confirm the app doesn't silently fail if the Claude API is slow — some loading indicator should show
- [ ] Note the app's cold-start time (Streamlit Cloud apps can sleep after inactivity — check how long it takes to wake up)

## 7. Final pre-demo pass (day-of or day-before)
- [ ] Run the exact 2–3 questions planned for the live demo, end to end, on the live URL
- [ ] Confirm results match what's expected (no surprises mid-demo)
- [ ] Have the fallback plan ready (see demo script) in case live API calls are slow during the actual presentation

---

**Notes:**
- Log any failure here with the exact question/action that caused it, plus a screenshot if possible — makes it much faster to hand off to whoever owns that part (A/B/C/D) for a fix.
- If Streamlit Cloud's free tier causes the app to sleep after inactivity, do a "wake-up" visit ~15–20 minutes before the actual demo starts.
