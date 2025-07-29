from app.celery_config import celery_app

# Импортируем задачи, чтобы они зарегистрировались в Celery
import app.tasks.initialize  # ← вот это важно
