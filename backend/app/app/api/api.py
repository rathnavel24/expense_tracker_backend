from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    categories,
    dashboard,
    health,
    history,
    insights,
    recurring,
    transactions,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(transactions.router)
api_router.include_router(recurring.router)
api_router.include_router(dashboard.router)
api_router.include_router(history.router)
api_router.include_router(insights.router)
