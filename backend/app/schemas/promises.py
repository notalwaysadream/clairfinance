from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ShockSimulationRequest(BaseModel):
    shock_day: int = Field(1, ge=1, le=28, description="Day of month when shock occurs (1=tomorrow, 15=mid-month)")
    buffer_amount: float = Field(5000.0, ge=0.0, description="Minimum buffer to maintain")
    current_balance: Optional[float] = Field(None, ge=0.0, description="Current bank balance override")
    shock_amount: Optional[float] = Field(None, ge=0.0, description="Specific shock amount to test")


class BillSimulationRequest(BaseModel):
    bill_name: str = Field("Upcoming Bill", max_length=100)
    bill_amount: float = Field(15000.0, ge=100.0, le=500000.0)
    due_day: int = Field(10, ge=1, le=30)
    buffer_amount: float = Field(5000.0, ge=0.0)
    current_balance: Optional[float] = Field(None, ge=0.0)
    expected_inflow_amount: float = Field(20000.0, ge=0.0)
    expected_inflow_prob: float = Field(0.75, ge=0.0, le=1.0)
    target_risk: float = Field(0.05, ge=0.0, le=1.0)


class Promise1Response(BaseModel):
    has_enough_data: bool
    data_days: int
    X: float
    L: float
    H: float
    base_risk: float
    target_risk: float
    shock_day: int
    buffer_amount: float
    promise_text: str
    message: Optional[str] = None


class Promise2Response(BaseModel):
    bill_name: str
    bill_amount: float
    due_day: int
    risk_A: float
    risk_B: float
    risk_increase: float
    first_shortfall_day: int
    first_shortfall_date: str
    median_shortfall_day: Optional[int] = None
    action_evaluations: List[Dict[str, Any]]
    recommended_actions: List[str]
    start_by_day: int
    start_by_date: str
    mitigated_risk_C: float
    upside_note: Dict[str, Any]
    promise_text: str


class FanChartResponse(BaseModel):
    days: List[str]
    buffer: float
    current_balance: float
    percentiles: Dict[str, List[float]]


class BacktestResponse(BaseModel):
    total_windows_tested: int
    under_5_pct_promise_verified: bool
    empirical_shortfall_rate: float
    guarantee_status: str
    brier_score: float
    calibration_points: List[Dict[str, Any]]
    summary_statement: str


class PromisesOverviewResponse(BaseModel):
    promise_1: Dict[str, Any]
    promise_2: Dict[str, Any]
    fan_chart: Dict[str, Any]
    backtest: Dict[str, Any]
    current_balance: float
    buffer_amount: float
    user_name: str
