import uuid
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, index=True, nullable=False)
    icon = Column(String(50), nullable=False)
    color = Column(String(20), nullable=False)
    is_default = Column(Boolean, default=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="category")
    budget_limits = relationship("BudgetLimit", back_populates="category")
    recurring_patterns = relationship("RecurringPattern", back_populates="category")
