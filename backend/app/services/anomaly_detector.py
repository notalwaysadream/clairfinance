import math
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import numpy as np
from sklearn.ensemble import IsolationForest

def detect_anomalies(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Multi-Layered Anomaly Detection Engine per Hackathon Blueprint (Section 7.3):
    Layer 1: Statistical Z-Score per Category (|z| > 2.5 standard deviations).
    Layer 2: Multi-Dimensional Outlier Detection using scikit-learn IsolationForest
             evaluating amount, day of week, day of month, and category encoding.
    Layer 3: Category Frequency Anomaly Detection identifying sudden order surges
             within rolling weekly windows.
    Returns transactions with 'anomaly_score' (0.0 to 1.0) and anomaly flags.
    """
    debit_txns = [t for t in transactions if t.get("type") == "debit"]
    if not debit_txns:
        for t in transactions:
            t["anomaly_score"] = 0.0
        return transactions

    # -------------------------------------------------------------
    # Layer 1: Category Statistical Z-Score
    # -------------------------------------------------------------
    category_amounts = defaultdict(list)
    for txn in debit_txns:
        cat = txn.get("category_name", "Miscellaneous")
        amt = float(txn.get("amount", 0.0))
        if amt > 0:
            category_amounts[cat].append(amt)

    category_stats = {}
    for cat, amounts in category_amounts.items():
        if len(amounts) >= 3:
            arr = np.array(amounts)
            mean = float(np.mean(arr))
            std = float(np.std(arr))
            category_stats[cat] = (mean, std if std > 0 else 1.0)

    z_scores = {}
    for idx, txn in enumerate(debit_txns):
        cat = txn.get("category_name", "Miscellaneous")
        amt = float(txn.get("amount", 0.0))
        if cat in category_stats:
            mean, std = category_stats[cat]
            z = (amt - mean) / std
            if z > 2.5:
                # Normalize z-score to 0.5 - 1.0 range
                norm_z = min(1.0, 0.5 + (z - 2.5) * 0.1)
                z_scores[idx] = norm_z
            else:
                z_scores[idx] = 0.0
        else:
            z_scores[idx] = 0.0

    # -------------------------------------------------------------
    # Layer 2: IsolationForest Multi-Dimensional Clustering
    # -------------------------------------------------------------
    iforest_scores = {}
    if len(debit_txns) >= 20:
        try:
            # Build feature matrix: [amount, day_of_week, day_of_month, category_hash]
            feature_rows = []
            for txn in debit_txns:
                amt = float(txn.get("amount", 0.0))
                d = txn.get("date")
                dow = d.weekday() if hasattr(d, "weekday") else 0
                dom = d.day if hasattr(d, "day") else 1
                cat_name = txn.get("category_name", "Miscellaneous")
                cat_code = abs(hash(cat_name)) % 100
                feature_rows.append([amt, dow, dom, cat_code])

            X = np.array(feature_rows)
            clf = IsolationForest(
                n_estimators=100,
                contamination=0.04,
                random_state=42
            )
            clf.fit(X)
            # decision_function yields negative values for anomalies
            raw_scores = clf.decision_function(X)

            # Map raw negative scores into normalized [0.5, 1.0] anomaly range
            min_raw = float(np.min(raw_scores))
            for idx, raw in enumerate(raw_scores):
                if raw < 0.0:
                    severity = min(1.0, 0.5 + (abs(raw) / max(0.01, abs(min_raw))) * 0.5)
                    iforest_scores[idx] = severity
                else:
                    iforest_scores[idx] = 0.0
        except Exception:
            iforest_scores = {i: 0.0 for i in range(len(debit_txns))}
    else:
        iforest_scores = {i: 0.0 for i in range(len(debit_txns))}

    # -------------------------------------------------------------
    # Layer 3: Weekly Spending Frequency Surge Detection
    # -------------------------------------------------------------
    weekly_frequency = defaultdict(lambda: defaultdict(int))
    for txn in debit_txns:
        cat = txn.get("category_name", "Miscellaneous")
        d = txn.get("date")
        if hasattr(d, "isocalendar"):
            year, week, _ = d.isocalendar()
            week_key = f"{year}-W{week:02d}"
            weekly_frequency[cat][week_key] += 1

    # Identify categories with unusual weekly surge (> 2.5x weekly average)
    surge_weeks = set()
    for cat, weeks_map in weekly_frequency.items():
        if len(weeks_map) >= 3:
            counts = list(weeks_map.values())
            avg_count = float(np.mean(counts))
            for wk, cnt in weeks_map.items():
                if cnt >= 5 and cnt > avg_count * 2.5:
                    surge_weeks.add((cat, wk))

    # -------------------------------------------------------------
    # Combine Multi-Layered Anomaly Scores
    # -------------------------------------------------------------
    for idx, txn in enumerate(debit_txns):
        # Condition: If it's a recurring payment (e.g. house rent, EMI, subscription), it is NOT an anomaly!
        if txn.get("is_recurring", False):
            txn["anomaly_score"] = 0.0
            continue

        z_val = z_scores.get(idx, 0.0)
        if_val = iforest_scores.get(idx, 0.0)

        # Check frequency surge
        freq_boost = 0.0
        d = txn.get("date")
        if hasattr(d, "isocalendar"):
            year, week, _ = d.isocalendar()
            wk_key = f"{year}-W{week:02d}"
            cat = txn.get("category_name", "Miscellaneous")
            if (cat, wk_key) in surge_weeks and float(txn.get("amount", 0.0)) > 500:
                freq_boost = 0.65

        combined_score = max(z_val, if_val, freq_boost)
        txn["anomaly_score"] = round(combined_score, 2)

    # Set non-debit and recurring transactions to 0.0
    for txn in transactions:
        if txn.get("type") != "debit" or txn.get("is_recurring", False):
            txn["anomaly_score"] = 0.0

    return transactions
