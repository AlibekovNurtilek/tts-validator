#!/bin/bash

# Название лог-файлов
LOG_FILE="logs/server.log"
ERROR_FILE="logs/error.log"

# Создаём папку для логов, если не существует
mkdir -p logs

# Запускаем сервер с nohup и сохраняем логи
nohup uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8081 \
  --reload \
  > "$LOG_FILE" 2> "$ERROR_FILE" &
  
echo "✅ Server started on port 8081 (logs: $LOG_FILE)"
