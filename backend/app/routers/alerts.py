from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.database import get_db
from app.models.user import User
from app.models.alert import Alert
from app.utils.helpers import get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("")
async def get_alerts(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns alerts for the user (anomalies, recurring payments, low balance).
    """
    filters = [Alert.user_id == current_user.id]
    if unread_only:
        filters.append(Alert.is_read == False)

    stmt = select(Alert).where(and_(*filters)).order_by(desc(Alert.created_at)).limit(50)
    res = await db.execute(stmt)
    records = res.scalars().all()

    return [
        {
            "id": a.id,
            "alert_type": a.alert_type,
            "title": a.title,
            "description": a.description,
            "severity": a.severity,
            "is_read": a.is_read,
            "trigger_date": a.trigger_date.strftime("%Y-%m-%d") if a.trigger_date else None,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for a in records
    ]

@router.patch("/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Alert).where(and_(Alert.id == alert_id, Alert.user_id == current_user.id))
    res = await db.execute(stmt)
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    alert.is_read = True
    await db.commit()
    return {"message": "Alert marked as read."}

@router.get("/upcoming")
async def get_upcoming_alerts(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cutoff = date.today() + timedelta(days=days)
    stmt = (
        select(Alert)
        .where(and_(
            Alert.user_id == current_user.id,
            Alert.alert_type == "recurring_payment",
            Alert.trigger_date <= cutoff
        ))
        .order_by(Alert.trigger_date)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "severity": a.severity,
            "trigger_date": a.trigger_date.strftime("%Y-%m-%d") if a.trigger_date else None,
        }
        for a in records
    ]
