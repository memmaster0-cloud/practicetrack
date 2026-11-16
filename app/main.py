"""Точка входа веб-приложения ПрактикаТрек (FastAPI + SQLAlchemy).

Схему БД создают миграции Alembic: alembic upgrade head (в Docker выполняется при запуске).
"""
import logging
from contextlib import asynccontextmanager

from .api.factory import create_app
from .api.routes import get_container
from .config import load_settings
from .container import sql_container_dependency
from .db.session import make_session_factory
from .logging_config import configure_logging

settings = load_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("practicetrack")

_engine, session_factory = make_session_factory(settings.database_url)


@asynccontextmanager
async def lifespan(_app):
    logger.info("Приложение запущено, окружение: %s", settings.app_env)
    yield


app = create_app(lifespan=lifespan)
app.dependency_overrides[get_container] = sql_container_dependency(
    session_factory, settings.secret_key, settings.token_ttl_seconds)
