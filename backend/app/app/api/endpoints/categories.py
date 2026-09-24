from fastapi import APIRouter

from app.core.security import CurrentUser
from app.db.session import DB
from app.models import TransactionType
from app.schemas.category import CategoryOut
from app.schemas.common import UNAUTHORIZED
from app.services import category_service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get(
    "",
    response_model=list[CategoryOut],
    summary="List categories",
    description="Expense categories (`kind=expense`) and income sources (`kind=income`), "
    "in display order. Omit `kind` to get both.",
    responses=UNAUTHORIZED,
)
def list_categories(
    _: CurrentUser, db: DB, kind: TransactionType | None = None
) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in category_service.list_active(db, kind)]
