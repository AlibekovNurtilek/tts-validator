from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db import SessionLocal
from pydantic import BaseModel
from app.models.datasets import AudioDataset
from app.services import dataset_service
from app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetOut,
    DatasetInitRequest
)
from app.tasks.initialize_dataset_tasks import initialize_dataset_task
from app.services.initialize_service import create_dataset_entry



router = APIRouter(prefix="/datasets", tags=["datasets"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



# ---------------------
# 📍 Роуты
# ---------------------

@router.get("/", response_model=List[DatasetOut])
def get_all_datasets(db: Session = Depends(get_db)):
    return dataset_service.get_all_datasets(db)


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset_by_id(dataset_id: int, db: Session = Depends(get_db)):
    return dataset_service.get_dataset_by_id(dataset_id, db)


@router.get("/by-speaker/{speaker_id}", response_model=List[DatasetOut])
def get_datasets_by_speaker_id(speaker_id: int, db: Session = Depends(get_db)):
    return dataset_service.get_datasets_by_speaker_id(speaker_id, db)


@router.post("/", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def create_dataset(dataset: DatasetCreate, db: Session = Depends(get_db)):
    return dataset_service.create_dataset(dataset, db)


@router.put("/{dataset_id}", response_model=DatasetOut)
def update_dataset(dataset_id: int, dataset: DatasetUpdate, db: Session = Depends(get_db)):
    return dataset_service.update_dataset(dataset_id, dataset, db)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset_service.delete_dataset(dataset_id, db)
    return
@router.post("/initialize")
def initialize_dataset(data: DatasetInitRequest, db: Session = Depends(get_db)):
    if not data.speaker_name:
        raise HTTPException(status_code=400, detail="speaker_name обязателен")

    # Шаг 1: создаём запись в БД со статусом INITIALIZING
    dataset_id = create_dataset_entry(db, data.speaker_name, data.url)

    # Шаг 2: запускаем фоновую задачу
    task = initialize_dataset_task.delay(dataset_id, data.dict())

    return {
        "message": "Задача инициализации добавлена",
        "task_id": task.id,
        "dataset_id": dataset_id
    }