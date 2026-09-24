from fastapi import APIRouter

from app.api.routes import (
    auth,
    categories,
    dashboard,
    health,
    history,
    insights,
    recurring,
    transactions,
)

api_router = APIRouter(prefix="/api")
for module in (health, auth, categories, transactions, recurring, dashboard, history, insights):
    api_router.include_router(module.router)
