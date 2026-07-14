"""
circular_transfer_detector.py

FraudLens AI — Fraud Detection Agent (Member B)
Detector: Circular Transfers / Money Laundering

WHAT THIS DETECTS
------------------
A "circular transfer" is a chain of transactions where money moves
A -> B -> C -> ... -> A and returns (in whole or in large part) to the
account it started from, within a short time window. This is a classic
layering pattern used to obscure the origin of funds.

DESIGN PRINCIPLES (matches the project's "no black box" requirement)
----------------------------------------------------------------------
1. Rule-based only. No ML, no learned weights. Every flag is a direct
   consequence of the transaction data, and can be explained in one
   sentence to a non-technical reviewer.
2. Time-ordered. A cycle only counts if each transfer happens strictly
   after the previous one. Three transactions that happen to form a
   loop on paper, but occurred months apart, are NOT flagged — that's
   not a real movement of funds, just coincidental structure.
3. Bounded hops and bounded time window. Both are configurable, but
   default to the project's stated MVP scope: 3-hop cycles (A->B->C->A)
   within a 24-hour window. This mirrors the Network Analysis Agent's
   scope so results stay consistent across the two agents.
4. Full evidence trail. Every flagged cycle returns the exact
   transaction IDs, amounts, and time gaps involved — nothing is
   summarized away. This is what the Explanation Agent (Member D)
   needs to write a grounded, verifiable explanation instead of an
   invented one.

INPUT FORMAT
------------
transactions: list of dicts, each with:
    {
        "txn_id": str,
        "sender": str,
        "receiver": str,
        "amount": float,
        "timestamp": datetime  (or ISO string; will be parsed)
    }

OUTPUT FORMAT
-------------
list of dicts, each representing one flagged cycle:
    {
        "pattern": "circular_transfer",
        "accounts_involved": [A, B, C],
        "cycle_txn_ids": [txn1, txn2, txn3],
        "cycle_amounts": [amt1, amt2, amt3],
        "start_amount": amt1,
        "return_amount": amt3,
        "return_ratio": return_amount / start_amount,
        "total_elapsed_minutes": float,
        "risk_signal": "high" | "medium",
        "evidence": "human-readable one-liner citing exact numbers"
    }
"""

from datetime import datetime
from collections import defaultdict
from itertools import count


def _parse_timestamp(ts):
    """Accept either a datetime object or an ISO-format string."""
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(ts)


def _build_outgoing_index(transactions):
    """
    Build an index: sender -> list of transactions sent, sorted by time.
    This lets the cycle search always move forward in time from each hop.
    """
    outgoing = defaultdict(list)
    for txn in transactions:
        txn = dict(txn)  # don't mutate caller's data
        txn["timestamp"] = _parse_timestamp(txn["timestamp"])
        outgoing[txn["sender"]].append(txn)

    for sender in outgoing:
        outgoing[sender].sort(key=lambda t: t["timestamp"])

    return outgoing


