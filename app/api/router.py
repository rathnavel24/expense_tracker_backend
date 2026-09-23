from fastapi import APIRouter

from app.api.routes import auth, categories, dashboard, health, transactions

api_router = APIRouter(prefix="/api")
for module in (health, auth, categories, transactions, dashboard):
    api_router.include_router(module.router)
