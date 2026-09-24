"""Import all models here so Alembic autogenerate can discover them via Base.metadata."""

from app.db.base_class import Base  # noqa: F401
from app.models.auth_session import AuthSession  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.recurring_rule import RecurringRule  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.user import User  # noqa: F401