def detect_circular_transfers(
    transactions,
    max_hops=3,
    time_window_hours=24,
    min_return_ratio=0.5,
):
    """
    Detect circular transfer chains starting and ending at the same account.

    Parameters
    ----------
    transactions : list of dict
        Raw transaction records (see module docstring for schema).
    max_hops : int
        Maximum chain length before requiring the money to return to the
        origin account. Default 3 matches the MVP scope (A->B->C->A).
    time_window_hours : float
        Maximum total elapsed time from the first transfer to the last,
        for the chain to still count as one connected movement of funds.
    min_return_ratio : float
        Minimum fraction of the original amount that must return to the
        origin account for the cycle to be flagged (0.5 = at least 50%
        of the money came back). This avoids flagging trivial/incidental
        loops where only a negligible amount returns.

    Returns
    -------
    list of dict — one entry per detected cycle, each fully traceable
    to specific transaction IDs and numbers (see module docstring).
    """
    outgoing = _build_outgoing_index(transactions)
    flagged = []
    seen_cycles = set()  # avoid reporting the same account-set+txns twice

    def dfs(origin, current_account, path_txns, path_accounts, start_time):
        if len(path_txns) >= 2:
            elapsed = (path_txns[-1]["timestamp"] - start_time).total_seconds() / 3600
            if elapsed > time_window_hours:
                return

        if len(path_txns) == max_hops:
            return  # hop budget exhausted, this branch is done

        for txn in outgoing.get(current_account, []):
            # must move strictly forward in time from the previous hop
            if path_txns and txn["timestamp"] <= path_txns[-1]["timestamp"]:
                continue

            # closing the loop: this hop pays back to the origin account
            if txn["receiver"] == origin and len(path_txns) >= 1:
                full_chain = path_txns + [txn]
                elapsed_total = (
                    full_chain[-1]["timestamp"] - full_chain[0]["timestamp"]
                ).total_seconds() / 60

                # enforce the time window on the FULL closed chain, not just
                # mid-chain hops — a cycle that closes on the very next hop
                # must still respect the window (this was a bug: a 2-hop
                # cycle could previously close instantly, before the
                # mid-chain window check ever ran)
                if elapsed_total > time_window_hours * 60:
                    continue

                start_amount = full_chain[0]["amount"]
                return_amount = full_chain[-1]["amount"]
                ratio = return_amount / start_amount if start_amount else 0

                cycle_key = tuple(sorted(t["txn_id"] for t in full_chain))
                if ratio >= min_return_ratio and cycle_key not in seen_cycles:
                    seen_cycles.add(cycle_key)
                    accounts = path_accounts + [current_account, origin]
                    flagged.append({
                        "pattern": "circular_transfer",
                        "accounts_involved": accounts,
                        "cycle_txn_ids": [t["txn_id"] for t in full_chain],
                        "cycle_amounts": [t["amount"] for t in full_chain],
                        "start_amount": start_amount,
                        "return_amount": return_amount,
                        "return_ratio": round(ratio, 2),
                        "total_elapsed_minutes": round(elapsed_total, 1),
                        "risk_signal": "high" if ratio >= 0.85 else "medium",
                        "evidence": (
                            f"{accounts[0]} sent {start_amount:,.2f} through "
                            f"{' -> '.join(accounts[1:-1])} and "
                            f"{return_amount:,.2f} "
                            f"({ratio*100:.0f}% of the original) returned to "
                            f"{accounts[0]} within {elapsed_total:.0f} minutes."
                        ),
                    })
                continue  # don't also treat this as a mid-chain hop

            # otherwise, keep extending the chain
            if txn["receiver"] not in path_accounts and txn["receiver"] != origin:
                dfs(
                    origin,
                    txn["receiver"],
                    path_txns + [txn],
                    path_accounts + [current_account],
                    start_time,
                )

    for account in outgoing:
        for first_txn in outgoing[account]:
            dfs(
                origin=account,
                current_account=first_txn["receiver"],
                path_txns=[first_txn],
                path_accounts=[account],
                start_time=first_txn["timestamp"],
            )

    return flagged


# ---------------------------------------------------------------------------
# NetworkX-based variant: detect_circular_transfers_nx
#
# Same rule, different engine. Uses a directed graph to find candidate
# 3-hop structural cycles (A->B->C->A) cheaply, then verifies each
# candidate against the actual transaction timestamps — a structural
# cycle only counts as fraud-relevant if the money moved in that order,
# within window_minutes, start to finish.
#
# Why two passes (structure first, then time)? Graph cycle-finding
# doesn't know about timestamps — it just tells you "these three
# accounts are connected in a loop." We still need to check the real
# transaction data to confirm funds actually flowed around that loop
# in the right order and fast enough to be one connected movement.
# ---------------------------------------------------------------------------
import networkx as nx


def detect_circular_transfers_nx(transactions, window_minutes=30):
    """
    Detect 3-hop circular transfers (A -> B -> C -> A) using NetworkX
    for cycle structure, verified against real transaction timestamps.

    Parameters
    ----------
    transactions : list of dict
        Same schema as detect_circular_transfers: txn_id, sender,
        receiver, amount, timestamp (datetime or ISO string).
    window_minutes : float
        Maximum total elapsed time from the first transfer in the cycle
        to the last, for it to count as one connected movement of funds.

    Returns
    -------
    list of dict, one per detected cycle:
        {
            "pattern": "circular_transfer",
            "accounts_involved": [A, B, C],
            "cycle_txn_ids": [txn_ab, txn_bc, txn_ca],
            "cycle_amounts": [amt_ab, amt_bc, amt_ca],
            "time_gaps_minutes": [gap_ab_to_bc, gap_bc_to_ca],
            "total_elapsed_minutes": float,
            "evidence": "human-readable one-liner"
        }
    """
    txns = []
    for t in transactions:
        t = dict(t)
        t["timestamp"] = _parse_timestamp(t["timestamp"])
        txns.append(t)

    # index transactions by (sender, receiver) pair, sorted by time, so we
    # can quickly pull "all transfers from A to B" when verifying a cycle
    by_pair = defaultdict(list)
    for t in txns:
        by_pair[(t["sender"], t["receiver"])].append(t)
    for pair in by_pair:
        by_pair[pair].sort(key=lambda t: t["timestamp"])

    # build a directed graph purely for structure — one edge per unique
    # (sender, receiver) pair, regardless of how many transactions
    # occurred between them
    graph = nx.DiGraph()
    for sender, receiver in by_pair:
        graph.add_edge(sender, receiver)

    flagged = []
    seen_cycles = set()

    # nx.simple_cycles finds every structural cycle; we only want length-3
    # ones (A->B->C->A), which matches the MVP's stated 3-hop scope
    for cycle in nx.simple_cycles(graph, length_bound=3):
        if len(cycle) != 3:
            continue

        # nx.simple_cycles returns the 3 accounts in an arbitrary rotation
        # (e.g. it might hand back [C, A, B] even though A->B->C->A is the
        # order money actually moved). The graph only knows structure, not
        # time, so we must try all 3 rotations as possible starting points
        # and let the timestamp checks below decide which one, if any, is
        # a real time-ordered chain.
        rotations = [
            (cycle[0], cycle[1], cycle[2]),
            (cycle[1], cycle[2], cycle[0]),
            (cycle[2], cycle[0], cycle[1]),
        ]

        for a, b, c in rotations:
            _check_rotation(a, b, c, by_pair, window_minutes, seen_cycles, flagged)

    return flagged


