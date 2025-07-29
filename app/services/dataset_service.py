from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.datasets import AudioDataset
from app.models.speakers import Speaker
from app.schemas.dataset import DatasetCreate, DatasetUpdate, DatasetInitRequest
from app.config import BASE_DATA_DIR



def get_all_datasets(db: Session):
    return db.query(AudioDataset).all()


def get_dataset_by_id(dataset_id: int, db: Session):
    dataset = db.query(AudioDataset).filter(AudioDataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


def get_datasets_by_speaker_id(speaker_id: int, db: Session):
    return db.query(AudioDataset).filter(AudioDataset.speaker_id == speaker_id).all()


def create_dataset(dataset: DatasetCreate, db: Session):
    new_dataset = AudioDataset(**dataset.dict())
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)
    return new_dataset


def update_dataset(dataset_id: int, dataset: DatasetUpdate, db: Session):
    db_dataset = db.query(AudioDataset).filter(AudioDataset.id == dataset_id).first()
    if not db_dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    for field, value in dataset.dict().items():
        setattr(db_dataset, field, value)
    db.commit()
    db.refresh(db_dataset)
    return db_dataset


def delete_dataset(dataset_id: int, db: Session):
    db_dataset = db.query(AudioDataset).filter(AudioDataset.id == dataset_id).first()
    if not db_dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(db_dataset)
    db.commit()


