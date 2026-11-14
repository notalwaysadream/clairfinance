import uuid
from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, delete
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.alert import Alert, RecurringPattern
from app.schemas.transaction import (
    TransactionOut,
    TransactionListResponse,
    TransactionSummaryResponse,
    TransactionUpdate,
    CSVUploadResponse,
)
from app.utils.helpers import (
    get_current_user,
    get_or_create_persona_user,
    set_active_persona_id,
    create_access_token,
)
from app.services.csv_parser import parse_csv_content
from app.services.categorizer import categorizer
from app.services.anomaly_detector import detect_anomalies
from app.services.recurring_detector import detect_recurring_patterns

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.post("/upload", response_model=CSVUploadResponse)
async def upload_transactions_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Uploads a bank statement CSV, validates, auto-categorizes, runs anomaly & recurring detection,
    and stores records in database.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV (.csv) file."
        )

    content = await file.read()
    raw_txns, parse_errors = parse_csv_content(content)

    if not raw_txns:
        err_msg = "; ".join(parse_errors[:3]) if parse_errors else "Please verify that the CSV has columns for Date, Description/Merchant, and Amount/Amt."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse valid transactions from the uploaded CSV: {err_msg}"
        )

    # Use the isolated Custom user so uploaded statements do not mix with pre-seeded demo personas
    custom_user = await get_or_create_persona_user(db, "custom")
    target_user_id = custom_user.id
    set_active_persona_id("custom")

    # Clear previous transactions, alerts, and recurring patterns for the custom statement
    await db.execute(delete(Alert).where(Alert.user_id == target_user_id))
    await db.execute(delete(RecurringPattern).where(RecurringPattern.user_id == target_user_id))
    await db.execute(delete(Transaction).where(Transaction.user_id == target_user_id))

    # Fetch all categories from DB for ID resolution
    cat_stmt = select(Category)
    cat_res = await db.execute(cat_stmt)
    categories = {c.name.lower(): c for c in cat_res.scalars().all()}
    misc_cat = categories.get("miscellaneous")

    # Step 1: Auto-categorize each transaction with 3-tier pipeline
    category_names_list = [c.name for c in cat_res.scalars().all()]
    categorization_results = await categorizer.categorize_batch_with_llm(raw_txns, category_names_list)

    categorized_count = 0
    for txn, (cat_name, conf) in zip(raw_txns, categorization_results):
        matched_cat = categories.get(cat_name.lower(), misc_cat)
        if matched_cat:
            txn["category_id"] = matched_cat.id
            txn["category_name"] = matched_cat.name
            categorized_count += 1
        else:
            txn["category_id"] = None
            txn["category_name"] = "Miscellaneous"

    # Step 2: Recurring Pattern Detection (Runs BEFORE Anomaly Detection so recurring payments are marked)
    raw_txns, recurring_patterns = detect_recurring_patterns(raw_txns)
    recurring_detected = sum(1 for t in raw_txns if t.get("is_recurring", False))

    # Step 3: Anomaly Detection (Recurring payments like house rent / EMIs are assigned score 0.0)
    raw_txns = detect_anomalies(raw_txns)
    anomalies_detected = sum(1 for t in raw_txns if t.get("anomaly_score", 0.0) > 0.0)

    batch_id = str(uuid.uuid4())[:8]

    # Step 4: Persist to DB under target_user_id
    db_txns = []
    for item in raw_txns:
        txn_obj = Transaction(
            user_id=target_user_id,
            date=item["date"],
            description=item["description"],
            amount=item["amount"],
            type=item["type"],
            payment_mode=item["payment_mode"],
            category_id=item["category_id"],
            raw_description=item.get("raw_description"),
            is_recurring=item.get("is_recurring", False),
            anomaly_score=item.get("anomaly_score", 0.0),
            upload_batch_id=batch_id,
        )
        db_txns.append(txn_obj)

    db.add_all(db_txns)

    # Create alerts for high anomalies detected (never for recurring transactions)
    for txn in raw_txns:
        if txn.get("anomaly_score", 0.0) >= 0.7 and not txn.get("is_recurring", False):
            alert = Alert(
                user_id=target_user_id,
                alert_type="anomaly",
                title=f"Unusual Spend: ₹{txn['amount']:,.0f} on {txn['category_name']}",
                description=f"Transaction '{txn['description']}' was flagged as unusually high for category '{txn['category_name']}'.",
                severity="warning",
                trigger_date=txn["date"]
            )
            db.add(alert)

    # Record recurring patterns
    for pat in recurring_patterns:
        rec_obj = RecurringPattern(
            user_id=target_user_id,
            description=pat["description"],
            category_id=pat.get("category_id"),
            typical_amount=pat["typical_amount"],
            frequency=pat["frequency"],
            day_of_period=pat["day_of_period"],
            next_expected=pat["next_expected"],
            confidence=pat["confidence"]
        )
        db.add(rec_obj)

        # Create alert for upcoming recurring payment
        alert = Alert(
            user_id=target_user_id,
            alert_type="recurring_payment",
            title=f"Upcoming {pat['frequency'].title()} Payment: ₹{pat['typical_amount']:,.0f}",
            description=f"Recurring charge expected for '{pat['description']}' around {pat['next_expected']}.",
            severity="info",
            trigger_date=pat["next_expected"]
        )
        db.add(alert)

    await db.commit()

    token = create_access_token({"sub": custom_user.email, "user_id": custom_user.id, "persona": "custom"})

    return CSVUploadResponse(
        message="CSV successfully parsed, categorized, and stored.",
        total_parsed=len(raw_txns),
        total_saved=len(db_txns),
        batch_id=batch_id,
        auto_categorized_count=categorized_count,
        anomalies_detected=anomalies_detected,
        recurring_detected=recurring_detected,
        access_token=token,
        persona_id="custom",
        errors=parse_errors[:10]
    )

