from pydantic import BaseModel
from typing import List, Optional
from app.schemas.transaction import TransactionOut

class CategorySpending(BaseModel):
    category_id: Optional[str] = None
    category_name: str
    icon: str
    color: str
    total_amount: float
    percentage: float
    transaction_count: int

class CashFlowPoint(BaseModel):
    period: str  # e.g., "2025-10" or "2025-11-01"
    income: float
    expenses: float
    net_savings: float

class HealthScoreComponent(BaseModel):
    name: str
    score: float
    max_score: float
    value: str
    description: str

class HealthScoreBreakdown(BaseModel):
    total_score: int
    status: str  # "Excellent" | "Good" | "Fair" | "Needs Work"
    status_color: str
    components: List[HealthScoreComponent]
    recommendations: List[str]

class BudgetStatusItem(BaseModel):
    category_id: str
    category_name: str
    icon: str
    color: str
    actual_spent: float
    recommended_limit: float
    user_limit: Optional[float] = None
    percentage_used: float
    status: str  # "safe" | "warning" | "exceeded"

class DashboardOverview(BaseModel):
    total_income: float
    total_expenses: float
    net_savings: float
    savings_rate: float
    health_score: int
    health_status: str
    active_alerts_count: int
    recent_transactions: List[TransactionOut]
    spending_breakdown: List[CategorySpending]
    cash_flow: List[CashFlowPoint]
