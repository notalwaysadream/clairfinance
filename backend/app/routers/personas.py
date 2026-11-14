import os
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.persona import PersonaInfo, PersonaSwitchResponse
from app.utils.helpers import (
    PERSONA_REGISTRY,
    get_active_persona_id,
    set_active_persona_id,
    get_or_create_persona_user,
    create_access_token,
)
from app.services.csv_parser import parse_csv_content
from app.services.categorizer import categorizer
from app.services.anomaly_detector import detect_anomalies
from app.services.recurring_detector import detect_recurring_patterns
from app.services.health_scorer import calculate_health_score

router = APIRouter(prefix="/personas", tags=["Personas"])

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

async def ensure_persona_data_loaded(db: AsyncSession, persona_id: str, user: User):
    """
    Checks if transactions exist for the persona; if not, loads and processes the CSV.
    """
    stmt = select(func.count(Transaction.id)).where(Transaction.user_id == user.id)
    count = (await db.execute(stmt)).scalar() or 0
    if count > 0:
        return count

    persona = PERSONA_REGISTRY[persona_id]
    csv_file = DATA_DIR / persona["csv_file"]
    if not csv_file.exists():
        return 0

    with open(csv_file, "rb") as f:
        raw_txns, _ = parse_csv_content(f.read())

    # Get categories map
    cat_res = await db.execute(select(Category))
    categories = {c.name.lower(): c for c in cat_res.scalars().all()}
    misc_cat = categories.get("miscellaneous")

    # Categorize
    for txn in raw_txns:
        cat_name, _ = categorizer.categorize(txn["description"], txn_type=txn["type"])
        matched = categories.get(cat_name.lower(), misc_cat)
        txn["category_id"] = matched.id if matched else None
        txn["category_name"] = matched.name if matched else "Miscellaneous"

    # Anomalies and Recurring
    raw_txns = detect_anomalies(raw_txns)
    raw_txns, _ = detect_recurring_patterns(raw_txns)

    db_items = [
        Transaction(
            user_id=user.id,
            date=item["date"],
            description=item["description"],
            amount=item["amount"],
            type=item["type"],
            payment_mode=item["payment_mode"],
            category_id=item["category_id"],
            raw_description=item.get("raw_description"),
            is_recurring=item.get("is_recurring", False),
            anomaly_score=item.get("anomaly_score", 0.0),
            upload_batch_id=f"persona-{persona_id}",
        )
        for item in raw_txns
    ]
    db.add_all(db_items)
    await db.commit()
    return len(db_items)

@router.get("", response_model=List[PersonaInfo])
async def list_personas():
    """
    Lists all available test personas (Salaried, Freelancer, Student) and highlights the currently active one.
    """
    active_id = get_active_persona_id()
    result = []
    for pid, p in PERSONA_REGISTRY.items():
        result.append(PersonaInfo(
            id=p["id"],
            name=p["name"],
            email=p["email"],
            role=p["role"],
            avatar_url=p["avatar_url"],
            income_pattern=p["income_pattern"],
            key_characteristics=p["key_characteristics"],
            is_active=(pid == active_id)
        ))
    return result

@router.get("/active", response_model=PersonaInfo)
async def get_active_persona():
    """
    Returns the currently active test persona.
    """
    active_id = get_active_persona_id()
    p = PERSONA_REGISTRY[active_id]
    return PersonaInfo(
        id=p["id"],
        name=p["name"],
        email=p["email"],
        role=p["role"],
        avatar_url=p["avatar_url"],
        income_pattern=p["income_pattern"],
        key_characteristics=p["key_characteristics"],
        is_active=True
    )

@router.post("/switch/{persona_id}", response_model=PersonaSwitchResponse)
async def switch_persona(persona_id: str, db: AsyncSession = Depends(get_db)):
    """
    One-Click Persona Switcher:
    Switches active profile to Salaried, Freelancer, or Student.
    Loads 12-month transaction dataset if needed and returns an active JWT token and summary financial stats.
    """
    persona_id = persona_id.lower()
    if persona_id not in PERSONA_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona '{persona_id}' not found. Available personas: {list(PERSONA_REGISTRY.keys())}"
        )

    # 1. Get or create user for this persona
    user = await get_or_create_persona_user(db, persona_id)

    # 2. Ensure their 12-month dataset is loaded
    txn_count = await ensure_persona_data_loaded(db, persona_id, user)

    # 3. Set as active persona
    set_active_persona_id(persona_id)

    # 4. Generate JWT Token
    token = create_access_token({"sub": user.id, "email": user.email, "persona": persona_id})

    # 5. Compute Quick Financial Stats
    stmt_totals = (
        select(Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.user_id == user.id)
        .group_by(Transaction.type)
    )
    res_totals = await db.execute(stmt_totals)
    totals = {r[0]: (r[1] or 0.0) for r in res_totals.all()}
    total_inc = totals.get("credit", 0.0)
    total_exp = totals.get("debit", 0.0)
    net_sav = total_inc - total_exp
    sav_rate = (net_sav / total_inc * 100.0) if total_inc > 0 else 0.0

    # Monthly breakdown for health score
    stmt_monthly = (
        select(func.sum(Transaction.amount))
        .where(and_(Transaction.user_id == user.id, Transaction.type == "debit"))
        .group_by(func.strftime("%Y-%m", Transaction.date))
    )
    monthly_expenses = [float(r[0] or 0.0) for r in (await db.execute(stmt_monthly)).all()]

    health = calculate_health_score(
        total_income=total_inc,
        total_expenses=total_exp,
        monthly_expenses_list=monthly_expenses,
        total_emis=0.0,
        current_savings=max(0.0, net_sav),
        category_expenses={}
    )

    p = PERSONA_REGISTRY[persona_id]
    info = PersonaInfo(
        id=p["id"],
        name=p["name"],
        email=p["email"],
        role=p["role"],
        avatar_url=p["avatar_url"],
        income_pattern=p["income_pattern"],
        key_characteristics=p["key_characteristics"],
        is_active=True
    )

    return PersonaSwitchResponse(
        message=f"Successfully switched to {p['name']} ({p['role']}).",
        active_persona=info,
        access_token=token,
        total_income=round(total_inc, 2),
        total_expenses=round(total_exp, 2),
        net_savings=round(net_sav, 2),
        savings_rate=round(max(0.0, sav_rate), 1),
        health_score=health.total_score,
        health_status=health.status,
        transactions_count=txn_count
    )

@router.post("/seed-all")
async def seed_all_personas(db: AsyncSession = Depends(get_db)):
    """
    Pre-populates all 3 personas into the database simultaneously so switching is instantaneous.
    """
    results = {}
    for pid in PERSONA_REGISTRY.keys():
        user = await get_or_create_persona_user(db, pid)
        count = await ensure_persona_data_loaded(db, pid, user)
        results[pid] = {"user": user.email, "transactions_loaded": count}
    return {"message": "All 3 personas successfully seeded.", "details": results}
