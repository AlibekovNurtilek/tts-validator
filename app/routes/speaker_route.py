from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.db import SessionLocal
from app.schemas.speaker import SpeakerCreate, SpeakerUpdate, SpeakerOut
from app.services import speaker_service

router = APIRouter(prefix="/speakers", tags=["speakers"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[SpeakerOut])
def get_all_speakers(db: Session = Depends(get_db)):
    return speaker_service.get_all_speakers(db)

@router.post("/", response_model=SpeakerOut, status_code=status.HTTP_201_CREATED)
def create_speaker(speaker: SpeakerCreate, db: Session = Depends(get_db)):
    return speaker_service.create_speaker(speaker, db)

@router.put("/{speaker_id}", response_model=SpeakerOut)
def update_speaker(speaker_id: int, speaker: SpeakerUpdate, db: Session = Depends(get_db)):
    return speaker_service.update_speaker(speaker_id, speaker, db)

@router.delete("/{speaker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_speaker(speaker_id: int, db: Session = Depends(get_db)):
    speaker_service.delete_speaker(speaker_id, db)
    return
