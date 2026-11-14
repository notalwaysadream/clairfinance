from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.simulation import (
    LoanSimulationRequest,
    LoanSimulationResponse,
    PurchaseSimulationRequest,
    PurchaseSimulationResponse,
    SavingsGoalRequest,
    SavingsGoalResponse,
)
from app.utils.helpers import get_current_user
from app.services.simulator import (
    calculate_loan_simulation,
    calculate_purchase_simulation,
    calculate_savings_goal,
)

router = APIRouter(prefix="/simulator", tags=["Simulators"])

@router.post("/loan", response_model=LoanSimulationResponse)
async def simulate_loan(req: LoanSimulationRequest):
    """
    Simulates loan EMI, total interest, and full monthly amortization schedule.
    """
    return calculate_loan_simulation(req)

@router.post("/purchase", response_model=PurchaseSimulationResponse)
async def simulate_purchase(
    req: PurchaseSimulationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Simulates the impact of a large one-time purchase on emergency reserves and savings buffer.
    """
    stmt = (
        select(
            Transaction.type,
            func.sum(Transaction.amount).label("sum_amt"),
            func.count(func.distinct(func.strftime("%Y-%m", Transaction.date))).label("months_count")
        )
        .where(Transaction.user_id == current_user.id)
        .group_by(Transaction.type)
    )
    res = await db.execute(stmt)
    
    total_inc = 0.0
    total_exp = 0.0
    months = 1
    for r_type, r_sum, m_cnt in res.all():
        months = max(months, m_cnt or 1)
        if r_type == "credit":
            total_inc += (r_sum or 0.0)
        else:
            total_exp += (r_sum or 0.0)

    current_savings = max(0.0, total_inc - total_exp)
    avg_exp = total_exp / months if months > 0 else 30000.0
    avg_sav = max(1000.0, (total_inc - total_exp) / months) if months > 0 else 10000.0

    return calculate_purchase_simulation(
        req=req,
        current_savings=current_savings,
        avg_monthly_expenses=avg_exp,
        avg_monthly_savings=avg_sav
    )

@router.post("/savings-goal", response_model=SavingsGoalResponse)
async def simulate_savings_goal(
    req: SavingsGoalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Simulates the timeline to reach a savings goal (e.g., bike down payment, emergency buffer).
    """
    stmt = (
        select(
            Transaction.type,
            func.sum(Transaction.amount).label("sum_amt"),
            func.count(func.distinct(func.strftime("%Y-%m", Transaction.date))).label("months_count")
        )
        .where(Transaction.user_id == current_user.id)
        .group_by(Transaction.type)
    )
    res = await db.execute(stmt)
    
    total_inc = 0.0
    total_exp = 0.0
    months = 1
    for r_type, r_sum, m_cnt in res.all():
        months = max(months, m_cnt or 1)
        if r_type == "credit":
            total_inc += (r_sum or 0.0)
        else:
            total_exp += (r_sum or 0.0)

    avg_inc = total_inc / months if months > 0 else 50000.0
    avg_exp = total_exp / months if months > 0 else 35000.0
    rate = ((avg_inc - avg_exp) / avg_inc * 100.0) if avg_inc > 0 else 0.0

    return calculate_savings_goal(
        req=req,
        current_savings_rate=rate,
        current_monthly_income=avg_inc,
        current_monthly_expenses=avg_exp
    )
