from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.utils.helpers import get_current_user, get_data_dir, PERSONA_REGISTRY, get_active_persona_id
from app.services.csv_parser import parse_csv_content
from app.services.promises_engine import CashFlowSimulator
from app.schemas.promises import (
    ShockSimulationRequest,
    BillSimulationRequest,
    PromisesOverviewResponse,
    Promise1Response,
    Promise2Response,
    FanChartResponse,
    BacktestResponse,
)

router = APIRouter(prefix="/promises", tags=["Refined Promises"])


async def _get_user_transactions(user: User, db: AsyncSession):
    """
    Retrieves transactions for the user. If user has no database transactions yet,
    loads the pre-seeded active persona dataset as a fallback.
    """
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.date)
    )
    res = await db.execute(stmt)
    txns_db = res.scalars().all()

    if txns_db:
        return [
            {
                "date": str(t.date),
                "amount": float(t.amount),
                "type": str(t.type),
                "description": t.description,
                "category_name": t.category.name if t.category else "Miscellaneous"
            }
            for t in txns_db
        ]

    # Fallback to active persona CSV
    active_pid = get_active_persona_id()
    persona = PERSONA_REGISTRY.get(active_pid, PERSONA_REGISTRY["salaried"])
    csv_file = get_data_dir() / persona.get("csv_file", "salaried_transactions.csv")
    if csv_file.exists():
        with open(csv_file, "rb") as f:
            raw_txns, _ = parse_csv_content(f.read())
            return raw_txns

    return []


@router.get("/overview", response_model=PromisesOverviewResponse)
async def get_promises_overview(
    buffer_amount: float = Query(5000.0, ge=0.0),
    current_balance: Optional[float] = Query(None, ge=0.0),
    shock_day: int = Query(1, ge=1, le=28),
    bill_name: str = Query("Upcoming Medical / Annual Insurance"),
    bill_amount: float = Query(15000.0, ge=100.0),
    bill_due_day: int = Query(10, ge=1, le=30),
    expected_inflow_amount: float = Query(20000.0, ge=0.0),
    expected_inflow_prob: float = Query(0.75, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns full Refined Promises analysis:
      1. Promise 1: Shock Absorption ("You could absorb about ₹X (₹L–₹H)")
      2. Promise 2: Bill Risk & Dynamic Action Plan ("This bill raises risk from A% to B%...")
      3. Monte Carlo 30-day Fan Chart percentiles (5th, 25th, 50th, 75th, 95th)
      4. Rolling Backtest certification and calibration metrics.
    """
    txns = await _get_user_transactions(current_user, db)
    sim = CashFlowSimulator(
        txns,
        current_balance=current_balance,
        buffer_amount=buffer_amount,
        n_paths=5000,
        seed=42
    )

    p1 = sim.promise_1_shock_absorption(shock_day=shock_day)
    p2 = sim.promise_2_bill_impact(
        bill_name=bill_name,
        bill_amount=bill_amount,
        due_day=bill_due_day,
        expected_inflow_amount=expected_inflow_amount,
        expected_inflow_prob=expected_inflow_prob
    )
    prospective = {"name": bill_name, "amount": bill_amount, "due_day": bill_due_day}
    fan = sim.get_fan_chart_data(prospective_bill=prospective)
    bt = sim.run_rolling_backtest()

    return PromisesOverviewResponse(
        promise_1=p1,
        promise_2=p2,
        fan_chart=fan,
        backtest=bt,
        current_balance=sim.current_balance,
        buffer_amount=sim.buffer_amount,
        user_name=current_user.name or "Member"
    )


@router.post("/simulate-bill", response_model=Promise2Response)
async def simulate_bill_impact(
    req: BillSimulationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Recalculates Promise 2 and Action Plan for a user-specified prospective bill.
    """
    txns = await _get_user_transactions(current_user, db)
    sim = CashFlowSimulator(
        txns,
        current_balance=req.current_balance,
        buffer_amount=req.buffer_amount,
        n_paths=5000,
        seed=42
    )
    p2 = sim.promise_2_bill_impact(
        bill_name=req.bill_name,
        bill_amount=req.bill_amount,
        due_day=req.due_day,
        expected_inflow_amount=req.expected_inflow_amount,
        expected_inflow_prob=req.expected_inflow_prob,
        target_risk=req.target_risk
    )
    return Promise2Response(**p2)


@router.post("/simulate-shock", response_model=Promise1Response)
async def simulate_shock_absorption(
    req: ShockSimulationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Recalculates Promise 1 for tomorrow (Day 1) or mid-month (Day 15).
    """
    txns = await _get_user_transactions(current_user, db)
    sim = CashFlowSimulator(
        txns,
        current_balance=req.current_balance,
        buffer_amount=req.buffer_amount,
        n_paths=5000,
        seed=42
    )
    p1 = sim.promise_1_shock_absorption(shock_day=req.shock_day)
    return Promise1Response(**p1)


@router.get("/backtest", response_model=BacktestResponse)
async def get_backtest_calibration(
    buffer_amount: float = Query(5000.0, ge=0.0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns empirical rolling backtest evaluation and calibration chart data points.
    """
    txns = await _get_user_transactions(current_user, db)
    sim = CashFlowSimulator(
        txns,
        buffer_amount=buffer_amount,
        n_paths=3000,
        seed=42
    )
    bt = sim.run_rolling_backtest()
    return BacktestResponse(**bt)
