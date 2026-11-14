import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Boolean, Date, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    alert_type = Column(String(50), nullable=False)  # 'recurring_payment', 'anomaly', 'low_balance', 'budget_exceeded'
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="info")  # 'info', 'warning', 'critical'
    is_read = Column(Boolean, default=False)
    trigger_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="alerts")

class BudgetLimit(Base):
    __tablename__ = "budget_limits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), index=True, nullable=False)
    recommended_limit = Column(Float, nullable=False)
    user_limit = Column(Float, nullable=True)
    period = Column(String(20), default="monthly")  # 'monthly', 'weekly'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="budget_limits")
    category = relationship("Category", back_populates="budget_limits")

class RecurringPattern(Base):
    __tablename__ = "recurring_patterns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    description = Column(String(255), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    typical_amount = Column(Float, nullable=False)
    frequency = Column(String(20), default="monthly")  # 'monthly', 'weekly', 'quarterly', 'annual'
    day_of_period = Column(Integer, default=1)
    next_expected = Column(Date, nullable=True)
    confidence = Column(Float, default=0.9)
    detected_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="recurring_patterns")
    category = relationship("Category", back_populates="recurring_patterns")
