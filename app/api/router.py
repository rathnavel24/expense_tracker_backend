from fastapi import APIRouter

from app.api.routes import auth, categories, dashboard, health, insights, recurring, transactions

api_router = APIRouter(prefix="/api")
for module in (health, auth, categories, transactions, recurring, dashboard, insights):
    api_router.include_router(module.router)
