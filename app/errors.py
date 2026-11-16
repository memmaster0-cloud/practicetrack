"""Исключения предметной области."""


class DomainError(Exception):
    """Базовое исключение приложения."""


class ValidationError(DomainError):
    """Некорректные входные данные."""


class AuthError(DomainError):
    """Неверные учётные данные или токен."""


class PermissionDenied(DomainError):
    """Действие запрещено для данного пользователя."""


class NotFoundError(DomainError):
    """Запрошенный объект не найден."""


class ConflictError(DomainError):
    """Конфликт данных (например, email уже занят)."""
