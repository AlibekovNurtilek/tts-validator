from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base

class SampleText(Base):
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("audio_datasets.id"), nullable=False)
    speaker_id = Column(Integer, ForeignKey("speakers.id"), nullable=False)

    filename = Column(String, nullable=False)  # имя .wav файла
    text = Column(Text, nullable=False)        # транскрипция

    start_time = Column(Float, nullable=True)  # начало в секундах
    end_time = Column(Float, nullable=True)    # конец в секундах
    duration = Column(Float, nullable=True)    # длина сегмента

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    dataset = relationship("AudioDataset", backref="samples")
    speaker = relationship("Speaker", backref="samples")
