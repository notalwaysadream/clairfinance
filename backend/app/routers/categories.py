from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.category import Category

router = APIRouter(prefix="/categories", tags=["Categories"])

class CategoryOut(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    is_default: bool

@router.get("", response_model=List[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """
    Returns all configured system categories.
    """
    stmt = select(Category).order_by(Category.name)
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [
        CategoryOut(
            id=c.id,
            name=c.name,
            icon=c.icon,
            color=c.color,
            is_default=c.is_default
        )
        for c in records
    ]

@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(category_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns details for a single category by UUID.
    """
    stmt = select(Category).where(Category.id == category_id)
    res = await db.execute(stmt)
    cat = res.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    return CategoryOut(
        id=cat.id,
        name=cat.name,
        icon=cat.icon,
        color=cat.color,
        is_default=cat.is_default
    )
