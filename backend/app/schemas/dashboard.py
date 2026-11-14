from pydantic import BaseModel
from typing import List, Optional, Dict, Any
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

class SetBudgetLimitRequest(BaseModel):
    category_id: str
    user_limit: float
    period: Optional[str] = "monthly"

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

# Spending Personality Profile Schemas
class PersonalityTrait(BaseModel):
    name: str
    rating: int  # 1 to 5
    max_rating: int = 5
    description: str

class PersonalityProfileResponse(BaseModel):
    archetype: str
    badge_icon: str
    title: str
    description: str
    key_strength: str
    key_vulnerability: str
    traits: List[PersonalityTrait]
    actionable_tip: str

# Peer Benchmark Schemas
class BenchmarkMetric(BaseModel):
    metric_name: str
    user_value: float
    peer_average: float
    top_percentile: float
    unit: str
    status: str  # "ahead" | "average" | "behind"

class BenchmarkComparisonResponse(BaseModel):
    cohort_name: str
    cohort_description: str
    metrics: List[BenchmarkMetric]
    cohort_insight: str

# Savings Streak and Milestones Schemas
class SavingsStreakMilestone(BaseModel):
    title: str
    achieved: bool
    description: str
    achieved_date: Optional[str] = None

class SavingsStreakResponse(BaseModel):
    current_streak_months: int
    best_streak_months: int
    total_positive_months: int
    cumulative_savings: float
    milestones: List[SavingsStreakMilestone]

# Calendar Heatmap Schemas
class CalendarDayPoint(BaseModel):
    date: str
    total_amount: float
    total_spend: Optional[float] = None
    transaction_count: int
    intensity: int  # 0 to 4
    top_category: str
    day_number: Optional[int] = None

class CalendarHeatmapResponse(BaseModel):
    start_date: str
    end_date: str
    total_days: int
    total_spent: float
    days: List[CalendarDayPoint]
