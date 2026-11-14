import json
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User
from app.models.chat_history import ChatHistory
from app.schemas.query import QueryHistoryOut
from app.utils.helpers import get_current_user

router = APIRouter(prefix="/history", tags=["History"])

@router.get("", response_model=List[QueryHistoryOut])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(ChatHistory)
        .where(ChatHistory.user_id == current_user.id)
        .order_by(desc(ChatHistory.created_at))
        .limit(50)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    out = []
    for r in records:
        try:
            resp = json.loads(r.response_json)
        except Exception:
            resp = {}

        out.append(QueryHistoryOut(
            id=r.id,
            query_text=r.query_text,
            query_type=r.query_type,
            confidence_score=r.confidence_score,
            response=resp,
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M")
        ))
    return out
