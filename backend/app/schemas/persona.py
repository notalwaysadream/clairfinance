from pydantic import BaseModel
from typing import Optional, List

class PersonaInfo(BaseModel):
    id: str
    name: str
    email: str
    role: str
    avatar_url: str
    income_pattern: str
    key_characteristics: str
    is_active: bool

class PersonaSwitchResponse(BaseModel):
    message: str
    active_persona: PersonaInfo
    access_token: str
    token_type: str = "bearer"
    total_income: float
    total_expenses: float
    net_savings: float
    savings_rate: float
    health_score: int
    health_status: str
    transactions_count: int
