#!/bin/bash

# Название лог-файлов
LOG_DIR="logs"
SERVER_LOG="$LOG_DIR/server.log"
CELERY_LOG="$LOG_DIR/celery.log"

# Создаём папку для логов, если не существует
mkdir -p "$LOG_DIR"

# Запускаем FastAPI сервер (stdout + stderr в один лог)
nohup uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8081 \
  --reload \
  > "$SERVER_LOG" 2>&1 &

echo "✅ Server started on port 8081 (logs: $SERVER_LOG)"

# Запускаем Celery воркер (отдельный лог)
nohup celery -A app.celery_worker worker \
  --loglevel=info > "$CELERY_LOG" 2>&1 &

echo "✅ Celery worker started (logs: $CELERY_LOG)"
