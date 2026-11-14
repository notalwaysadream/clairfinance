from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.models import DEFAULT_CATEGORIES, Category, User
from app.utils.helpers import DEV_USER_EMAIL, DEV_USER_NAME, DEV_USER_AVATAR
from app.routers import (
    auth_router,
    personas_router,
    transactions_router,
    dashboard_router,
    forecast_router,
    query_router,
    simulator_router,
    alerts_router,
    history_router,
    anomalies_router,
    categories_router,
)

async def seed_initial_data():
    """
    Initializes database tables and ensures default categories and test user are present.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check and seed categories
        cat_stmt = select(Category)
        existing_cats = (await session.execute(cat_stmt)).scalars().all()
        existing_names = {c.name.lower() for c in existing_cats}

        new_cats = []
        for cat_def in DEFAULT_CATEGORIES:
            if cat_def["name"].lower() not in existing_names:
                new_cats.append(Category(
                    name=cat_def["name"],
                    icon=cat_def["icon"],
                    color=cat_def["color"],
                    is_default=True
                ))

        if new_cats:
            session.add_all(new_cats)

        # Check and seed default dev user
        user_stmt = select(User).where(User.email == DEV_USER_EMAIL)
        dev_user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not dev_user:
            dev_user = User(
                email=DEV_USER_EMAIL,
                name=DEV_USER_NAME,
                avatar_url=DEV_USER_AVATAR
            )
            session.add(dev_user)

        await session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await seed_initial_data()
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Powered Personal Financial Operating System Backend API",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health checks
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }

# Register API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(personas_router, prefix=settings.API_V1_STR)
app.include_router(transactions_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(forecast_router, prefix=settings.API_V1_STR)
app.include_router(query_router, prefix=settings.API_V1_STR)
app.include_router(simulator_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)
app.include_router(history_router, prefix=settings.API_V1_STR)
app.include_router(anomalies_router, prefix=settings.API_V1_STR)
app.include_router(categories_router, prefix=settings.API_V1_STR)

# Serve Frontend static files if present
from pathlib import Path
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if (FRONTEND_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

