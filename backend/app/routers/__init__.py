from app.routers.auth import router as auth_router
from app.routers.personas import router as personas_router
from app.routers.transactions import router as transactions_router
from app.routers.dashboard import router as dashboard_router
from app.routers.forecast import router as forecast_router
from app.routers.query import router as query_router
from app.routers.simulator import router as simulator_router
from app.routers.alerts import router as alerts_router
from app.routers.history import router as history_router
from app.routers.anomalies import router as anomalies_router
from app.routers.categories import router as categories_router
from app.routers.promises import router as promises_router

__all__ = [
    "auth_router",
    "personas_router",
    "transactions_router",
    "dashboard_router",
    "forecast_router",
    "query_router",
    "simulator_router",
    "alerts_router",
    "history_router",
    "anomalies_router",
    "categories_router",
    "promises_router",
]
