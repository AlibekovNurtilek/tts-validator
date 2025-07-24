from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.samples import SampleText
from app.schemas.sample import SampleCreate, SampleUpdate


def get_all_samples(db: Session):
    return db.query(SampleText).all()


def get_sample_by_id(sample_id: int, db: Session):
    sample = db.query(SampleText).filter(SampleText.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    return sample


def get_samples_by_speaker_id(speaker_id: int, db: Session):
    return db.query(SampleText).filter(SampleText.speaker_id == speaker_id).all()


def get_samples_by_dataset_id(dataset_id: int, db: Session):
    return db.query(SampleText).filter(SampleText.dataset_id == dataset_id).all()


def create_sample(sample: SampleCreate, db: Session):
    new_sample = SampleText(**sample.dict())
    db.add(new_sample)
    db.commit()
    db.refresh(new_sample)
    return new_sample


def update_sample(sample_id: int, sample: SampleUpdate, db: Session):
    db_sample = db.query(SampleText).filter(SampleText.id == sample_id).first()
    if not db_sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    for field, value in sample.dict().items():
        setattr(db_sample, field, value)
    db.commit()
    db.refresh(db_sample)
    return db_sample


def delete_sample(sample_id: int, db: Session):
    db_sample = db.query(SampleText).filter(SampleText.id == sample_id).first()
    if not db_sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    db.delete(db_sample)
    db.commit()
