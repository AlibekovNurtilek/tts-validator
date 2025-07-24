from pydantic import BaseModel
from datetime import datetime

class SampleBase(BaseModel):
    dataset_id: int
    speaker_id: int
    filename: str
    text: str
    start_time: float | None = None
    end_time: float | None = None
    duration: float | None = None

class SampleCreate(SampleBase):
    pass

class SampleUpdate(SampleBase):
    pass

class SampleOut(SampleBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
