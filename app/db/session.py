"""Подключение к базе данных."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


def make_session_factory(database_url: str):
    """Создаёт движок и фабрику сеансов; для SQLite включает проверку внешних ключей."""
    kwargs = {"pool_pre_ping": True}
    is_sqlite = database_url.startswith("sqlite")
    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **kwargs)
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _record):
            """SQLite по умолчанию не проверяет внешние ключи и не выполняет каскады."""
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
