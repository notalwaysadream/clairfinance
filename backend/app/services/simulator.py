import math
from typing import List, Dict, Any, Optional
from app.schemas.simulation import (
    LoanSimulationRequest,
    LoanSimulationResponse,
    MonthlyPaymentSchedule,
    PurchaseSimulationRequest,
    PurchaseSimulationResponse,
    SavingsGoalRequest,
    SavingsGoalResponse,
)

def calculate_loan_simulation(req: LoanSimulationRequest) -> LoanSimulationResponse:
    P = float(req.loan_amount)
    annual_rate = float(req.interest_rate)
    n = int(req.tenure_months)

    if n <= 0 or P <= 0:
        return LoanSimulationResponse(
            emi=0.0,
            total_payment=0.0,
            total_interest=0.0,
            tenure_months=0,
            schedule=[],
            impact_summary="Invalid loan parameters."
        )

    r = (annual_rate / 12.0) / 100.0
    if r > 0:
        emi = (P * r * ((1.0 + r) ** n)) / (((1.0 + r) ** n) - 1.0)
    else:
        emi = P / n

    total_payment = emi * n
    total_interest = total_payment - P

    schedule = []
    balance = P
    for month in range(1, n + 1):
        interest_for_month = balance * r
        principal_for_month = emi - interest_for_month
        balance = max(0.0, balance - principal_for_month)
        schedule.append(MonthlyPaymentSchedule(
            month=month,
            principal_paid=round(principal_for_month, 2),
            interest_paid=round(interest_for_month, 2),
            remaining_balance=round(balance, 2),
            emi=round(emi, 2)
        ))

    summary = (
        f"Borrowing ₹{P:,.0f} at {annual_rate}% over {n} months incurs a monthly EMI of "
        f"₹{emi:,.0f}. Total interest payable is ₹{total_interest:,.0f} ({round((total_interest/P)*100, 1)}% of principal)."
    )

    return LoanSimulationResponse(
        emi=round(emi, 2),
        total_payment=round(total_payment, 2),
        total_interest=round(total_interest, 2),
        tenure_months=n,
        schedule=schedule,
        impact_summary=summary
    )

def calculate_purchase_simulation(
    req: PurchaseSimulationRequest,
    current_savings: float,
    avg_monthly_expenses: float,
    avg_monthly_savings: float
) -> PurchaseSimulationResponse:
    amt = float(req.amount)
    buffer_before = current_savings / avg_monthly_expenses if avg_monthly_expenses > 0 else 6.0
    remaining_savings = max(0.0, current_savings - amt)
    buffer_after = remaining_savings / avg_monthly_expenses if avg_monthly_expenses > 0 else 0.0

    is_safe = buffer_after >= 2.0 and remaining_savings > 0
    if buffer_after >= 3.0:
        verdict = "Safe to Purchase"
    elif buffer_after >= 1.5:
        verdict = "Moderate Risk — Buffer Weakened"
    else:
        verdict = "High Risk — Depletes Emergency Buffer"

    recovery_months = math.ceil(amt / avg_monthly_savings) if avg_monthly_savings > 0 else 12

    recs = []
    if buffer_after < 2.0:
        recs.append(f"After this purchase, your buffer falls to {buffer_after:.1f} months (below recommended 3 months).")
        recs.append(f"Consider saving for an additional {recovery_months} months to avoid cash crunch.")
    else:
        recs.append(f"Your emergency cushion remains healthy at {buffer_after:.1f} months.")
        recs.append(f"At current savings rate, this amount is recouped in {recovery_months} months.")

    return PurchaseSimulationResponse(
        amount=amt,
        current_savings=round(current_savings, 2),
        remaining_savings=round(remaining_savings, 2),
        emergency_buffer_before_months=round(buffer_before, 1),
        emergency_buffer_after_months=round(buffer_after, 1),
        is_safe=is_safe,
        verdict=verdict,
        timeline_recovery_months=recovery_months,
        recommendations=recs
    )

def calculate_savings_goal(
    req: SavingsGoalRequest,
    current_savings_rate: float,
    current_monthly_income: float,
    current_monthly_expenses: float
) -> SavingsGoalResponse:
    goal = float(req.goal_amount)
    monthly_net = max(0.0, current_monthly_income - current_monthly_expenses)
    
    if req.monthly_contribution and req.monthly_contribution > 0:
        monthly_saving = req.monthly_contribution
    else:
        monthly_saving = max(1000.0, monthly_net)

    months = math.ceil(goal / monthly_saving) if monthly_saving > 0 else 60

    if months <= 12:
        feasibility = "Highly Feasible"
    elif months <= 36:
        feasibility = "Achievable with Budgeting"
    else:
        feasibility = "Long Term — Needs Acceleration"

    accelerators = [
        "Automate an SIP/recurring transfer on salary day.",
        "Trimming discretionary food & shopping by 15% cuts goal time by ~20%.",
        "Direct any bonuses or tax refunds directly towards this goal."
    ]

    return SavingsGoalResponse(
        goal_amount=goal,
        current_savings_rate=round(current_savings_rate, 1),
        estimated_months_to_goal=months,
        required_monthly_savings=round(monthly_saving, 2),
        feasibility=feasibility,
        accelerators=accelerators
    )
