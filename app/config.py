"""Настройки приложения из переменных окружения (секреты не хранятся в коде)."""
import os
from dataclasses import dataclass
from typing import Mapping, Optional

from .errors import ValidationError
from .security import DEFAULT_TOKEN_TTL_SECONDS

DEV_SECRET = "dev-secret-change-me"
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _positive_int(name: str, value, maximum: Optional[int] = None) -> int:
    """Проверяет числовую настройку до запуска сервера или выдачи токена."""
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} должен быть целым числом") from exc
    if number <= 0 or (maximum is not None and number > maximum):
        limit = f"от 1 до {maximum}" if maximum is not None else "больше нуля"
        raise ValidationError(f"{name} должен быть {limit}")
    return number


@dataclass(frozen=True)
class Settings:
    """Настройки приложения, прочитанные из окружения."""

    database_url: str
    secret_key: str
    log_level: str
    token_ttl_seconds: int
    port: int
    app_env: str


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    """Читает и проверяет настройки; в production обязателен собственный SECRET_KEY."""
    env = os.environ if env is None else env
    app_env = env.get("APP_ENV", "development")
    secret = env.get("SECRET_KEY", DEV_SECRET)
    if app_env == "production" and secret in ("", DEV_SECRET):
        raise ValidationError("В production необходимо задать SECRET_KEY")
    log_level = env.get("LOG_LEVEL", "INFO").upper()
    if log_level not in LOG_LEVELS:
        raise ValidationError(f"Недопустимый LOG_LEVEL: {log_level}")
    ttl = _positive_int("TOKEN_TTL_SECONDS",
                        env.get("TOKEN_TTL_SECONDS", DEFAULT_TOKEN_TTL_SECONDS))
    port = _positive_int("PORT", env.get("PORT", "8000"), maximum=65535)
    return Settings(
        database_url=env.get("DATABASE_URL", "sqlite:///./practicetrack.db"),
        secret_key=secret, log_level=log_level,
        token_ttl_seconds=ttl, port=port, app_env=app_env)
