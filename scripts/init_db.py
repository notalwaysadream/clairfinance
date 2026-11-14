#!/usr/bin/env python3
"""
Clairfinance Database Initializer
Creates all database tables, seeds default categories, dev user, and all demo personas.
"""
import sys
import asyncio
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.database import engine, Base, AsyncSessionLocal
from app.main import seed_initial_data
from app.routers.personas import seed_all_personas

async def main():
    print("🔧 Ensuring database tables and default categories exist...")
    await seed_initial_data()
    print("🌱 Seeding demo personas (Salaried, Freelancer, Student)...")
    async with AsyncSessionLocal() as session:
        res = await seed_all_personas(session)
        print(f"✅ Seeding finished: {res.get('message', 'Done')}")
    print("🎉 Clairfinance Database ready.")

if __name__ == "__main__":
    asyncio.run(main())
