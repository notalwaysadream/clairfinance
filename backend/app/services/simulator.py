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
    WhatIfSimulationRequest,
    WhatIfSimulationResponse,
    WhatIfMonthPoint,
    EMIOptimizerRequest,
    EMIOptimizerResponse,
    OptimizationScenario,
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

def calculate_what_if_simulation(
    req: WhatIfSimulationRequest,
    current_savings: float,
    current_monthly_income: float,
    current_monthly_expenses: float
) -> WhatIfSimulationResponse:
    inc_pct = float(req.income_change_percent or 0.0)
    exp_delta = float(req.monthly_expense_change or 0.0)
    inflow = float(req.one_time_inflow or 0.0)
    outflow = float(req.one_time_outflow or 0.0)
    n_months = max(1, min(24, int(req.projection_months or 6)))

    base_inc = float(current_monthly_income)
    base_exp = float(current_monthly_expenses)
    base_sav = base_inc - base_exp

    sim_inc = max(0.0, base_inc * (1.0 + (inc_pct / 100.0)))
    sim_exp = max(0.0, base_exp + exp_delta)
    sim_sav = sim_inc - sim_exp

    monthly_delta = sim_sav - base_sav
    annual_delta = (monthly_delta * 12.0) + inflow - outflow

    base_buffer = current_savings / base_exp if base_exp > 0 else 6.0
    initial_sim_savings = max(0.0, current_savings + inflow - outflow)
    sim_buffer = initial_sim_savings / sim_exp if sim_exp > 0 else 6.0
    buffer_change = sim_buffer - base_buffer

    # Monthly projections
    projection = []
    base_running = current_savings
    sim_running = initial_sim_savings

    for m in range(1, n_months + 1):
        base_running += base_sav
        sim_running += sim_sav
        diff = sim_running - base_running
        projection.append(WhatIfMonthPoint(
            month=f"Month {m}",
            baseline_balance=round(base_running, 2),
            simulated_balance=round(sim_running, 2),
            net_difference=round(diff, 2)
        ))

    # Verdict and insights
    insights = []
    if sim_sav < 0:
        verdict = "Unsustainable Deficit"
        insights.append(
            f"This scenario leads to a monthly deficit of ₹{abs(sim_sav):,.0f}, exhausting reserves rapidly."
        )
    elif sim_sav > base_sav * 1.25:
        verdict = "Substantially Accelerated Savings"
        insights.append(
            f"Boosts monthly savings by {((sim_sav - base_sav) / max(1.0, base_sav)) * 100:.1f}%, adding ₹{annual_delta:,.0f} annually."
        )
    elif sim_sav >= base_sav:
        verdict = "Positive Financial Expansion"
        insights.append(
            f"Maintains a positive trajectory with net annual improvement of ₹{annual_delta:,.0f}."
        )
    else:
        verdict = "Narrowed Financial Buffer"
        insights.append(
            f"Reduces monthly surplus by ₹{abs(monthly_delta):,.0f}. Emergency cushion contracts by {abs(buffer_change):.1f} months."
        )

    if inflow > 0:
        insights.append(f"One-time inflow of ₹{inflow:,.0f} provides an immediate liquidity boost.")
    if outflow > 0:
        insights.append(f"One-time outflow of ₹{outflow:,.0f} absorbs near-term cash buffer.")

    return WhatIfSimulationResponse(
        scenario_name=req.scenario_name or "What-If Scenario",
        baseline_monthly_income=round(base_inc, 2),
        baseline_monthly_expenses=round(base_exp, 2),
        baseline_monthly_savings=round(base_sav, 2),
        simulated_monthly_income=round(sim_inc, 2),
        simulated_monthly_expenses=round(sim_exp, 2),
        simulated_monthly_savings=round(sim_sav, 2),
        net_change_in_annual_savings=round(annual_delta, 2),
        buffer_change_months=round(buffer_change, 1),
        verdict=verdict,
        monthly_projection=projection,
        insights=insights
    )

