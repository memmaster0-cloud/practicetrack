"""Соответствие исключений предметной области и HTTP-статусов."""
from ..errors import (AuthError, ConflictError, DomainError, NotFoundError, PermissionDenied,
                      ValidationError)

_STATUS_BY_ERROR = (
    (AuthError, 401),
    (PermissionDenied, 403),
    (NotFoundError, 404),
    (ConflictError, 409),
    (ValidationError, 422),
)


def status_for(exc: Exception) -> int:
    """HTTP-статус для исключения: 401, 403, 404, 409, 422; для прочих DomainError 400."""
    for cls, code in _STATUS_BY_ERROR:
        if isinstance(exc, cls):
            return code
    if isinstance(exc, DomainError):
        return 400
    return 500
