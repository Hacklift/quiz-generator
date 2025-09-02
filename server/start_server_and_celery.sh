#!/usr/bin/env bash
# -e = exit immediately if any command fails
# -m = enable job control (background jobs can be managed)
set -e -m

echo "[STARTUP] Launching Celery worker..."
celery -A server.celery_config.celery_app worker \
  -Q email,celery \
  --loglevel=info \
  --pool=solo \
  --concurrency=1 &

echo "[STARTUP] Starting FastAPI with Uvicorn..."
exec uvicorn server.main:app --host 0.0.0.0 --port 10000
