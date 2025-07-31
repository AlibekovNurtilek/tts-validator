from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException
from app.models.samples import SampleText
from app.schemas.sample import SampleCreate, SampleUpdate
from app.models.data_status import SampleStatus

def get_all_samples(db: Session):
    return db.query(SampleText).all()


def get_sample_by_id(sample_id: int, db: Session):
    sample = db.query(SampleText).filter(SampleText.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    return sample


def get_samples_by_speaker_id(speaker_id: int, db: Session):
    return db.query(SampleText).filter(SampleText.speaker_id == speaker_id).all()




def get_samples_by_dataset_id(
    dataset_id: int,
    db: Session,
    page: int,
    limit: int,
    status: SampleStatus | None = None,
    search: str | None = None
):
    offset = (page - 1) * limit

    query = db.query(SampleText).filter(SampleText.dataset_id == dataset_id)

    # Фильтрация по статусу
    if status:
        if status == SampleStatus.UNREVIEWED:
            query = query.filter(
                SampleText.status.notin_([SampleStatus.APPROVED, SampleStatus.REJECTED])
            )
        else:
            query = query.filter(SampleText.status == status)

    # Поиск по filename или text, с игнором регистра
    if search:
        pattern = f"%{search.strip()}%"  # НЕ .lower()
        query = query.filter(
            or_(
                SampleText.filename.ilike(pattern),
                SampleText.text.ilike(pattern)
            )
        )

    total = query.count()

    samples = (
        query
        .order_by(SampleText.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "dataset_id": dataset_id,
        "page": page,
        "limit": limit,
        "total": total,
        "samples": samples
    }

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
    
    db_sample.text = sample.text
    db.commit()
    db.refresh(db_sample)
    return db_sample



def delete_sample(sample_id: int, db: Session):
    db_sample = db.query(SampleText).filter(SampleText.id == sample_id).first()
    if not db_sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    db.delete(db_sample)
    db.commit()

def approve_sample(sample_id: int, db: Session):
    sample = db.query(SampleText).filter(SampleText.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    sample.status = SampleStatus.APPROVED
    db.commit()
    db.refresh(sample)
    return sample

def reject_sample(sample_id: int, db: Session):
    sample = db.query(SampleText).filter(SampleText.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    sample.status = SampleStatus.REJECTED
    db.commit()
    db.refresh(sample)
    return sample
