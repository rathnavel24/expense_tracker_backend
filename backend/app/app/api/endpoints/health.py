from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import DB

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", summary="Liveness and database check")
def health(db: DB) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
