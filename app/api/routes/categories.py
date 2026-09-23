from fastapi import APIRouter

from app.api.deps import DB, CurrentUser
from app.api.responses import UNAUTHORIZED
from app.models import TransactionType
from app.repositories import categories
from app.schemas.category import CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


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
    return [CategoryOut.model_validate(c) for c in categories.list_active(db, kind)]