def calculate_emi_optimization(
    req: EMIOptimizerRequest,
    current_monthly_income: float,
    existing_monthly_emi: float
) -> EMIOptimizerResponse:
    P = float(req.proposed_loan_amount)
    annual_rate = float(req.proposed_interest_rate)
    n = int(req.proposed_tenure_months)
    prepay_avail = float(req.lump_sum_prepayment_available or 0.0)
    income = max(10000.0, current_monthly_income)
    existing_debt = float(existing_monthly_emi)

    def compute_emi(principal: float, rate_pct: float, tenure: int) -> float:
        if tenure <= 0 or principal <= 0:
            return 0.0
        r_mo = (rate_pct / 12.0) / 100.0
        if r_mo == 0:
            return principal / tenure
        return (principal * r_mo * ((1.0 + r_mo) ** tenure)) / (((1.0 + r_mo) ** tenure) - 1.0)

    # Baseline: new loan standard EMI
    base_new_emi = compute_emi(P, annual_rate, n)
    base_total_payment = base_new_emi * n
    base_interest = base_total_payment - P
    standard_combined_emi = existing_debt + base_new_emi
    base_dti = (standard_combined_emi / income) * 100.0

    scenarios = []

    # Scenario 1: Standard Additive Commitment
    scenarios.append(OptimizationScenario(
        scenario_id="standard",
        title="Standard Direct Financing",
        description=f"Add new EMI of ₹{base_new_emi:,.0f} directly to existing obligations for {n} months.",
        combined_monthly_emi=round(standard_combined_emi, 2),
        total_interest_payable=round(base_interest, 2),
        interest_saved_vs_baseline=0.0,
        dti_ratio_percent=round(base_dti, 1),
        recommendation_level="Baseline"
    ))

    # Scenario 2: Principal Prepayment / Down Payment Reduction
    if prepay_avail > 0:
        reduced_principal = max(1000.0, P - prepay_avail)
        prep_emi = compute_emi(reduced_principal, annual_rate, n)
        prep_interest = (prep_emi * n) - reduced_principal
        prep_combined = existing_debt + prep_emi
        prep_dti = (prep_combined / income) * 100.0
        interest_saved = base_interest - prep_interest

        scenarios.append(OptimizationScenario(
            scenario_id="prepayment",
            title=f"Lump-Sum Down Payment (₹{prepay_avail:,.0f})",
            description=f"Apply ₹{prepay_avail:,.0f} upfront to reduce principal to ₹{reduced_principal:,.0f}, cutting monthly EMI to ₹{prep_emi:,.0f}.",
            combined_monthly_emi=round(prep_combined, 2),
            total_interest_payable=round(prep_interest, 2),
            interest_saved_vs_baseline=round(interest_saved, 2),
            dti_ratio_percent=round(prep_dti, 1),
            recommendation_level="Highly Recommended"
        ))

    # Scenario 3: Tenure Restructuring
    if base_dti > 40.0:
        # Stretch tenure to reduce monthly burden below 35%
        stretched_n = n + 12
        stretch_emi = compute_emi(P, annual_rate, stretched_n)
        stretch_interest = (stretch_emi * stretched_n) - P
        stretch_combined = existing_debt + stretch_emi
        stretch_dti = (stretch_combined / income) * 100.0

        scenarios.append(OptimizationScenario(
            scenario_id="tenure_extension",
            title=f"Tenure Extension ({stretched_n} Months)",
            description=f"Extend tenure by 12 months to soften monthly EMI to ₹{stretch_emi:,.0f}, easing monthly debt burden.",
            combined_monthly_emi=round(stretch_combined, 2),
            total_interest_payable=round(stretch_interest, 2),
            interest_saved_vs_baseline=round(base_interest - stretch_interest, 2),
            dti_ratio_percent=round(stretch_dti, 1),
            recommendation_level="Viable Alternative"
        ))
    else:
        # Accelerated tenure to save maximum interest
        accel_n = max(6, n - 12)
        accel_emi = compute_emi(P, annual_rate, accel_n)
        accel_interest = (accel_emi * accel_n) - P
        accel_combined = existing_debt + accel_emi
        accel_dti = (accel_combined / income) * 100.0
        accel_interest_saved = max(0.0, base_interest - accel_interest)

        scenarios.append(OptimizationScenario(
            scenario_id="accelerated_payoff",
            title=f"Accelerated Payoff ({accel_n} Months)",
            description=f"Shorten tenure to {accel_n} months. Saves ₹{accel_interest_saved:,.0f} in interest while maintaining safe DTI.",
            combined_monthly_emi=round(accel_combined, 2),
            total_interest_payable=round(accel_interest, 2),
            interest_saved_vs_baseline=round(accel_interest_saved, 2),
            dti_ratio_percent=round(accel_dti, 1),
            recommendation_level="Highly Recommended" if accel_dti <= 35.0 else "Viable Alternative"
        ))

    summary = (
        f"Borrowing ₹{P:,.0f} adds ₹{base_new_emi:,.0f}/month to your existing ₹{existing_debt:,.0f} debt. "
        f"Total debt obligations would represent {base_dti:.1f}% of your monthly income."
    )
    if prepay_avail > 0:
        summary += f" Utilizing your ₹{prepay_avail:,.0f} down payment saves interest and lowers DTI."

    return EMIOptimizerResponse(
        current_monthly_debt=round(existing_debt, 2),
        proposed_new_emi=round(base_new_emi, 2),
        standard_combined_emi=round(standard_combined_emi, 2),
        scenarios=scenarios,
        advisor_summary=summary
    )
