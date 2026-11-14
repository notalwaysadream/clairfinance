from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)

PERSONA_REGISTRY: Dict[str, Dict[str, Any]] = {
    "salaried": {
        "id": "salaried",
        "name": "Rahul Sharma",
        "email": "demo.rahul@clairfinance.com",
        "role": "Salaried Tech Professional",
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop",
        "csv_file": "salaried_transactions.csv",
        "persona_type": "salaried",
        "income_pattern": "Fixed monthly salary (₹75k–₹95k) on 1st of every month",
        "key_characteristics": "Predictable income, regular rent, car EMI, SIPs, steady cash flow",
    },
    "freelancer": {
        "id": "freelancer",
        "name": "Priya Patel",
        "email": "demo.priya@clairfinance.com",
        "role": "Independent UI/UX Freelancer",
        "avatar_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=100&h=100&fit=crop",
        "csv_file": "freelancer_transactions.csv",
        "persona_type": "freelancer",
        "income_pattern": "Irregular client payments (₹25k–₹1.2L) across 2–4 invoices/month",
        "key_characteristics": "Volatile income, SaaS subscriptions (Figma/AWS), coworking space, feast-or-famine cycles",
    },
    "student": {
        "id": "student",
        "name": "Amit Verma",
        "email": "demo.amit@clairfinance.com",
        "role": "Engineering College Student",
        "avatar_url": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=100&h=100&fit=crop",
        "csv_file": "student_transactions.csv",
        "persona_type": "student",
        "income_pattern": "Pocket money allowance (₹8k–₹12k) + occasional tutoring (₹3k–₹5k)",
        "key_characteristics": "Tight budget, UPI micro-payments, mess fees, semi-annual semester fee spikes",
    },
}

_active_persona_id = "salaried"

def get_active_persona_id() -> str:
    global _active_persona_id
    return _active_persona_id

def set_active_persona_id(persona_id: str):
    global _active_persona_id
    if persona_id in PERSONA_REGISTRY:
        _active_persona_id = persona_id

DEV_USER_EMAIL = PERSONA_REGISTRY["salaried"]["email"]
DEV_USER_NAME = PERSONA_REGISTRY["salaried"]["name"]
DEV_USER_AVATAR = PERSONA_REGISTRY["salaried"]["avatar_url"]

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_or_create_persona_user(db: AsyncSession, persona_id: str) -> User:
    persona = PERSONA_REGISTRY.get(persona_id, PERSONA_REGISTRY["salaried"])
    stmt = select(User).where(User.email == persona["email"])
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        user = User(
            email=persona["email"],
            name=persona["name"],
            avatar_url=persona["avatar_url"],
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user

async def get_or_create_dev_user(db: AsyncSession) -> User:
    return await get_or_create_persona_user(db, get_active_persona_id())

async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validates JWT token if provided.
    If no token is provided, returns user for the currently active persona.
    """
    if not auth or not auth.credentials:
        # Fallback to currently active persona
        return await get_or_create_persona_user(db, get_active_persona_id())

    token = auth.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            return await get_or_create_persona_user(db, get_active_persona_id())
    except JWTError:
        return await get_or_create_persona_user(db, get_active_persona_id())

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return await get_or_create_persona_user(db, get_active_persona_id())

    return user
