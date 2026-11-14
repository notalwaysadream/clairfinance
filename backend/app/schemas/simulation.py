from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class LoanSimulationRequest(BaseModel):
    loan_amount: float
    interest_rate: float  # Annual %
    tenure_months: int

class MonthlyPaymentSchedule(BaseModel):
    month: int
    principal_paid: float
    interest_paid: float
    remaining_balance: float
    emi: float

class LoanSimulationResponse(BaseModel):
    emi: float
    total_payment: float
    total_interest: float
    tenure_months: int
    schedule: List[MonthlyPaymentSchedule]
    impact_summary: str

class PurchaseSimulationRequest(BaseModel):
    amount: float
    item_name: Optional[str] = "Major Purchase"
    planned_month: Optional[int] = 1

class PurchaseSimulationResponse(BaseModel):
    amount: float
    current_savings: float
    remaining_savings: float
    emergency_buffer_before_months: float
    emergency_buffer_after_months: float
    is_safe: bool
    verdict: str
    timeline_recovery_months: int
    recommendations: List[str]

class SavingsGoalRequest(BaseModel):
    goal_amount: float
    target_months: Optional[int] = None
    monthly_contribution: Optional[float] = None

class SavingsGoalResponse(BaseModel):
    goal_amount: float
    current_savings_rate: float
    estimated_months_to_goal: int
    required_monthly_savings: float
    feasibility: str
    accelerators: List[str]

class WhatIfMonthPoint(BaseModel):
    month: str
    baseline_balance: float
    simulated_balance: float
    net_difference: float

class WhatIfSimulationRequest(BaseModel):
    scenario_name: Optional[str] = "What-If Scenario"
    income_change_percent: Optional[float] = 0.0
    monthly_expense_change: Optional[float] = 0.0
    one_time_inflow: Optional[float] = 0.0
    one_time_outflow: Optional[float] = 0.0
    projection_months: Optional[int] = 6

class WhatIfSimulationResponse(BaseModel):
    scenario_name: str
    baseline_monthly_income: float
    baseline_monthly_expenses: float
    baseline_monthly_savings: float
    simulated_monthly_income: float
    simulated_monthly_expenses: float
    simulated_monthly_savings: float
    net_change_in_annual_savings: float
    buffer_change_months: float
    verdict: str
    monthly_projection: List[WhatIfMonthPoint]
    insights: List[str]

class EMIOptimizerRequest(BaseModel):
    proposed_loan_amount: float
    proposed_interest_rate: float
    proposed_tenure_months: int
    lump_sum_prepayment_available: Optional[float] = 0.0

class OptimizationScenario(BaseModel):
    scenario_id: str
    title: str
    description: str
    combined_monthly_emi: float
    total_interest_payable: float
    interest_saved_vs_baseline: float
    dti_ratio_percent: float
    recommendation_level: str  # "Highly Recommended", "Viable Alternative", "Baseline"

class EMIOptimizerResponse(BaseModel):
    current_monthly_debt: float
    proposed_new_emi: float
    standard_combined_emi: float
    scenarios: List[OptimizationScenario]
    advisor_summary: str
