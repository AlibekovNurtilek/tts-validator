from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.speaker import Speaker
from app.schemas.speaker import SpeakerCreate, SpeakerUpdate

def get_all_speakers(db: Session):
    return db.query(Speaker).all()


def create_speaker(speaker: SpeakerCreate, db: Session):
    existing = db.query(Speaker).filter(Speaker.speaker_name == speaker.speaker_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Speaker already exists")
    new_speaker = Speaker(speaker_name=speaker.speaker_name)
    db.add(new_speaker)
    db.commit()
    db.refresh(new_speaker)
    return new_speaker


def update_speaker(speaker_id: int, speaker: SpeakerUpdate, db: Session):
    db_speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
    if not db_speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")
    db_speaker.speaker_name = speaker.speaker_name
    db.commit()
    db.refresh(db_speaker)
    return db_speaker


def delete_speaker(speaker_id: int, db: Session):
    db_speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
    if not db_speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")
    db.delete(db_speaker)
    db.commit()

def get_or_create_speaker_by_name(db: Session, speaker_name: str) -> Speaker:
    speaker = db.query(Speaker).filter(Speaker.speaker_name == speaker_name).first()
    if speaker:
        return speaker

    new_speaker = Speaker(speaker_name=speaker_name)
    db.add(new_speaker)
    db.commit()
    db.refresh(new_speaker)
    return new_speaker