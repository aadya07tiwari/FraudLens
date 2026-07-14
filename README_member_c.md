# FraudLens — Member C Deliverables

This covers the parts of FraudLens owned by Member C: the network analysis and visualization layer.

1. **Graph Builder** (`graph_builder.py`) — turns a list of transactions into a directed NetworkX graph, with accounts as nodes and transfers as edges (aggregated by weight, count, and raw transaction history).
2. **Central Accounts Finder** (`central_accounts.py`) — ranks accounts by combined degree + betweenness centrality, to surface which accounts are most worth investigating first.
3. **Transaction Network Plot** (`plot_network.py`) — renders the graph with Plotly, sizing nodes by centrality and highlighting a flagged cycle's edges in a different color/thickness if one is passed in.
4. **Community Detection** (`community_detection.py`) — clusters the graph into groups using the Louvain method, surfacing unusually tightly-connected clusters of accounts.
5. **Fraud Heatmap** (`fraud_heatmap.py`) — aggregates flagged transactions by region and renders a color-scaled bar chart. *Note: requires a `location` field on each transaction — PaySim doesn't include this natively, see "Known limitations" below.*
6. **Timeline Replay** (`timeline_replay.py`) — steps through a flagged cycle's transactions in chronological order with a Play button and slider, showing money move from account to account over time.

---

## 1. Setup

```
cd fraudlens_member_c
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` should include:
```
networkx
plotly
pandas
```

No API key is needed for this layer — it works purely on transaction data already in memory or pulled from the database. (Member A's `.env` setup with `ANTHROPIC_API_KEY` is only needed for the conversational layer.)

---

## 2. How to run each file standalone

Every file has a small test block at the bottom (`if __name__ == "__main__":`) with sample data, so you can run any of them directly to sanity-check they work:

```
python graph_builder.py
python central_accounts.py
python plot_network.py
python community_detection.py
python fraud_heatmap.py
python timeline_replay.py
```

`plot_network.py` and `timeline_replay.py` save an HTML preview file you can open directly in a browser to see the chart before it's wired into the main app.

---

## 3. How this connects to the rest of the app

- **Input**: these functions expect transaction data shaped like `{"sender", "receiver", "amount", "timestamp"}` (plus `"location"` and `"is_flagged"` for the heatmap) — this should match the schema Member A's SQL agent queries against.
- **Output**: `plot_transaction_network()`, `plot_fraud_heatmap()`, and `plot_timeline_replay()` all return a Plotly figure, meant to be displayed in Member A's Streamlit app with `st.plotly_chart(fig)`.
- **Dependency on Member B**: `plot_transaction_network()`'s `highlight_cycle` argument and `plot_timeline_replay()`'s `cycle_transactions` argument both expect the flagged-cycle output from Member B's `detect_circular_transfers()` — the account list and ordered transaction list respectively.

---

## Known limitations

- `plot_fraud_heatmap()` requires a `location` field that PaySim does not natively provide. For the demo, locations were synthetically assigned; this should be noted honestly in the final report as a dataset limitation, not presented as real geographic fraud data.
- Community detection thresholds (`size >= 5`, `density > 0.5` for flagging a cluster as "unusual") were tuned on synthetic test data and should be re-checked against real PaySim distributions before the demo.
