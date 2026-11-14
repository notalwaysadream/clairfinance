import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.chat_history import ChatHistory
from app.schemas.query import QueryAskRequest, QueryAskResponse, QueryHistoryOut
from app.utils.helpers import get_current_user
from app.services.query_engine import evaluate_affordability
from app.services.health_scorer import calculate_health_score

router = APIRouter(prefix="/query", tags=["Can I Afford This?"])

@router.post("/ask", response_model=QueryAskResponse)
async def ask_financial_query(
    req: QueryAskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Core AI Financial Advisor endpoint. Answers 'Can I afford this?' questions
    with structured verdicts, impact charts, risks, and alternatives.
    """
    # 1. Compute User Financial Metrics
    stmt_totals = (
        select(
            Transaction.type,
            func.sum(Transaction.amount).label("sum_amt"),
            func.count(func.distinct(func.strftime("%Y-%m", Transaction.date))).label("months_count")
        )
        .where(Transaction.user_id == current_user.id)
        .group_by(Transaction.type)
    )
    res_totals = await db.execute(stmt_totals)
    
    total_inc = 0.0
    total_exp = 0.0
    months_active = 1
    for r_type, r_sum, m_cnt in res_totals.all():
        months_active = max(months_active, m_cnt or 1)
        if r_type == "credit":
            total_inc += (r_sum or 0.0)
        else:
            total_exp += (r_sum or 0.0)

    avg_monthly_income = total_inc / months_active if months_active > 0 else 50000.0
    avg_monthly_expenses = total_exp / months_active if months_active > 0 else 35000.0
    current_savings = max(0.0, total_inc - total_exp)

    # 2. Existing EMIs
    stmt_emi = (
        select(func.sum(Transaction.amount))
        .join(Category, Transaction.category_id == Category.id)
        .where(and_(
            Transaction.user_id == current_user.id,
            Transaction.type == "debit",
            Category.name == "EMI & Loans"
        ))
    )
    existing_emis = (await db.execute(stmt_emi)).scalar() or 0.0
    existing_emis_monthly = existing_emis / months_active if months_active > 0 else 0.0

    # 3. Monthly expenses list for health score
    stmt_monthly = (
        select(func.sum(Transaction.amount))
        .where(and_(Transaction.user_id == current_user.id, Transaction.type == "debit"))
        .group_by(func.strftime("%Y-%m", Transaction.date))
    )
    m_exp_list = [float(r[0] or 0.0) for r in (await db.execute(stmt_monthly)).all()]

    health = calculate_health_score(
        total_income=total_inc,
        total_expenses=total_exp,
        monthly_expenses_list=m_exp_list,
        total_emis=existing_emis,
        current_savings=current_savings,
        category_expenses={}
    )

    # Determine persona type
    persona_type = "salaried"
    if "priya" in current_user.email.lower() or "freelancer" in current_user.email.lower():
        persona_type = "freelancer"
    elif "amit" in current_user.email.lower() or "student" in current_user.email.lower():
        persona_type = "student"

    # 4. Fetch recent chat history for Contextual AI Memory (last 5 inquiries)
    stmt_prev = (
        select(ChatHistory)
        .where(ChatHistory.user_id == current_user.id)
        .order_by(desc(ChatHistory.created_at))
        .limit(5)
    )
    prev_records = (await db.execute(stmt_prev)).scalars().all()
    past_queries_context = []
    for pr in prev_records:
        verdict_val = "evaluated"
        try:
            p_data = json.loads(pr.response_json)
            verdict_val = p_data.get("verdict", "evaluated")
        except Exception:
            pass
        past_queries_context.append({
            "query_text": pr.query_text,
            "verdict": verdict_val,
            "created_at": pr.created_at.strftime("%Y-%m-%d") if pr.created_at else ""
        })

    # 5. Run Evaluation Engine with contextual memory
    result = await evaluate_affordability(
        req=req,
        avg_monthly_income=avg_monthly_income,
        avg_monthly_expenses=avg_monthly_expenses,
        current_savings=current_savings,
        existing_emis=existing_emis_monthly,
        health_score=health.total_score,
        persona_type=persona_type,
        past_queries=past_queries_context
    )

    # 6. Store in Chat History
    chat_entry = ChatHistory(
        user_id=current_user.id,
        query_text=f"{req.item_name} (₹{req.estimated_price:,.0f}, {req.payment_method})",
        query_type="affordability",
        response_json=json.dumps(result.model_dump()),
        confidence_score=result.confidence,
    )
    db.add(chat_entry)
    await db.commit()

    return result

@router.get("/history", response_model=List[QueryHistoryOut])
async def get_query_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(ChatHistory)
        .where(ChatHistory.user_id == current_user.id)
        .order_by(desc(ChatHistory.created_at))
        .limit(20)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    out = []
    for r in records:
        try:
            resp_data = json.loads(r.response_json)
        except Exception:
            resp_data = {}

        out.append(QueryHistoryOut(
            id=r.id,
            query_text=r.query_text,
            query_type=r.query_type,
            confidence_score=r.confidence_score,
            response=resp_data,
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M")
        ))
    return out

@router.get("/{query_id}", response_model=QueryHistoryOut)
async def get_single_query(
    query_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ChatHistory).where(
        and_(ChatHistory.id == query_id, ChatHistory.user_id == current_user.id)
    )
    res = await db.execute(stmt)
    rec = res.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Query record not found.")

    try:
        resp_data = json.loads(rec.response_json)
    except Exception:
        resp_data = {}

    return QueryHistoryOut(
        id=rec.id,
        query_text=rec.query_text,
        query_type=rec.query_type,
        confidence_score=rec.confidence_score,
        response=resp_data,
        created_at=rec.created_at.strftime("%Y-%m-%d %H:%M")
    )
