#!/usr/bin/env bash
# Резервная копия базы данных PostgreSQL из контейнера db (сжатый SQL-дамп).
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="$BACKUP_DIR/practicetrack_${STAMP}.sql.gz"

docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$FILE"

# Политика хранения: удаляем копии старше KEEP_DAYS дней
find "$BACKUP_DIR" -name 'practicetrack_*.sql.gz' -mtime +"$KEEP_DAYS" -delete

echo "Резервная копия создана: $FILE"