@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    limit: Optional[int] = None,
    category_id: Optional[str] = None,
    txn_type: Optional[str] = Query(None, alias="type"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns paginated list of transactions with flexible search and filtering.
    """
    actual_size = max(1, min(500, limit or page_size))
    filters = [Transaction.user_id == current_user.id]

    if category_id:
        filters.append(Transaction.category_id == category_id)
    if txn_type and isinstance(txn_type, str):
        filters.append(Transaction.type == txn_type.lower())
    if start_date:
        filters.append(Transaction.date >= start_date)
    if end_date:
        filters.append(Transaction.date <= end_date)
    if search:
        filters.append(Transaction.description.ilike(f"%{search}%"))

    # Count total
    count_stmt = select(func.count()).select_from(Transaction).where(and_(*filters))
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Query page
    offset = (page - 1) * actual_size
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(and_(*filters))
        .order_by(desc(Transaction.date), desc(Transaction.created_at))
        .offset(offset)
        .limit(actual_size)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()

    txns_out = []
    for r in records:
        txns_out.append(TransactionOut(
            id=r.id,
            date=r.date,
            description=r.description,
            amount=r.amount,
            type=r.type,
            payment_mode=r.payment_mode or "UPI",
            category_id=r.category_id,
            category_name=r.category.name if r.category else "Miscellaneous",
            category_icon=r.category.icon if r.category else "circle",
            category_color=r.category.color if r.category else "#78716c",
            raw_description=r.raw_description,
            is_recurring=r.is_recurring,
            anomaly_score=r.anomaly_score,
            created_at=r.created_at
        ))

    total_pages = (total_count + actual_size - 1) // actual_size if total_count > 0 else 1

    return TransactionListResponse(
        total=total_count,
        page=page,
        page_size=actual_size,
        total_pages=total_pages,
        transactions=txns_out,
        items=txns_out
    )

@router.get("/summary", response_model=TransactionSummaryResponse)
async def get_transactions_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Aggregates total income, total expenses, net savings, and savings rate.
    """
    filters = [Transaction.user_id == current_user.id]
    if start_date:
        filters.append(Transaction.date >= start_date)
    if end_date:
        filters.append(Transaction.date <= end_date)

    stmt = (
        select(
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count")
        )
        .where(and_(*filters))
        .group_by(Transaction.type)
    )
    res = await db.execute(stmt)
    rows = res.all()

    total_income = 0.0
    total_expenses = 0.0
    total_count = 0

    for r_type, r_sum, r_cnt in rows:
        total_count += r_cnt
        if r_type == "credit":
            total_income += (r_sum or 0.0)
        elif r_type == "debit":
            total_expenses += (r_sum or 0.0)

    net_savings = total_income - total_expenses
    savings_rate = (net_savings / total_income * 100.0) if total_income > 0 else 0.0

    return TransactionSummaryResponse(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        net_savings=round(net_savings, 2),
        savings_rate=round(max(0.0, savings_rate), 1),
        transaction_count=total_count
    )

@router.get("/{txn_id}", response_model=TransactionOut)
async def get_transaction(
    txn_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(and_(Transaction.id == txn_id, Transaction.user_id == current_user.id))
    )
    res = await db.execute(stmt)
    txn = res.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    return TransactionOut(
        id=txn.id,
        date=txn.date,
        description=txn.description,
        amount=txn.amount,
        type=txn.type,
        payment_mode=txn.payment_mode or "UPI",
        category_id=txn.category_id,
        category_name=txn.category.name if txn.category else "Miscellaneous",
        category_icon=txn.category.icon if txn.category else "circle",
        category_color=txn.category.color if txn.category else "#78716c",
        raw_description=txn.raw_description,
        is_recurring=txn.is_recurring,
        anomaly_score=txn.anomaly_score,
        created_at=txn.created_at
    )

@router.patch("/{txn_id}", response_model=TransactionOut)
async def update_transaction(
    txn_id: str,
    update_data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.category))
        .where(and_(Transaction.id == txn_id, Transaction.user_id == current_user.id))
    )
    res = await db.execute(stmt)
    txn = res.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    if update_data.category_id is not None:
        txn.category_id = update_data.category_id
        # Active learning feedback: learn from user correction
        cat_stmt = select(Category).where(Category.id == update_data.category_id)
        cat_obj = (await db.execute(cat_stmt)).scalar_one_or_none()
        if cat_obj:
            categorizer.record_user_correction(txn.description, cat_obj.name)
    if update_data.description is not None:
        txn.description = update_data.description
    if update_data.amount is not None:
        txn.amount = update_data.amount
    if update_data.type is not None:
        txn.type = update_data.type
    if update_data.payment_mode is not None:
        txn.payment_mode = update_data.payment_mode

    await db.commit()
    await db.refresh(txn)

    return TransactionOut(
        id=txn.id,
        date=txn.date,
        description=txn.description,
        amount=txn.amount,
        type=txn.type,
        payment_mode=txn.payment_mode or "UPI",
        category_id=txn.category_id,
        category_name=txn.category.name if txn.category else "Miscellaneous",
        category_icon=txn.category.icon if txn.category else "circle",
        category_color=txn.category.color if txn.category else "#78716c",
        raw_description=txn.raw_description,
        is_recurring=txn.is_recurring,
        anomaly_score=txn.anomaly_score,
        created_at=txn.created_at
    )

@router.delete("/{txn_id}")
async def delete_transaction(
    txn_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Transaction).where(and_(Transaction.id == txn_id, Transaction.user_id == current_user.id))
    res = await db.execute(stmt)
    txn = res.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    await db.delete(txn)
    await db.commit()
    return {"message": "Transaction deleted successfully."}
