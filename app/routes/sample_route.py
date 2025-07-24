from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db import SessionLocal
from app.schemas.sample import (
    SampleCreate, SampleUpdate, SampleOut
)
from app.services import sample_service

router = APIRouter(prefix="/samples", tags=["samples"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[SampleOut])
def get_all_samples(db: Session = Depends(get_db)):
    return sample_service.get_all_samples(db)


@router.get("/{sample_id}", response_model=SampleOut)
def get_sample_by_id(sample_id: int, db: Session = Depends(get_db)):
    return sample_service.get_sample_by_id(sample_id, db)


@router.get("/by-speaker/{speaker_id}", response_model=List[SampleOut])
def get_samples_by_speaker_id(speaker_id: int, db: Session = Depends(get_db)):
    return sample_service.get_samples_by_speaker_id(speaker_id, db)


@router.get("/by-dataset/{dataset_id}", response_model=List[SampleOut])
def get_samples_by_dataset_id(dataset_id: int, db: Session = Depends(get_db)):
    return sample_service.get_samples_by_dataset_id(dataset_id, db)


@router.post("/", response_model=SampleOut, status_code=status.HTTP_201_CREATED)
def create_sample(sample: SampleCreate, db: Session = Depends(get_db)):
    return sample_service.create_sample(sample, db)


@router.put("/{sample_id}", response_model=SampleOut)
def update_sample(sample_id: int, sample: SampleUpdate, db: Session = Depends(get_db)):
    return sample_service.update_sample(sample_id, sample, db)


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sample(sample_id: int, db: Session = Depends(get_db)):
    sample_service.delete_sample(sample_id, db)
    return
