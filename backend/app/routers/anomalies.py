from datetime import date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.utils.helpers import get_current_user

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])

@router.get("")
async def get_anomalies(
    min_score: float = Query(0.1, ge=0.0, le=1.0),
    category_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists detected spending anomalies exceeding the specified anomaly score threshold.
    """
    filters = [
        Transaction.user_id == current_user.id,
        Transaction.type == "debit",
        Transaction.anomaly_score >= min_score,
    ]
    if category_id:
        filters.append(Transaction.category_id == category_id)

    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(and_(*filters))
        .order_by(desc(Transaction.anomaly_score), desc(Transaction.date))
        .limit(limit)
    )
    records = (await db.execute(stmt)).scalars().all()

    items = []
    for r in records:
        severity = "critical" if r.anomaly_score >= 0.8 else ("warning" if r.anomaly_score >= 0.5 else "info")
        items.append({
            "id": r.id,
            "date": r.date.strftime("%Y-%m-%d"),
            "description": r.description,
            "amount": r.amount,
            "category_id": r.category_id,
            "category_name": r.category.name if r.category else "Miscellaneous",
            "category_icon": r.category.icon if r.category else "circle",
            "category_color": r.category.color if r.category else "#78716c",
            "anomaly_score": r.anomaly_score,
            "severity": severity,
            "payment_mode": r.payment_mode or "UPI"
        })

    return {
        "total_anomalies": len(items),
        "threshold": min_score,
        "anomalies": items
    }

@router.get("/patterns")
async def get_anomaly_patterns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Aggregates statistical patterns of detected spending anomalies:
    category concentrations, weekday distribution, and top outlier spikes.
    """
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(and_(
            Transaction.user_id == current_user.id,
            Transaction.type == "debit",
            Transaction.anomaly_score > 0.0
        ))
        .order_by(desc(Transaction.anomaly_score))
    )
    res = await db.execute(stmt)
    anomalies = res.scalars().all()

    if not anomalies:
        return {
            "total_anomalies": 0,
            "total_anomalous_spend": 0.0,
            "high_severity_count": 0,
            "category_distribution": [],
            "day_of_week_distribution": {},
            "top_outliers": []
        }

    total_spend = sum(a.amount for a in anomalies)
    high_sev = sum(1 for a in anomalies if a.anomaly_score >= 0.7)

    # Category distribution
    cat_counts: Dict[str, Dict[str, Any]] = {}
    for a in anomalies:
        cname = a.category.name if a.category else "Miscellaneous"
        ccolor = a.category.color if a.category else "#78716c"
        if cname not in cat_counts:
            cat_counts[cname] = {"category": cname, "color": ccolor, "count": 0, "total_amount": 0.0}
        cat_counts[cname]["count"] += 1
        cat_counts[cname]["total_amount"] += a.amount

    cat_list = sorted(cat_counts.values(), key=lambda x: x["count"], reverse=True)

    # Day of week distribution (0 = Monday, 6 = Sunday)
    dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_counts = {name: 0 for name in dow_names}
    for a in anomalies:
        dow_idx = a.date.weekday()
        dow_counts[dow_names[dow_idx]] += 1

    # Top outliers
    top_outliers = [
        {
            "id": a.id,
            "date": a.date.strftime("%Y-%m-%d"),
            "description": a.description,
            "amount": a.amount,
            "category_name": a.category.name if a.category else "Miscellaneous",
            "anomaly_score": a.anomaly_score
        }
        for a in anomalies[:5]
    ]

    return {
        "total_anomalies": len(anomalies),
        "total_anomalous_spend": round(total_spend, 2),
        "high_severity_count": high_sev,
        "category_distribution": cat_list,
        "day_of_week_distribution": dow_counts,
        "top_outliers": top_outliers
    }
