from pydantic import BaseModel
from datetime import datetime

class DatasetBase(BaseModel):
    name: str
    speaker_id: int
    url: str
    full_audio_path: str
    samples_dir: str
    count_of_samples: int
    duration: float

class DatasetCreate(DatasetBase):
    pass

class DatasetUpdate(DatasetBase):
    pass

class DatasetOut(DatasetBase):
    id: int
    created_at: datetime
    last_update: datetime

    class Config:
        orm_mode = True

class DatasetInitRequest(BaseModel):
    url: str
    speaker_id: int | None = None
    speaker_name: str | None = None
