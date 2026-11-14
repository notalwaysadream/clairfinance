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

    # Known monthly recurring commitment keywords (e.g. house rent, mortgages, EMIs)
    HOUSE_AND_BILL_KEYWORDS = [
        "rent", "house rent", "housing", "landlord", "flat rent", "apartment rent",
        "society maintenance", "home loan", "mortgage", "car loan", "auto-debit",
        "mutual fund sip", "sip", "broadband", "electricity bill", "water bill"
    ]

    for norm_name, items in groups.items():
        is_known_commitment = any(kw in norm_name for kw in HOUSE_AND_BILL_KEYWORDS)

        # Single occurrence check for explicit house rent / housing loan
        if len(items) == 1 and is_known_commitment:
            idx, txn = items[0]
            recurring_indices.add(idx)
            txn_date = txn["date"]
            patterns.append({
                "description": txn["description"],
                "normalized_name": norm_name,
                "typical_amount": float(txn["amount"]),
                "frequency": "monthly",
                "day_of_period": txn_date.day if hasattr(txn_date, "day") else 1,
                "next_expected": (txn_date + timedelta(days=30)) if hasattr(txn_date, "day") else None,
                "confidence": 0.85,
                "category_id": txn.get("category_id"),
            })
            continue

        if len(items) < 2:
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
            if is_known_commitment:
                for idx, _ in items:
                    recurring_indices.add(idx)
            continue

        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        cv = std_interval / mean_interval if mean_interval > 0 else 1.0

        # Regular cadence check: weekly (~7d), monthly (~25-35d), quarterly (~90d), annual (~365d)
        is_recurring = False
        frequency = "monthly"

        allowed_cv = 0.45 if is_known_commitment else 0.35

        if 5 <= mean_interval <= 10 and cv < allowed_cv:
            is_recurring = True
            frequency = "weekly"
        elif 20 <= mean_interval <= 40 and cv < allowed_cv:
            is_recurring = True
            frequency = "monthly"
        elif 75 <= mean_interval <= 105 and cv < allowed_cv:
            is_recurring = True
            frequency = "quarterly"
        elif 340 <= mean_interval <= 390 and cv < allowed_cv:
            is_recurring = True
            frequency = "annual"
        elif is_known_commitment and 15 <= mean_interval <= 45:
            # Special guarantee for house payments / bills
            is_recurring = True
            frequency = "monthly"

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
