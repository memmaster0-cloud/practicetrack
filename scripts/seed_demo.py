"""Заполняет базу демонстрационными данными: python scripts/seed_demo.py

В Docker: docker compose exec app python scripts/seed_demo.py
"""
import sys
from os.path import dirname, abspath

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from app.config import load_settings  # noqa: E402
from app.container import build_sql_container  # noqa: E402
from app.db.session import make_session_factory  # noqa: E402
from app.demo import seed_demo  # noqa: E402


def main() -> None:
    settings = load_settings()
    _engine, factory = make_session_factory(settings.database_url)
    with factory() as session:
        container = build_sql_container(session, settings.secret_key,
                                        settings.token_ttl_seconds)
        result = seed_demo(container)
    if result["created"]:
        print("Демо-данные созданы.")
        print(f"Преподаватель: {result['teacher']} / {result['password']}")
        print(f"Студенты: {', '.join(result['students'])} / {result['password']}")
    else:
        print("Демо-данные уже есть, ничего не изменено.")


if __name__ == "__main__":
    main()
