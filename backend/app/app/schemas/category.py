from app.models.category import TransactionType
from app.schemas.common import Schema


class CategoryOut(Schema):
    id: int
    kind: TransactionType
    slug: str
    name: str
    icon: str
    color: str
