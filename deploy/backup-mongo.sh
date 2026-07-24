#!/usr/bin/env bash
# Nightly MongoDB backup for Quiz Generator. Installed as a cron job by
# deploy.sh. Keeps 7 daily archives in /opt/quiz-generator/backups.
set -euo pipefail

APP_DIR=/opt/quiz-generator
BACKUP_DIR=$APP_DIR/backups
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

cd $APP_DIR
docker compose -f docker-compose.prod.yml exec -T mongodb \
    mongodump --archive --gzip --db quizApp_db \
    > "$BACKUP_DIR/quizApp_db-$(date +%F).archive.gz"

find "$BACKUP_DIR" -name 'quizApp_db-*.archive.gz' -mtime +$RETENTION_DAYS -delete

echo "$(date -Is) backup complete: $(ls -lh "$BACKUP_DIR" | tail -1)"
