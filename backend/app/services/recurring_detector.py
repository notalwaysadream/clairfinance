import re
from datetime import date, timedelta
from typing import List, Dict, Any, Tuple
import numpy as np

def normalize_recurring_desc(desc: str) -> str:
    s = str(desc).lower()
    s = re.sub(r"^(upi|pos|neft|imps|ach|auto-debit)[-\s:]+", "", s)
    s = re.sub(r"[\d\-_/]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def detect_recurring_patterns(transactions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Identifies recurring subscriptions, EMIs, and bills using interval clustering & CV.
    Returns (updated_transactions, list_of_detected_patterns).
    """
    groups = {}
    for idx, txn in enumerate(transactions):
        if txn.get("type") == "debit":
            norm = normalize_recurring_desc(txn.get("description", ""))
            if len(norm) >= 3:
                groups.setdefault(norm, []).append((idx, txn))

    patterns = []
    recurring_indices = set()

    for norm_name, items in groups.items():
        if len(items) < 3:
            continue

        # Sort items chronologically
        items.sort(key=lambda x: x[1]["date"])
        dates = [x[1]["date"] for x in items]
        amounts = [float(x[1]["amount"]) for x in items]

        # Calculate day intervals
        intervals = []
        for i in range(1, len(dates)):
            diff = (dates[i] - dates[i-1]).days
            if diff > 0:
                intervals.append(diff)

        if not intervals:
            continue

        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        cv = std_interval / mean_interval if mean_interval > 0 else 1.0

        # Regular cadence check: weekly (~7d), monthly (~28-32d), quarterly (~90d), annual (~365d)
        is_recurring = False
        frequency = "monthly"

        if 5 <= mean_interval <= 9 and cv < 0.35:
            is_recurring = True
            frequency = "weekly"
        elif 25 <= mean_interval <= 35 and cv < 0.35:
            is_recurring = True
            frequency = "monthly"
        elif 80 <= mean_interval <= 100 and cv < 0.35:
            is_recurring = True
            frequency = "quarterly"
        elif 350 <= mean_interval <= 380 and cv < 0.35:
            is_recurring = True
            frequency = "annual"

        if is_recurring:
            for idx, _ in items:
                recurring_indices.add(idx)

            median_amt = float(np.median(amounts))
            last_date = dates[-1]
            if frequency == "monthly":
                next_date = last_date + timedelta(days=30)
            elif frequency == "weekly":
                next_date = last_date + timedelta(days=7)
            elif frequency == "quarterly":
                next_date = last_date + timedelta(days=90)
            else:
                next_date = last_date + timedelta(days=365)

            patterns.append({
                "description": items[0][1]["description"],
                "normalized_name": norm_name,
                "typical_amount": round(median_amt, 2),
                "frequency": frequency,
                "day_of_period": last_date.day,
                "next_expected": next_date,
                "confidence": round(max(0.7, 1.0 - cv), 2),
                "category_id": items[0][1].get("category_id"),
            })

    for idx, txn in enumerate(transactions):
        txn["is_recurring"] = idx in recurring_indices

    return transactions, patterns
