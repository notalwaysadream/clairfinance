import math
from typing import List, Dict, Any, Tuple
import numpy as np

def detect_anomalies(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Computes statistical Z-Score per category for debit transactions.
    Flags transactions where |z| > 2.5 as unusual spending anomalies.
    Returns the list with updated 'anomaly_score' (0.0 to 1.0).
    """
    category_amounts = {}
    for txn in transactions:
        if txn.get("type") == "debit":
            cat = txn.get("category_name", "Miscellaneous")
            amt = float(txn.get("amount", 0.0))
            if amt > 0:
                category_amounts.setdefault(cat, []).append(amt)

    # Calculate mean and standard deviation per category
    category_stats = {}
    for cat, amounts in category_amounts.items():
        if len(amounts) >= 3:
            arr = np.array(amounts)
            mean = float(np.mean(arr))
            std = float(np.std(arr))
            if std == 0:
                std = 1.0
            category_stats[cat] = (mean, std)

    flagged_count = 0
    for txn in transactions:
        if txn.get("type") == "debit":
            cat = txn.get("category_name", "Miscellaneous")
            amt = float(txn.get("amount", 0.0))
            if cat in category_stats:
                mean, std = category_stats[cat]
                z_score = (amt - mean) / std
                if z_score > 2.5:
                    # Normalize z-score into 0.5 - 1.0 range
                    norm_score = min(1.0, 0.5 + (z_score - 2.5) * 0.1)
                    txn["anomaly_score"] = round(norm_score, 2)
                    flagged_count += 1
                else:
                    txn["anomaly_score"] = 0.0
            else:
                txn["anomaly_score"] = 0.0
        else:
            txn["anomaly_score"] = 0.0

    return transactions
