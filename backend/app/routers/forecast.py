from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.prediction import Prediction
from app.models.alert import RecurringPattern
from app.utils.helpers import get_current_user
from app.services.forecaster import (
    forecast_cashflow,
    forecast_category_spending,
    backtest_forecast,
)

router = APIRouter(prefix="/forecast", tags=["Forecasting"])

@router.get("/cashflow")
async def get_forecast_cashflow(
    months: int = Query(3, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns forward time-series cash flow predictions with lower and upper confidence intervals.
    """
    stmt = (
        select(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("amt")
        )
        .where(Transaction.user_id == current_user.id)
        .group_by("month", Transaction.type)
        .order_by("month")
    )
    res = await db.execute(stmt)
    
    monthly_dict = {}
    for m, t_type, amt in res.all():
        if m not in monthly_dict:
            monthly_dict[m] = {"month": m, "income": 0.0, "expenses": 0.0}
        if t_type == "credit":
            monthly_dict[m]["income"] += (amt or 0.0)
        else:
            monthly_dict[m]["expenses"] += (amt or 0.0)

    history = [monthly_dict[k] for k in sorted(monthly_dict.keys())]
    predictions = forecast_cashflow(history, months_ahead=months)

    # Persist predictions to PREDICTIONS table for forecasting tracking & backtesting
    for pred in predictions:
        pred_m = pred.get("month", "")
        try:
            parts = [int(p) for p in pred_m.split("-")]
            pred_date = date(parts[0], parts[1], 1)
        except Exception:
            continue

        pred_stmt = select(Prediction).where(and_(
            Prediction.user_id == current_user.id,
            Prediction.prediction_date == pred_date,
            Prediction.prediction_type == "monthly"
        ))
        existing_pred = (await db.execute(pred_stmt)).scalar_one_or_none()

        if existing_pred:
            existing_pred.predicted_amount = pred["predicted_expenses"]
            existing_pred.lower_bound = pred["lower_bound"]
            existing_pred.upper_bound = pred["upper_bound"]
            existing_pred.confidence = pred["confidence"]
        else:
            db_pred = Prediction(
                user_id=current_user.id,
                prediction_date=pred_date,
                predicted_amount=pred["predicted_expenses"],
                lower_bound=pred["lower_bound"],
                upper_bound=pred["upper_bound"],
                confidence=pred["confidence"],
                prediction_type="monthly"
            )
            db.add(db_pred)

    await db.commit()

    return {
        "months_ahead": months,
        "historical_periods": len(history),
        "forecast": predictions
    }

@router.get("/category/{category_id}")
async def get_category_forecast(
    category_id: str,
    months: int = Query(3, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Category-specific forward spending forecast with confidence bands and trend velocity.
    """
    cat_res = await db.execute(select(Category).where(Category.id == category_id))
    cat = cat_res.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    stmt = (
        select(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            func.sum(Transaction.amount).label("total")
        )
        .where(and_(
            Transaction.user_id == current_user.id,
            Transaction.category_id == category_id,
            Transaction.type == "debit"
        ))
        .group_by("month")
        .order_by("month")
    )
    rows = (await db.execute(stmt)).all()
    monthly_data = [{"month": r[0], "amount": float(r[1] or 0.0)} for r in rows]

    forecast_res = forecast_category_spending(monthly_data, months_ahead=months)

    return {
        "category_id": cat.id,
        "category_name": cat.name,
        "category_icon": cat.icon,
        "category_color": cat.color,
        "months_ahead": months,
        **forecast_res
    }

@router.get("/categories")
async def get_all_category_forecasts(
    months: int = Query(3, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns forward forecasts for all spending categories that have historical transactions.
    """
    stmt = (
        select(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.strftime("%Y-%m", Transaction.date).label("month"),
            func.sum(Transaction.amount).label("total")
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(and_(
            Transaction.user_id == current_user.id,
            Transaction.type == "debit"
        ))
        .group_by(Category.id, "month")
        .order_by(Category.name, "month")
    )
    rows = (await db.execute(stmt)).all()

    grouped_data: Dict[str, Dict[str, Any]] = {}
    for cid, cname, cicon, ccolor, m, total in rows:
        if cid not in grouped_data:
            grouped_data[cid] = {
                "category_id": cid,
                "category_name": cname,
                "category_icon": cicon,
                "category_color": ccolor,
                "monthly_data": []
            }
        grouped_data[cid]["monthly_data"].append({"month": m, "amount": float(total or 0.0)})

    category_forecasts = []
    for cid, cinfo in grouped_data.items():
        fc = forecast_category_spending(cinfo["monthly_data"], months_ahead=months)
        next_month_pred = fc["forecast"][0]["predicted_amount"] if fc["forecast"] else 0.0
        category_forecasts.append({
            "category_id": cid,
            "category_name": cinfo["category_name"],
            "category_icon": cinfo["category_icon"],
            "category_color": cinfo["category_color"],
            "trend": fc["trend"],
            "trend_percentage": fc["trend_percentage"],
            "average_monthly_spend": fc["average_monthly_spend"],
            "next_month_predicted": next_month_pred,
            "forecast": fc["forecast"]
        })

    category_forecasts.sort(key=lambda x: x["next_month_predicted"], reverse=True)
    return category_forecasts

@router.get("/accuracy")
async def get_forecast_accuracy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Backtesting evaluation: compares AI predictions with actual historical data.
    """
    stmt = (
        select(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("amt")
        )
        .where(Transaction.user_id == current_user.id)
        .group_by("month", Transaction.type)
        .order_by("month")
    )
    res = await db.execute(stmt)

    monthly_dict = {}
    for m, t_type, amt in res.all():
        if m not in monthly_dict:
            monthly_dict[m] = {"month": m, "income": 0.0, "expenses": 0.0}
        if t_type == "credit":
            monthly_dict[m]["income"] += (amt or 0.0)
        else:
            monthly_dict[m]["expenses"] += (amt or 0.0)

    history = [monthly_dict[k] for k in sorted(monthly_dict.keys())]
    return backtest_forecast(history)

@router.get("/recurring")
async def get_recurring_forecast(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns detected recurring subscriptions, EMIs, and upcoming bill occurrences.
    """
    stmt = (
        select(RecurringPattern)
        .where(RecurringPattern.user_id == current_user.id)
        .order_by(RecurringPattern.next_expected)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    items = []
    total_monthly_recurring = 0.0
    for r in records:
        if r.frequency == "monthly":
            total_monthly_recurring += r.typical_amount
        elif r.frequency == "weekly":
            total_monthly_recurring += r.typical_amount * 4
        elif r.frequency == "quarterly":
            total_monthly_recurring += r.typical_amount / 3
        elif r.frequency == "annual":
            total_monthly_recurring += r.typical_amount / 12

        items.append({
            "id": r.id,
            "description": r.description,
            "typical_amount": r.typical_amount,
            "frequency": r.frequency,
            "day_of_period": r.day_of_period,
            "next_expected": r.next_expected.strftime("%Y-%m-%d") if r.next_expected else None,
            "confidence": r.confidence,
        })

    return {
        "total_patterns": len(items),
        "estimated_monthly_recurring": round(total_monthly_recurring, 2),
        "patterns": items
    }

@router.get("/liquidity")
async def get_liquidity_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Checks if projected expenses and upcoming recurring bills risk causing a cash crunch.
    """
    # 1. Total income & expense
    stmt_totals = (
        select(Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.user_id == current_user.id)
        .group_by(Transaction.type)
    )
    res_totals = await db.execute(stmt_totals)
    totals = {r[0]: (r[1] or 0.0) for r in res_totals.all()}
    net_savings = totals.get("credit", 0.0) - totals.get("debit", 0.0)

    # 2. Upcoming recurring in next 30 days
    today = date.today()
    next_month = today + timedelta(days=30)
    stmt_rec = (
        select(RecurringPattern)
        .where(and_(
            RecurringPattern.user_id == current_user.id,
            RecurringPattern.next_expected <= next_month
        ))
    )
    res_rec = await db.execute(stmt_rec)
    patterns = res_rec.scalars().all()
    upcoming_total = sum(p.typical_amount for p in patterns)

    is_crunch_likely = (net_savings < upcoming_total) or (net_savings < 10000.0)

    return {
        "current_balance": round(max(0.0, net_savings), 2),
        "upcoming_30d_commitments": round(upcoming_total, 2),
        "is_shortage_risk": is_crunch_likely,
        "warning_message": (
            f"Caution: Upcoming obligations of ₹{upcoming_total:,.0f} exceed or leave tight margins on your current buffer of ₹{max(0.0, net_savings):,.0f}."
            if is_crunch_likely
            else "Liquidity looks safe for the next 30 days."
        )
    }