def _check_rotation(a, b, c, by_pair, window_minutes, seen_cycles, flagged):
    """Check one rotation (a->b->c->a) for valid time-ordered cycles."""
    if True:
        # try every combination of actual transactions along these three
        # edges, in time order, to find one valid time-windowed instance
        for txn_ab in by_pair.get((a, b), []):
            for txn_bc in by_pair.get((b, c), []):
                if txn_bc["timestamp"] <= txn_ab["timestamp"]:
                    continue
                for txn_ca in by_pair.get((c, a), []):
                    if txn_ca["timestamp"] <= txn_bc["timestamp"]:
                        continue

                    total_elapsed = (
                        txn_ca["timestamp"] - txn_ab["timestamp"]
                    ).total_seconds() / 60
                    if total_elapsed > window_minutes:
                        continue

                    cycle_key = tuple(sorted(
                        [txn_ab["txn_id"], txn_bc["txn_id"], txn_ca["txn_id"]]
                    ))
                    if cycle_key in seen_cycles:
                        continue
                    seen_cycles.add(cycle_key)

                    gap1 = (txn_bc["timestamp"] - txn_ab["timestamp"]).total_seconds() / 60
                    gap2 = (txn_ca["timestamp"] - txn_bc["timestamp"]).total_seconds() / 60

                    flagged.append({
                        "pattern": "circular_transfer",
                        "accounts_involved": [a, b, c],
                        "cycle_txn_ids": [txn_ab["txn_id"], txn_bc["txn_id"], txn_ca["txn_id"]],
                        "cycle_amounts": [txn_ab["amount"], txn_bc["amount"], txn_ca["amount"]],
                        "time_gaps_minutes": [round(gap1, 1), round(gap2, 1)],
                        "total_elapsed_minutes": round(total_elapsed, 1),
                        "evidence": (
                            f"{a} sent {txn_ab['amount']:,.2f} to {b}, who sent "
                            f"{txn_bc['amount']:,.2f} to {c} {gap1:.0f} min later, "
                            f"who sent {txn_ca['amount']:,.2f} back to {a} "
                            f"{gap2:.0f} min after that "
                            f"(total: {total_elapsed:.0f} min)."
                        ),
                    })


