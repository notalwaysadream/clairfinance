#!/usr/bin/env python3
"""
Seed Database with Generated Test Persona CSVs
"""

import sys
import asyncio
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.database import engine, Base, AsyncSessionLocal
from app.models import Category, User, Transaction, DEFAULT_CATEGORIES
from app.utils.helpers import DEV_USER_EMAIL, DEV_USER_NAME, DEV_USER_AVATAR
from app.services.csv_parser import parse_csv_content
from app.services.categorizer import categorizer
from app.services.anomaly_detector import detect_anomalies
from app.services.recurring_detector import detect_recurring_patterns
from sqlalchemy import select

async def seed_data(csv_file: str):
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"Error: CSV file '{csv_file}' not found.")
        return

    print(f"Seeding database with {csv_path.name}...")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Seed categories if not existing
        cat_res = await session.execute(select(Category))
        cats = {c.name.lower(): c for c in cat_res.scalars().all()}
        for cat_def in DEFAULT_CATEGORIES:
            if cat_def["name"].lower() not in cats:
                new_cat = Category(
                    name=cat_def["name"],
                    icon=cat_def["icon"],
                    color=cat_def["color"],
                    is_default=True
                )
                session.add(new_cat)
        await session.commit()

        # Re-fetch categories
        cat_res = await session.execute(select(Category))
        cats = {c.name.lower(): c for c in cat_res.scalars().all()}
        misc_cat = cats.get("miscellaneous")

        # Get or create dev user
        user_res = await session.execute(select(User).where(User.email == DEV_USER_EMAIL))
        dev_user = user_res.scalar_one_or_none()
        if not dev_user:
            dev_user = User(
                email=DEV_USER_EMAIL,
                name=DEV_USER_NAME,
                avatar_url=DEV_USER_AVATAR
            )
            session.add(dev_user)
            await session.commit()
            await session.refresh(dev_user)

        # Read CSV
        with open(csv_path, "rb") as f:
            raw_txns, errors = parse_csv_content(f.read())

        print(f"Parsed {len(raw_txns)} transactions from CSV.")

        # Categorize
        for t in raw_txns:
            c_name, _ = categorizer.categorize(t["description"], txn_type=t["type"])
            matched = cats.get(c_name.lower(), misc_cat)
            t["category_id"] = matched.id if matched else None
            t["category_name"] = matched.name if matched else "Miscellaneous"

        # Anomalies & Recurring
        raw_txns = detect_anomalies(raw_txns)
        raw_txns, _ = detect_recurring_patterns(raw_txns)

        # Batch insert
        db_items = [
            Transaction(
                user_id=dev_user.id,
                date=item["date"],
                description=item["description"],
                amount=item["amount"],
                type=item["type"],
                payment_mode=item["payment_mode"],
                category_id=item["category_id"],
                raw_description=item.get("raw_description"),
                is_recurring=item.get("is_recurring", False),
                anomaly_score=item.get("anomaly_score", 0.0),
                upload_batch_id="seed-initial",
            )
            for item in raw_txns
        ]
        session.add_all(db_items)
        await session.commit()

        print(f"Successfully loaded {len(db_items)} transactions into SQLite DB for user '{dev_user.email}'.")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "./data/salaried_transactions.csv"
    asyncio.run(seed_data(target))
