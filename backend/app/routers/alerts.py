from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.alert import Alert, RecurringPattern, BudgetLimit
from app.utils.helpers import get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("")
async def get_alerts(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns alerts for the user (anomalies, recurring payments, low balance).
    """
    filters = [Alert.user_id == current_user.id]
    if unread_only:
        filters.append(Alert.is_read == False)

    stmt = select(Alert).where(and_(*filters)).order_by(desc(Alert.created_at)).limit(50)
    res = await db.execute(stmt)
    records = res.scalars().all()

    return [
        {
            "id": a.id,
            "alert_type": a.alert_type,
            "title": a.title,
            "description": a.description,
            "severity": a.severity,
            "is_read": a.is_read,
            "trigger_date": a.trigger_date.strftime("%Y-%m-%d") if a.trigger_date else None,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for a in records
    ]

@router.patch("/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Alert).where(and_(Alert.id == alert_id, Alert.user_id == current_user.id))
    res = await db.execute(stmt)
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    alert.is_read = True
    await db.commit()
    return {"message": "Alert marked as read."}

@router.get("/upcoming")
async def get_upcoming_alerts(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cutoff = date.today() + timedelta(days=days)
    stmt = (
        select(Alert)
        .where(and_(
            Alert.user_id == current_user.id,
            Alert.alert_type == "recurring_payment",
            Alert.trigger_date <= cutoff
        ))
        .order_by(Alert.trigger_date)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "severity": a.severity,
            "trigger_date": a.trigger_date.strftime("%Y-%m-%d") if a.trigger_date else None,
        }
        for a in records
    ]

@router.get("/predictive")
async def get_predictive_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Smart predictive alert intelligence: analyzes category spending velocity against budgets
    and evaluates upcoming recurring commitments against liquid cash buffers.
    """
    predictive_alerts = []

    # 1. Check liquidity buffer against upcoming 30d commitments
    stmt_totals = (
        select(Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.user_id == current_user.id)
        .group_by(Transaction.type)
    )
    totals = {r[0]: (r[1] or 0.0) for r in (await db.execute(stmt_totals)).all()}
    net_buffer = max(0.0, totals.get("credit", 0.0) - totals.get("debit", 0.0))

    cutoff = date.today() + timedelta(days=30)
    stmt_rec = (
        select(RecurringPattern)
        .where(and_(
            RecurringPattern.user_id == current_user.id,
            RecurringPattern.next_expected <= cutoff
        ))
    )
    rec_patterns = (await db.execute(stmt_rec)).scalars().all()
    upcoming_commitments = sum(p.typical_amount for p in rec_patterns)

    if upcoming_commitments > 0 and (upcoming_commitments > net_buffer * 0.6 or net_buffer < 15000.0):
        predictive_alerts.append({
            "alert_type": "liquidity_crunch_warning",
            "title": f"Liquidity Crunch Warning: ₹{upcoming_commitments:,.0f} Due in 30 Days",
            "description": (
                f"Upcoming recurring bills of ₹{upcoming_commitments:,.0f} absorb a significant share of your "
                f"estimated liquid cushion (₹{net_buffer:,.0f}). Consider deferring non-essential discretionary purchases."
            ),
            "severity": "critical" if upcoming_commitments > net_buffer else "warning",
            "projected_deficit": max(0.0, upcoming_commitments - net_buffer),
        })

    # 2. Category budget burn rate evaluation
    stmt_cats = (
        select(
            Category.id,
            Category.name,
            func.sum(Transaction.amount).label("cat_total"),
            func.count(func.distinct(func.strftime("%Y-%m", Transaction.date))).label("months_count")
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(and_(Transaction.user_id == current_user.id, Transaction.type == "debit"))
        .group_by(Category.id)
    )
    cat_rows = (await db.execute(stmt_cats)).all()

    # Query custom user budget limits
    bl_stmt = select(BudgetLimit).where(BudgetLimit.user_id == current_user.id)
    user_limits = {b.category_id: b.user_limit for b in (await db.execute(bl_stmt)).scalars().all() if b.user_limit is not None}

    for cid, cname, ctotal, m_cnt in cat_rows:
        months = max(1, m_cnt or 1)
        avg_mo = (ctotal or 0.0) / months
        limit = user_limits.get(cid, round(avg_mo * 1.10, 0))

        # Check latest month spending pace
        stmt_latest = (
            select(func.sum(Transaction.amount))
            .where(and_(
                Transaction.user_id == current_user.id,
                Transaction.category_id == cid,
                Transaction.type == "debit",
                func.strftime("%Y-%m", Transaction.date) == date.today().strftime("%Y-%m")
            ))
        )
        spent_this_month = (await db.execute(stmt_latest)).scalar() or avg_mo
        day_of_month = max(1, date.today().day)
        daily_rate = spent_this_month / day_of_month
        projected_month_end = daily_rate * 30.0

        if projected_month_end > limit * 1.15 and limit > 1000.0:
            overrun = projected_month_end - limit
            predictive_alerts.append({
                "alert_type": "budget_pace_exceeded",
                "title": f"Spend Pace Warning: {cname}",
                "description": (
                    f"At your current spend rate of ₹{daily_rate:,.0f}/day, {cname} is projected to reach "
                    f"₹{projected_month_end:,.0f} by month-end, exceeding your limit by ₹{overrun:,.0f}."
                ),
                "severity": "warning",
                "category_id": cid,
                "projected_overrun": round(overrun, 2)
            })

    return {
        "total_predictive_alerts": len(predictive_alerts),
        "alerts": predictive_alerts
    }
