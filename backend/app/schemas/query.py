from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class QueryAskRequest(BaseModel):
    item_name: str
    estimated_price: float
    payment_method: str = "emi"  # "one_time" | "emi" | "loan"
    emi_tenure_months: Optional[int] = 24
    interest_rate: Optional[float] = 12.5  # % per annum
    link: Optional[str] = None
    additional_context: Optional[str] = None

class AffordabilityImpact(BaseModel):
    current_monthly_savings: float
    projected_monthly_savings: float
    savings_reduction_percent: float
    months_until_strain: Optional[int] = None

class CashFlowImpactPoint(BaseModel):
    month: str
    baseline_savings: float
    projected_savings: float
    projected_balance: float

class QueryAskResponse(BaseModel):
    verdict: str  # "easily_affordable" | "affordable_with_caution" | "risky" | "not_recommended"
    confidence: float
    monthly_emi: float
    impact: AffordabilityImpact
    analysis: str
    risks: List[str]
    alternatives: List[str]
    reasoning: str
    cash_flow_impact_chart_data: List[Dict[str, Any]] = []

class QueryHistoryOut(BaseModel):
    id: str
    query_text: str
    query_type: str
    confidence_score: float
    response: Dict[str, Any]
    created_at: str
