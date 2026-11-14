from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.alert import Alert, BudgetLimit
from app.schemas.dashboard import (
    DashboardOverview,
    CategorySpending,
    CashFlowPoint,
    HealthScoreBreakdown,
    BudgetStatusItem,
)
from app.schemas.transaction import TransactionOut
from app.utils.helpers import get_current_user
from app.services.health_scorer import calculate_health_score

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns full aggregate view for the main dashboard.
    """
    # 1. Total Income & Expenses
    stmt_totals = (
        select(Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.user_id == current_user.id)
        .group_by(Transaction.type)
    )
    res_totals = await db.execute(stmt_totals)
    totals_map = {r[0]: (r[1] or 0.0) for r in res_totals.all()}
    total_income = totals_map.get("credit", 0.0)
    total_expenses = totals_map.get("debit", 0.0)
    net_savings = total_income - total_expenses
    savings_rate = (net_savings / total_income * 100.0) if total_income > 0 else 0.0

    # 2. Recent Transactions (last 8)
    stmt_recent = (
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(Transaction.user_id == current_user.id)
        .order_by(desc(Transaction.date), desc(Transaction.created_at))
        .limit(8)
    )
    recent_res = await db.execute(stmt_recent)
    recent_txns = [
        TransactionOut(
            id=t.id,
            date=t.date,
            description=t.description,
            amount=t.amount,
            type=t.type,
            payment_mode=t.payment_mode or "UPI",
            category_id=t.category_id,
            category_name=t.category.name if t.category else "Miscellaneous",
            category_icon=t.category.icon if t.category else "circle",
            category_color=t.category.color if t.category else "#78716c",
            raw_description=t.raw_description,
            is_recurring=t.is_recurring,
            anomaly_score=t.anomaly_score,
            created_at=t.created_at
        )
        for t in recent_res.scalars().all()
    ]

    # 3. Category Spending Breakdown (Debits)
    stmt_cat = (
        select(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.sum(Transaction.amount).label("cat_total"),
            func.count(Transaction.id).label("txn_count")
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(and_(Transaction.user_id == current_user.id, Transaction.type == "debit"))
        .group_by(Category.id)
        .order_by(desc("cat_total"))
    )
    res_cat = await db.execute(stmt_cat)
    cat_rows = res_cat.all()

    spending_breakdown = []
    cat_expenses_dict = {}
    for cid, cname, cicon, ccolor, ctotal, ccount in cat_rows:
        ctotal = ctotal or 0.0
        pct = (ctotal / total_expenses * 100.0) if total_expenses > 0 else 0.0
        spending_breakdown.append(CategorySpending(
            category_id=cid,
            category_name=cname,
            icon=cicon,
            color=ccolor,
            total_amount=round(ctotal, 2),
            percentage=round(pct, 1),
            transaction_count=ccount
        ))
        cat_expenses_dict[cname] = ctotal

    # 4. Monthly Cash Flow points
    stmt_cf = (
        select(
            func.strftime("%Y-%m", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("amt")
        )
        .where(Transaction.user_id == current_user.id)
        .group_by("month", Transaction.type)
        .order_by("month")
    )
    res_cf = await db.execute(stmt_cf)
    cf_data = {}
    monthly_expenses_list = []
    for m, t_type, amt in res_cf.all():
        if m not in cf_data:
            cf_data[m] = {"income": 0.0, "expenses": 0.0}
        if t_type == "credit":
            cf_data[m]["income"] += (amt or 0.0)
        elif t_type == "debit":
            cf_data[m]["expenses"] += (amt or 0.0)

    cash_flow_points = []
    for m_label in sorted(cf_data.keys()):
        inc = cf_data[m_label]["income"]
        exp = cf_data[m_label]["expenses"]
        monthly_expenses_list.append(exp)
        cash_flow_points.append(CashFlowPoint(
            period=m_label,
            income=round(inc, 2),
            expenses=round(exp, 2),
            net_savings=round(inc - exp, 2)
        ))

    # 5. Financial Health Score
    stmt_emi = (
        select(func.sum(Transaction.amount))
        .join(Category, Transaction.category_id == Category.id)
        .where(and_(
            Transaction.user_id == current_user.id,
            Transaction.type == "debit",
            Category.name == "EMI & Loans"
        ))
    )
    total_emis = (await db.execute(stmt_emi)).scalar() or 0.0

    health_res = calculate_health_score(
        total_income=total_income,
        total_expenses=total_expenses,
        monthly_expenses_list=monthly_expenses_list,
        total_emis=total_emis,
        current_savings=max(0.0, net_savings),
        category_expenses=cat_expenses_dict
    )

    # 6. Active Alerts Count
    stmt_alerts = (
        select(func.count(Alert.id))
        .where(and_(Alert.user_id == current_user.id, Alert.is_read == False))
    )
    alerts_count = (await db.execute(stmt_alerts)).scalar() or 0

    return DashboardOverview(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        net_savings=round(net_savings, 2),
        savings_rate=round(max(0.0, savings_rate), 1),
        health_score=health_res.total_score,
        health_status=health_res.status,
        active_alerts_count=alerts_count,
        recent_transactions=recent_txns,
        spending_breakdown=spending_breakdown,
        cash_flow=cash_flow_points
    )

@router.get("/cashflow", response_model=List[CashFlowPoint])
async def get_cashflow_chart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
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
    cf_map = {}
    for m, t_type, amt in res.all():
        if m not in cf_map:
            cf_map[m] = {"income": 0.0, "expenses": 0.0}
        if t_type == "credit":
            cf_map[m]["income"] += (amt or 0.0)
        else:
            cf_map[m]["expenses"] += (amt or 0.0)

    points = []
    for m in sorted(cf_map.keys()):
        inc = cf_map[m]["income"]
        exp = cf_map[m]["expenses"]
        points.append(CashFlowPoint(
            period=m,
            income=round(inc, 2),
            expenses=round(exp, 2),
            net_savings=round(inc - exp, 2)
        ))
    return points

@router.get("/spending-breakdown", response_model=List[CategorySpending])
async def get_spending_breakdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt_total = (
        select(func.sum(Transaction.amount))
        .where(and_(Transaction.user_id == current_user.id, Transaction.type == "debit"))
    )
    total_expenses = (await db.execute(stmt_total)).scalar() or 0.0

    stmt = (
        select(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.sum(Transaction.amount).label("cat_total"),
            func.count(Transaction.id).label("txn_count")
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(and_(Transaction.user_id == current_user.id, Transaction.type == "debit"))
        .group_by(Category.id)
        .order_by(desc("cat_total"))
    )
    res = await db.execute(stmt)
    results = []
    for cid, cname, cicon, ccolor, ctotal, ccount in res.all():
        ctotal = ctotal or 0.0
        pct = (ctotal / total_expenses * 100.0) if total_expenses > 0 else 0.0
        results.append(CategorySpending(
            category_id=cid,
            category_name=cname,
            icon=cicon,
            color=ccolor,
            total_amount=round(ctotal, 2),
            percentage=round(pct, 1),
            transaction_count=ccount
        ))
    return results

@router.get("/health-score", response_model=HealthScoreBreakdown)
async def get_health_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Total Income and Total Expenses
    stmt_totals = (
        select(Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.user_id == current_user.id)
        .group_by(Transaction.type)
    )
    res_totals = await db.execute(stmt_totals)
    totals = {r[0]: (r[1] or 0.0) for r in res_totals.all()}
    total_income = totals.get("credit", 0.0)
    total_expenses = totals.get("debit", 0.0)

    # Monthly breakdown for variation
    stmt_monthly = (
        select(func.strftime("%Y-%m", Transaction.date).label("m"), func.sum(Transaction.amount))
        .where(and_(Transaction.user_id == current_user.id, Transaction.type == "debit"))
        .group_by("m")
    )
    monthly_expenses = [float(r[1] or 0.0) for r in (await db.execute(stmt_monthly)).all()]

    # Category expenses
    stmt_cat = (
        select(Category.name, func.sum(Transaction.amount))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(and_(Transaction.user_id == current_user.id, Transaction.type == "debit"))
        .group_by(Category.name)
    )
    cat_exp = {r[0]: float(r[1] or 0.0) for r in (await db.execute(stmt_cat)).all()}
    total_emis = cat_exp.get("EMI & Loans", 0.0)
    current_savings = max(0.0, total_income - total_expenses)

    return calculate_health_score(
        total_income=total_income,
        total_expenses=total_expenses,
        monthly_expenses_list=monthly_expenses,
        total_emis=total_emis,
        current_savings=current_savings,
        category_expenses=cat_exp
    )

@router.get("/budget-status", response_model=List[BudgetStatusItem])
async def get_budget_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns spending vs recommended budget per category.
    """
    stmt = (
        select(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            func.sum(Transaction.amount).label("cat_total"),
            func.count(func.distinct(func.strftime("%Y-%m", Transaction.date))).label("months_count")
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(and_(Transaction.user_id == current_user.id, Transaction.type == "debit"))
        .group_by(Category.id)
        .order_by(desc("cat_total"))
    )
    res = await db.execute(stmt)
    items = []
    for cid, cname, cicon, ccolor, ctotal, m_cnt in res.all():
        months = max(1, m_cnt or 1)
        avg_monthly = (ctotal or 0.0) / months
        # Recommended monthly limit: avg monthly + 10% buffer
        rec_limit = round(avg_monthly * 1.10, 0)
        # Recent month spending
        pct = min(150.0, (avg_monthly / rec_limit * 100.0)) if rec_limit > 0 else 0.0
        status = "safe"
        if pct > 100.0:
            status = "exceeded"
        elif pct > 80.0:
            status = "warning"

        items.append(BudgetStatusItem(
            category_id=cid,
            category_name=cname,
            icon=cicon,
            color=ccolor,
            actual_spent=round(avg_monthly, 2),
            recommended_limit=rec_limit,
            percentage_used=round(pct, 1),
            status=status
        ))
    return items
