from typing import Any

from app.schemas.common import ErrorResponse

# Reusable OpenAPI documentation for error responses.
UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not signed in or session expired."}
}
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Not found (or not owned by you)."}
}
VALIDATION: dict[int | str, dict[str, Any]] = {
    422: {"model": ErrorResponse, "description": "Invalid input; see `fields`."}
}