# ---------------------------------------------------------------------------
# Velocity fraud detector: detect_velocity_fraud
#
# Flags an account that sends an unusually high number of transactions in
# a short window — a common signal for account takeover, bot-driven fraud,
# or rapid cash-out attempts.
#
# Design note: a naive sliding window would report every overlapping window
# that exceeds the threshold, which turns one real burst of activity into
# several near-duplicate flags (e.g. txns 1-6, then 2-7, then 3-8, all
# "flagged" separately even though it's a single incident). Instead, once
# a burst is detected, this jumps past it before continuing — so one real
# spike in activity produces exactly one flag, with the full list of
# transactions that make it up.
# ---------------------------------------------------------------------------
def detect_velocity_fraud(transactions, account_id, window_minutes=10, min_count=5):
    """
    Flag an account if it sends more than `min_count` transactions within
    any `window_minutes` window.

    Parameters
    ----------
    transactions : list of dict
        Full transaction list (any accounts). Only transactions where
        this account is the sender are considered.
    account_id : str
        The account to check.
    window_minutes : float
        Size of the rolling time window to check transaction counts within.
    min_count : int
        An account must send MORE than this many transactions inside the
        window to be flagged (i.e. min_count itself does not trigger a flag,
        min_count + 1 does).

    Returns
    -------
    list of dict, one per detected burst:
        {
            "pattern": "velocity_fraud",
            "account": account_id,
            "count": int,
            "window_minutes": window_minutes,
            "window_start": datetime,
            "window_end": datetime,
            "actual_span_minutes": float,
            "transactions": [ ...full txn dicts that make up this burst... ],
            "evidence": "human-readable one-liner"
        }
    """
    own_txns = []
    for t in transactions:
        if t["sender"] != account_id:
            continue
        t = dict(t)
        t["timestamp"] = _parse_timestamp(t["timestamp"])
        own_txns.append(t)
    own_txns.sort(key=lambda t: t["timestamp"])

    flagged = []
    n = len(own_txns)
    i = 0

    while i < n:
        left = i
        right = i
        # expand the window as far right as it still fits within
        # window_minutes of the leftmost transaction in this burst
        while (right + 1 < n and
               (own_txns[right + 1]["timestamp"] - own_txns[left]["timestamp"])
               .total_seconds() / 60 <= window_minutes):
            right += 1

        count = right - left + 1

        if count > min_count:
            burst = own_txns[left:right + 1]
            span_minutes = (
                burst[-1]["timestamp"] - burst[0]["timestamp"]
            ).total_seconds() / 60

            flagged.append({
                "pattern": "velocity_fraud",
                "account": account_id,
                "count": count,
                "window_minutes": window_minutes,
                "window_start": burst[0]["timestamp"],
                "window_end": burst[-1]["timestamp"],
                "actual_span_minutes": round(span_minutes, 1),
                "transactions": burst,
                "evidence": (
                    f"{account_id} sent {count} transactions in "
                    f"{span_minutes:.1f} minutes "
                    f"(threshold: more than {min_count} within "
                    f"{window_minutes} minutes), totalling "
                    f"{sum(t['amount'] for t in burst):,.2f}."
                ),
            })
            i = right + 1  # skip past this burst — don't re-flag overlapping windows
        else:
            i += 1

    return flagged


# ---------------------------------------------------------------------------
# Mule account detector: detect_mule_accounts
#
# Flags accounts that are new AND received a large total sum shortly after
# opening — the classic mule pattern (an account opened specifically to
# receive and quickly move laundered funds).
#
# Design note: this only sums money received DURING the account's first
# `age_days` — not its all-time total. A 2-year-old account that happens
# to receive a large sum today is not a mule signal; a 3-day-old account
# that already received a large sum IS. Summing lifetime totals would
# blur that distinction and produce false positives on legitimate old
# accounts, so age is checked at the time of each incoming transaction,
# not "as of now."
# ---------------------------------------------------------------------------
def detect_mule_accounts(transactions, accounts, age_days=7, amount_threshold=100000):
    """
    Flag accounts that were created within `age_days` of receiving a
    combined total above `amount_threshold`.

    Parameters
    ----------
    transactions : list of dict
        Full transaction list. Only incoming transactions (this account
        as receiver) are considered.
    accounts : list of dict
        Account metadata: [{"account_id": str, "created_at": datetime or
        ISO string}, ...]. One entry per account being checked.
    age_days : float
        The account must still be within this many days of its creation
        date at the time a transaction is received for that transaction
        to count toward the total.
    amount_threshold : float
        Combined total received (within the age window) needed to flag.

    Returns
    -------
    list of dict, one per flagged account:
        {
            "pattern": "mule_account",
            "account": account_id,
            "created_at": datetime,
            "total_received": float,
            "age_days": age_days,
            "amount_threshold": amount_threshold,
            "account_age_at_last_txn_days": float,
            "contributing_transactions": [ ...txn dicts... ],
            "evidence": "human-readable one-liner"
        }
    """
    # parse all transaction timestamps once
    txns = []
    for t in transactions:
        t = dict(t)
        t["timestamp"] = _parse_timestamp(t["timestamp"])
        txns.append(t)

    # index incoming transactions by receiver
    incoming = defaultdict(list)
    for t in txns:
        incoming[t["receiver"]].append(t)
    for receiver in incoming:
        incoming[receiver].sort(key=lambda t: t["timestamp"])

    flagged = []

    for acct in accounts:
        account_id = acct["account_id"]
        created_at = _parse_timestamp(acct["created_at"])

        # only transactions received while the account was still within
        # its "new account" window count toward the mule total
        contributing = [
            t for t in incoming.get(account_id, [])
            if (t["timestamp"] - created_at).total_seconds() / 86400 <= age_days
            and t["timestamp"] >= created_at  # guard against bad data (txn before account existed)
        ]

        total_received = sum(t["amount"] for t in contributing)

        if total_received > amount_threshold and contributing:
            last_txn_age_days = (
                contributing[-1]["timestamp"] - created_at
            ).total_seconds() / 86400

            flagged.append({
                "pattern": "mule_account",
                "account": account_id,
                "created_at": created_at,
                "total_received": total_received,
                "age_days": age_days,
                "amount_threshold": amount_threshold,
                "account_age_at_last_txn_days": round(last_txn_age_days, 1),
                "contributing_transactions": contributing,
                "evidence": (
                    f"{account_id} was created on "
                    f"{created_at.strftime('%Y-%m-%d')} and received "
                    f"{total_received:,.2f} across {len(contributing)} "
                    f"transaction(s) within {last_txn_age_days:.1f} days "
                    f"of opening (threshold: {amount_threshold:,.2f} within "
                    f"{age_days} days)."
                ),
            })

    return flagged


