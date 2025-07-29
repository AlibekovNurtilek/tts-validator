from app.celery_config import celery_app

@celery_app.task
def run_sampling(dataset_id: int):
    print(f"🔁 Запуск семплинга для dataset_id={dataset_id}")
    # Тут будет реальная логика семплинга
    return {"status": "completed", "dataset_id": dataset_id}
