#!/usr/bin/env bash
# Все проверки проекта, которые работают без установки зависимостей (стандартная библиотека).
# С установленными зависимостями дополнительно запустите: pytest -v && behave && flake8 .
set -u
cd "$(dirname "$0")/.."
status=0
run() { echo; echo "=== $1 ==="; shift; "$@" || status=1; }

run "Модульные тесты" python3 -m unittest discover -s tests -t .
run "Покрытие кода (trace)" python3 measure_coverage.py
run "Метрики кода" python3 docs/analyze_code.py
run "Сверка миграций со схемой и моделями" python3 docs/verify_migrations.py
run "Сценарий Postman через сервисы" python3 docs/simulate_scenario.py
run "Генерация OpenAPI и Postman" python3 docs/gen_api_docs.py
if command -v flake8 >/dev/null 2>&1; then run "flake8" flake8 .; fi
echo; [ "$status" -eq 0 ] && echo "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" || echo "ЕСТЬ ОШИБКИ"
exit "$status"