# ---------------------------------------------------------------------------
# High-risk transfer detector: detect_high_risk_transfers
#
# Flags a transaction as abnormal for a given account if its amount sits
# far above that account's own historical average (in standard deviations).
#
# Two design choices worth calling out:
#
# 1. "Historical" means PRIOR transactions only, not the account's full
#    transaction list. Computing the baseline from all transactions
#    (including ones that happen after the transaction being checked)
#    would be a look-ahead bug — in a live system, you can't use future
#    data to judge a transaction happening right now. Each transaction's
#    baseline is built only from what happened strictly before it.
#
# 2. A minimum history size (min_history) is required before flagging
#    anything. With only 1-2 prior transactions, "average" and "standard
#    deviation" aren't statistically meaningful yet — flagging off a
#    baseline of one data point would produce noise, not signal.
# ---------------------------------------------------------------------------
def detect_high_risk_transfers(transactions, account_id, std_multiplier=3, min_history=3):
    """
    Flag transactions sent by `account_id` whose amount is more than
    `std_multiplier` standard deviations above that account's own prior
    average (computed only from transactions strictly before each one).

    Parameters
    ----------
    transactions : list of dict
        Full transaction list. Only transactions where this account is
        the sender are considered.
    account_id : str
        The account to check.
    std_multiplier : float
        How many standard deviations above the historical mean a
        transaction must be to get flagged.
    min_history : int
        Minimum number of prior transactions required before a baseline
        is considered reliable enough to flag against. Transactions
        occurring before the account has this much history are skipped.

    Returns
    -------
    list of dict, one per flagged transaction:
        {
            "pattern": "high_risk_transfer",
            "account": account_id,
            "txn_id": str,
            "amount": float,
            "historical_mean": float,
            "historical_std": float,
            "std_multiplier": std_multiplier,
            "std_devs_above_mean": float,
            "history_size": int,
            "evidence": "human-readable one-liner"
        }
    """
    import statistics

    own_txns = []
    for t in transactions:
        if t["sender"] != account_id:
            continue
        t = dict(t)
        t["timestamp"] = _parse_timestamp(t["timestamp"])
        own_txns.append(t)
    own_txns.sort(key=lambda t: t["timestamp"])

    flagged = []

    for i, txn in enumerate(own_txns):
        prior = own_txns[:i]  # strictly before this transaction — no look-ahead

        if len(prior) < min_history:
            continue  # not enough history yet to trust a baseline

        prior_amounts = [t["amount"] for t in prior]
        mean = statistics.mean(prior_amounts)
        std = statistics.stdev(prior_amounts)  # sample stdev, len(prior) >= 3 guaranteed

        if std == 0:
            # every prior transaction was identical — any different amount
            # is technically "infinite" std devs away, which isn't a
            # meaningful signal on its own. Skip rather than over-flag;
            # this is a known limitation worth documenting, not a bug.
            continue

        std_devs_above = (txn["amount"] - mean) / std

        if std_devs_above > std_multiplier:
            flagged.append({
                "pattern": "high_risk_transfer",
                "account": account_id,
                "txn_id": txn["txn_id"],
                "amount": txn["amount"],
                "historical_mean": round(mean, 2),
                "historical_std": round(std, 2),
                "std_multiplier": std_multiplier,
                "std_devs_above_mean": round(std_devs_above, 2),
                "history_size": len(prior),
                "evidence": (
                    f"{account_id} sent {txn['amount']:,.2f} in txn "
                    f"{txn['txn_id']}, which is {std_devs_above:.1f} standard "
                    f"deviations above its historical average of "
                    f"{mean:,.2f} (based on {len(prior)} prior "
                    f"transaction(s), threshold: {std_multiplier} std devs)."
                ),
            })

    return flagged


