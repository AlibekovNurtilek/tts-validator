#!/bin/bash

# Порты, которые нужно очистить (например, FastAPI)
ports=(8081)

# Остановка процессов по портам
for port in "${ports[@]}"; do
    pid=$(lsof -ti :$port)
    if [ -n "$pid" ]; then
        echo "🔴 Killing process on port $port (PID: $pid)..."
        kill -9 $pid
    else
        echo "🟢 No process running on port $port."
    fi
done

# Остановка Celery воркеров
celery_pids=$(pgrep -f "celery -A app.celery_worker worker")
if [ -n "$celery_pids" ]; then
    echo "🔴 Killing Celery workers (PIDs: $celery_pids)..."
    kill -9 $celery_pids
else
    echo "🟢 No Celery workers running."
fi
