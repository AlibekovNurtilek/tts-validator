from app.celery_config import celery_app
from app.services.dataset_initializer import initialize_dataset_service
from app.db import SessionLocal

from app.schemas.dataset import DatasetInitRequest

@celery_app.task(bind=True)
def initialize_dataset_task(self, data_dict: dict):
    try:
        db = SessionLocal()
        data = DatasetInitRequest(**data_dict)
        result = initialize_dataset_service(data, db)
        return result
    except Exception as e:
        self.retry(exc=e, countdown=10, max_retries=3)  # если хочешь
        raise e
    finally:
        db.close()
