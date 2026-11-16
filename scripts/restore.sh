#!/usr/bin/env bash
# Восстановление базы данных из дампа: ./scripts/restore.sh backups/practicetrack_XXXX.sql.gz
set -euo pipefail

FILE="${1:?Укажите файл резервной копии}"
[ -f "$FILE" ] || { echo "Файл не найден: $FILE" >&2; exit 1; }

read -r -p "Данные в базе будут заменены данными из $FILE. Продолжить? [y/N] " answer
[ "$answer" = "y" ] || { echo "Отменено"; exit 1; }

docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'
gunzip -c "$FILE" | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
echo "База данных восстановлена из $FILE"
