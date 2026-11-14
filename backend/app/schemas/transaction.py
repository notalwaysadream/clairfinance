from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime

class TransactionBase(BaseModel):
    date: date
    description: str
    amount: float
    type: str  # 'credit' | 'debit'
    payment_mode: Optional[str] = "UPI"
    category_id: Optional[str] = None
    raw_description: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    category_id: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    payment_mode: Optional[str] = None

class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    date: date
    description: str
    amount: float
    type: str
    payment_mode: str
    category_id: Optional[str] = None
    category_name: Optional[str] = "Miscellaneous"
    category_icon: Optional[str] = "circle"
    category_color: Optional[str] = "#78716c"
    raw_description: Optional[str] = None
    is_recurring: bool = False
    anomaly_score: float = 0.0
    created_at: Optional[datetime] = None

class TransactionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    transactions: List[TransactionOut]
    items: Optional[List[TransactionOut]] = None

class TransactionSummaryResponse(BaseModel):
    total_income: float
    total_expenses: float
    net_savings: float
    savings_rate: float
    transaction_count: int

class CSVUploadResponse(BaseModel):
    message: str
    total_parsed: int
    total_saved: int
    batch_id: str
    auto_categorized_count: int
    anomalies_detected: int
    recurring_detected: int
    access_token: Optional[str] = None
    persona_id: Optional[str] = None
    errors: List[str] = []
