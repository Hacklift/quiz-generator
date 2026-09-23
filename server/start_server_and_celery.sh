#!/usr/bin/env bash
# -e = exit immediately if any command fails
set -e

shutdown() {
  trap - EXIT INT TERM
  echo "[SHUTDOWN] Stopping FastAPI, Celery worker, and Celery Beat..."
  kill -TERM "${uvicorn_pid:-}" "${celery_worker_pid:-}" "${celery_beat_pid:-}" 2>/dev/null || true
  wait "${uvicorn_pid:-}" "${celery_worker_pid:-}" "${celery_beat_pid:-}" 2>/dev/null || true
}

trap shutdown EXIT INT TERM

echo "[STARTUP] Launching Celery worker..."
celery -A server.celery_config.celery_app worker \
  -Q email,celery \
  --loglevel=info \
  --pool=solo \
  --concurrency=1 &
celery_worker_pid=$!

echo "[STARTUP] Launching Celery Beat..."
celery -A server.celery_config.celery_app beat \
  --loglevel=info \
  --schedule=/tmp/quizwerk-celerybeat-schedule \
  --pidfile=/tmp/quizwerk-celerybeat.pid &
celery_beat_pid=$!

echo "[STARTUP] Starting FastAPI with Uvicorn..."
uvicorn server.main:app --host 0.0.0.0 --port 10000 &
uvicorn_pid=$!

# Treat any critical child exiting as a service failure so Render restarts all
# three processes together instead of leaving scheduling or queue delivery down.
wait -n "$uvicorn_pid" "$celery_worker_pid" "$celery_beat_pid"
