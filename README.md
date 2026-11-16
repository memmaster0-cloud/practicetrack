# ПрактикаТрек

Веб-сервис учёта сдачи практических работ. Студент видит все свои работы со сроками и
статусами в одном месте, преподаватель принимает работы или возвращает их на доработку и
получает отчёт о задолженностях.

Мини-проект по дисциплине «Технологии разработки программного обеспечения».
Автор: Шамсетдинов Мансур Данильевич, группа БИС 31с.

## Возможности

- Регистрация и вход (JWT-токены, пароли хранятся в виде хэша PBKDF2).
- Преподаватель: создаёт дисциплины и практические работы со сроками, проверяет сдачи
  (принять или вернуть с комментарием), смотрит сдачи группы и отчёт о задолженностях.
- Студент: список работ с фильтрами по дисциплине и статусу, подсветка близких и
  просроченных сроков, смена статуса (начать, сдать), комментарии преподавателя, процент
  принятых работ.
- Статусы: не начата → в работе → сдана → принята или на доработке (правила переходов в
  `app/domain.py`).

## Технологии

Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (SQLite для разработки),
PyJWT, pytest/unittest, behave, flake8, Docker и Docker Compose, GitHub Actions.

## Быстрый старт в Docker

```bash
cp .env.example .env                              # задайте свои пароли и SECRET_KEY
docker compose up -d --build                      # приложение + PostgreSQL, миграции применяются сами
docker compose exec app python scripts/seed_demo.py   # демонстрационные данные
```

Интерактивная документация и «интерфейс» для демонстрации: http://localhost:8000/docs
Проверка работоспособности: http://localhost:8000/health

Демонстрационные учётные записи (пароль `demo12345`): `teacher@demo.kz`, `student1@demo.kz`,
`student2@demo.kz`, `student3@demo.kz`. Сценарий показа: `docs/DEMO.md`.

## Запуск без Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=sqlite:///./practicetrack.db SECRET_KEY=dev-secret
alembic upgrade head
python scripts/seed_demo.py
uvicorn app.main:app --reload
```

## Тесты и проверки

```bash
pytest -v                                    # модульные, API, CRUD, миграции
pytest --cov=app --cov-report=term-missing   # покрытие
behave                                       # BDD-сценарии
flake8 .                                     # стиль
python docs/analyze_code.py                  # метрики кода
python docs/verify_migrations.py             # сверка миграций со схемой и моделями
```

В CI (`.github/workflows/ci.yml`) выполняются те же проверки, затем собирается Docker-образ.

## Структура проекта

```
app/
  domain.py          сущности, статусы, правила переходов
  services.py        бизнес-логика (аутентификация, дисциплины, работы, сдачи, отчёты)
  repositories.py    абстракции хранилищ и реализации в памяти
  db/                модели SQLAlchemy, CRUD, репозитории SQL, сеансы
  api/               маршруты FastAPI, схемы, обработка ошибок
  container.py       сборка сервисов (память или SQL)
  security.py        хэширование паролей и JWT
  config.py          настройки из окружения
alembic/             миграции схемы БД
db/schema.sql        SQL-схема (PostgreSQL)
docs/                OpenAPI, коллекция Postman, сценарий демонстрации, скрипты проверки
features/            BDD-сценарии (Gherkin)
tests/               автоматические тесты
scripts/             резервное копирование, восстановление, демо-данные
```

## Что проверено и что нет

Выполнены pytest с покрытием, BDD и flake8, включая API, SQLAlchemy/SQLite и реальные
миграции Alembic. Команды, версии и результаты сохранены в `delivery/evidence/`.
Проверки выполнены на Windows/Python 3.15; Linux/Python 3.12 в CI и PostgreSQL/Docker
требуют отдельного запуска. Валидация диапазонов PORT и TOKEN_TTL_SECONDS исправлена
через реальный цикл TDD с сохранёнными логами.

## Комплект практических работ

`delivery/README.md` — указатель на 15 отчётов Word, итоговый отчёт, UML/ER,
презентацию из 13 слайдов и текст выступления. `delivery/REMAINING.md` перечисляет
необходимые действия в аккаунтах, реальные скриншоты и самооценку автора.
Для повторной проверки: `python scripts/validate_delivery.py`.
Для пересборки документов: установить `requirements-docs.txt`, затем
`python scripts/build_delivery.py`.

## Ограничения

- Веб-интерфейса нет: взаимодействие через Swagger UI и REST API (веб-клиент из архитектуры
  ПР4 не реализован).
- HTTPS в Compose не настроен (предполагается обратный прокси на сервере).
- Нагрузочное тестирование не проводилось.
- Отзыв JWT-токена до истечения срока не поддерживается.