# ---------------------------------------------------------------------------
# Combined aggregator: detect_fraud_patterns
#
# Runs all four detectors and produces a single per-account risk score
# (0-100) plus the full evidence trail behind it. This is the function
# the Explanation Agent (Member D) and Report Agent read from — every
# number in the output must be traceable to a specific rule and specific
# transaction(s), never a vague label like "suspicious."
#
# SCORING MODEL (fully rule-based, not a black box — see PATTERN_WEIGHTS)
# -------------------------------------------------------------------------
# Each pattern type has a fixed point value, documented here as an
# explicit judgment call (not derived from data — flag this in your
# writeup same as the other thresholds in this file). Circular transfers
# and mule accounts are weighted highest because they indicate money
# actually changed hands in a laundering-consistent way; velocity and
# high-risk transfers are weighted lower because, on their own, they can
# have innocent explanations (e.g. a business doing payroll).
#
# To stop one noisy pattern from single-handedly maxing out the score,
# each pattern type's contribution is capped at MAX_OCCURRENCES_COUNTED
# occurrences before the weight is applied. The final sum is capped at
# 100 regardless.
# -------------------------------------------------------------------------
PATTERN_WEIGHTS = {
    "circular_transfer": 40,
    "mule_account": 35,
    "velocity_fraud": 15,
    "high_risk_transfer": 10,
}

MAX_OCCURRENCES_COUNTED = {
    "circular_transfer": 2,   # a 2nd distinct cycle still adds signal, a 5th doesn't add much more
    "mule_account": 1,        # detect_mule_accounts already returns one entry per account
    "velocity_fraud": 3,
    "high_risk_transfer": 3,
}


def detect_fraud_patterns(
    transactions,
    accounts=None,
    circular_window_minutes=30,
    velocity_window_minutes=10,
    velocity_min_count=5,
    mule_age_days=7,
    mule_amount_threshold=100000,
    high_risk_std_multiplier=3,
    high_risk_min_history=3,
):
    """
    Run all four fraud detectors and combine their output into a single
    per-account risk score with full supporting evidence.

    Parameters
    ----------
    transactions : list of dict
        Full transaction list (schema used throughout this module).
    accounts : list of dict or None
        Account metadata for mule detection: [{"account_id": ...,
        "created_at": ...}, ...]. If None, mule-account detection is
        SKIPPED entirely (not faked, not assumed) — transaction data
        alone doesn't contain account creation dates, so this needs to
        come from wherever account metadata is loaded (Member E's data
        layer). Check `mule_check_skipped` in the return value to see
        whether this happened.
    circular_window_minutes, velocity_window_minutes, velocity_min_count,
    mule_age_days, mule_amount_threshold, high_risk_std_multiplier,
    high_risk_min_history :
        Passed straight through to the underlying detectors — see each
        function's docstring for what they mean.

    Returns
    -------
    dict:
        {
            "mule_check_skipped": bool,
            "accounts": {
                account_id: {
                    "risk_score": int (0-100),
                    "rules_fired": [pattern names, unique],
                    "evidence": [ ...full evidence dicts from the
                                  underlying detectors, unmodified... ]
                },
                ...
            }
        }
        Keyed by account for O(1) lookup — this is the shape the "Fraud
        Chat" feature needs for "Why was ACC102 flagged?" style queries.
    """
    # collect every account that appears anywhere in the transaction data
    all_accounts = set()
    for t in transactions:
        all_accounts.add(t["sender"])
        all_accounts.add(t["receiver"])

    # hits[account_id] = list of (pattern_name, evidence_dict)
    hits = defaultdict(list)

    # --- circular transfers (not per-account — a cycle implicates
    # every account in it, so attribute the same evidence to each) ---
    cycles = detect_circular_transfers_nx(
        transactions, window_minutes=circular_window_minutes
    )
    for cycle in cycles:
        for acct in cycle["accounts_involved"]:
            hits[acct].append(("circular_transfer", cycle))

    # --- velocity fraud (per sender account) ---
    for acct in all_accounts:
        bursts = detect_velocity_fraud(
            transactions, account_id=acct,
            window_minutes=velocity_window_minutes,
            min_count=velocity_min_count,
        )
        for burst in bursts:
            hits[acct].append(("velocity_fraud", burst))

    # --- mule accounts (only if metadata was supplied) ---
    mule_check_skipped = accounts is None
    if not mule_check_skipped:
        mule_hits = detect_mule_accounts(
            transactions, accounts,
            age_days=mule_age_days,
            amount_threshold=mule_amount_threshold,
        )
        for mule in mule_hits:
            hits[mule["account"]].append(("mule_account", mule))

    # --- high-risk transfers (per sender account) ---
    for acct in all_accounts:
        risky = detect_high_risk_transfers(
            transactions, account_id=acct,
            std_multiplier=high_risk_std_multiplier,
            min_history=high_risk_min_history,
        )
        for r in risky:
            hits[acct].append(("high_risk_transfer", r))

    # --- combine into per-account risk scores ---
    result_accounts = {}
    for acct, acct_hits in hits.items():
        by_pattern = defaultdict(list)
        for pattern_name, evidence in acct_hits:
            by_pattern[pattern_name].append(evidence)

        score = 0
        for pattern_name, evidence_list in by_pattern.items():
            weight = PATTERN_WEIGHTS[pattern_name]
            counted = min(len(evidence_list), MAX_OCCURRENCES_COUNTED[pattern_name])
            score += weight * counted
        score = min(score, 100)

        result_accounts[acct] = {
            "risk_score": score,
            "rules_fired": sorted(by_pattern.keys()),
            "evidence": [ev for _, ev in acct_hits],
        }

    return {
        "mule_check_skipped": mule_check_skipped,
        "accounts": result_accounts,
    }


