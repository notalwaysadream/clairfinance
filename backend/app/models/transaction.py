import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    description = Column(String(500), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(20), nullable=False)  # 'credit' | 'debit'
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), index=True, nullable=True)
    payment_mode = Column(String(50), default="UPI")  # 'UPI', 'NEFT', 'Card', 'Cash', 'EMI'
    raw_description = Column(String(1000), nullable=True)
    is_recurring = Column(Boolean, default=False)
    anomaly_score = Column(Float, default=0.0)
    upload_batch_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
