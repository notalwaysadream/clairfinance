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