# ---------------------------------------------------------------------------
# Quick manual test with synthetic data — run this file directly to check
# the detector behaves as expected before wiring it into the full pipeline.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_transactions = [
        # A clean 3-hop cycle: A -> B -> C -> A, all within an hour
        {"txn_id": "T1", "sender": "ACC_A", "receiver": "ACC_B",
         "amount": 250000, "timestamp": "2026-07-01T09:00:00"},
        {"txn_id": "T2", "sender": "ACC_B", "receiver": "ACC_C",
         "amount": 240000, "timestamp": "2026-07-01T09:10:00"},
        {"txn_id": "T3", "sender": "ACC_C", "receiver": "ACC_A",
         "amount": 235000, "timestamp": "2026-07-01T09:20:00"},

        # Unrelated normal transaction, should NOT be flagged
        {"txn_id": "T4", "sender": "ACC_D", "receiver": "ACC_E",
         "amount": 5000, "timestamp": "2026-07-01T10:00:00"},

        # A 2-hop cycle that closes on the very next hop, but a month later
        # (outside the 24h window) — should NOT flag. This specifically
        # tests the time-window check on chains that close immediately.
        {"txn_id": "T5", "sender": "ACC_F", "receiver": "ACC_G",
         "amount": 100000, "timestamp": "2026-06-01T09:00:00"},
        {"txn_id": "T6", "sender": "ACC_G", "receiver": "ACC_F",
         "amount": 95000, "timestamp": "2026-07-01T09:00:00"},
    ]

    results = detect_circular_transfers(sample_transactions)
    print(f"[pure-python] Detected {len(results)} circular transfer pattern(s):\n")
    for r in results:
        print(r["evidence"])
        print(f"  -> risk_signal: {r['risk_signal']}, "
              f"txns: {r['cycle_txn_ids']}\n")

    nx_results = detect_circular_transfers_nx(sample_transactions, window_minutes=30)
    print(f"[networkx] Detected {len(nx_results)} circular transfer pattern(s):\n")
    for r in nx_results:
        print(r["evidence"])
        print(f"  -> txns: {r['cycle_txn_ids']}, "
              f"gaps: {r['time_gaps_minutes']} min\n")

    # --- velocity fraud tests ---
    velocity_txns = [
        # 6 rapid-fire transfers from ACC_H within 8 minutes -> should flag
        {"txn_id": f"V{i}", "sender": "ACC_H", "receiver": f"ACC_{i}",
         "amount": 1000 * i, "timestamp": f"2026-07-01T09:0{i}:00"}
        for i in range(0, 6)  # V0..V5 at 09:00..09:05
    ] + [
        # a later, unrelated normal-paced transfer from the same account
        # (30 minutes after the burst) -> should NOT be part of any flag
        {"txn_id": "V6", "sender": "ACC_H", "receiver": "ACC_99",
         "amount": 500, "timestamp": "2026-07-01T09:35:00"},
    ] + [
        # exactly min_count (5) transactions for ACC_I -> should NOT flag
        # (rule is "more than min_count", not "min_count or more")
        {"txn_id": f"W{i}", "sender": "ACC_I", "receiver": f"ACC_{i}",
         "amount": 200, "timestamp": f"2026-07-01T10:0{i}:00"}
        for i in range(0, 5)  # exactly 5 txns
    ]

    velocity_results = detect_velocity_fraud(
        velocity_txns, account_id="ACC_H", window_minutes=10, min_count=5
    )
    print(f"[velocity: ACC_H] Detected {len(velocity_results)} burst(s):\n")
    for r in velocity_results:
        print(r["evidence"])
        print(f"  -> txn ids in burst: {[t['txn_id'] for t in r['transactions']]}\n")

    velocity_results_edge = detect_velocity_fraud(
        velocity_txns, account_id="ACC_I", window_minutes=10, min_count=5
    )
    print(f"[velocity: ACC_I, exactly at threshold] "
          f"Detected {len(velocity_results_edge)} burst(s) — expect 0\n")

    # --- mule account tests ---
    mule_accounts_meta = [
        {"account_id": "ACC_MULE", "created_at": "2026-07-01T00:00:00"},
        {"account_id": "ACC_OLD", "created_at": "2020-01-01T00:00:00"},
        {"account_id": "ACC_NEW_SLOW", "created_at": "2026-07-01T00:00:00"},
    ]
    mule_txns = [
        # ACC_MULE: brand new, receives 150,000 within 2 days -> should flag
        {"txn_id": "M1", "sender": "ACC_X", "receiver": "ACC_MULE",
         "amount": 90000, "timestamp": "2026-07-02T00:00:00"},
        {"txn_id": "M2", "sender": "ACC_Y", "receiver": "ACC_MULE",
         "amount": 60000, "timestamp": "2026-07-03T00:00:00"},

        # ACC_OLD: 6-year-old account receives 200,000 today -> should NOT
        # flag (age, not amount, is the deciding factor here)
        {"txn_id": "M3", "sender": "ACC_Z", "receiver": "ACC_OLD",
         "amount": 200000, "timestamp": "2026-07-05T00:00:00"},

        # ACC_NEW_SLOW: new account, but the large sum arrives on day 10 —
        # after the 7-day mule window -> should NOT flag
        {"txn_id": "M4", "sender": "ACC_W", "receiver": "ACC_NEW_SLOW",
         "amount": 150000, "timestamp": "2026-07-11T00:00:00"},
    ]

    mule_results = detect_mule_accounts(
        mule_txns, mule_accounts_meta, age_days=7, amount_threshold=100000
    )
    print(f"[mule accounts] Detected {len(mule_results)} flagged account(s) "
          f"— expect 1 (only ACC_MULE):\n")
    for r in mule_results:
        print(r["evidence"])
        print()

    # --- high-risk transfer tests ---
    risk_txns = [
        # ACC_J: 4 normal transfers around ~1,000, then one huge outlier
        {"txn_id": "R1", "sender": "ACC_J", "receiver": "ACC_A",
         "amount": 1000, "timestamp": "2026-07-01T09:00:00"},
        {"txn_id": "R2", "sender": "ACC_J", "receiver": "ACC_B",
         "amount": 1100, "timestamp": "2026-07-02T09:00:00"},
        {"txn_id": "R3", "sender": "ACC_J", "receiver": "ACC_C",
         "amount": 950, "timestamp": "2026-07-03T09:00:00"},
        {"txn_id": "R4_OUTLIER", "sender": "ACC_J", "receiver": "ACC_D",
         "amount": 50000, "timestamp": "2026-07-04T09:00:00"},

        # a normal-sized transfer AFTER the outlier — this specifically
        # tests the look-ahead fix: if the baseline wrongly included R5,
        # R4_OUTLIER's baseline mean would shift, potentially hiding it
        {"txn_id": "R5", "sender": "ACC_J", "receiver": "ACC_E",
         "amount": 1050, "timestamp": "2026-07-05T09:00:00"},
    ]

    risk_results = detect_high_risk_transfers(
        risk_txns, account_id="ACC_J", std_multiplier=3, min_history=3
    )
    print(f"[high-risk transfers] Detected {len(risk_results)} flagged txn(s) "
          f"— expect 1 (only R4_OUTLIER):\n")
    for r in risk_results:
        print(r["evidence"])
        print()

    # --- combined detect_fraud_patterns test ---
    combined_txns = (
        sample_transactions      # ACC_A/B/C circular cycle
        + velocity_txns          # ACC_H velocity burst
        + mule_txns               # ACC_MULE mule pattern
        + risk_txns                # ACC_J high-risk outlier
    )

    # test WITHOUT accounts metadata first — mule check should be skipped
    combined_no_accounts = detect_fraud_patterns(combined_txns)
    print(f"[combined, no accounts metadata] mule_check_skipped = "
          f"{combined_no_accounts['mule_check_skipped']} (expect True)\n")

    # test WITH accounts metadata — full pipeline
    combined_result = detect_fraud_patterns(combined_txns, accounts=mule_accounts_meta)
    print(f"[combined, with accounts metadata] mule_check_skipped = "
          f"{combined_result['mule_check_skipped']} (expect False)\n")

    print("Per-account risk scores (only accounts with hits shown):\n")
    for acct, info in sorted(
        combined_result["accounts"].items(),
        key=lambda kv: -kv[1]["risk_score"],
    ):
        print(f"  {acct}: score={info['risk_score']}, rules={info['rules_fired']}")
    print()